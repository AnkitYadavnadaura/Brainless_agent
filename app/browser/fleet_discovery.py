"""Read-only discovery of installed Windows browsers and their profile metadata.

Only executable locations, Chromium ``Local State``, Firefox ``profiles.ini``,
and directory names are inspected. Login databases and browser history are never
opened. Discovery does not start a browser or create/modify a profile.
"""
from __future__ import annotations

import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class BrowserInstallation:
    id: str
    name: str
    family: str
    executable: Path
    user_data_dir: Path


@dataclass(frozen=True)
class BrowserProfile:
    id: str
    browser_id: str
    name: str
    directory: Path
    profile_directory: str


@dataclass(frozen=True)
class BrowserInventory:
    browsers: list[BrowserInstallation]
    profiles: list[BrowserProfile]
    warnings: list[str]


@dataclass(frozen=True)
class _BrowserSpec:
    name: str
    family: str
    executables: tuple[str, ...]
    install_paths: tuple[tuple[str, str], ...]
    profile_env: str
    profile_path: str
    root_profile: bool = False


_SPECS = (
    _BrowserSpec("Google Chrome", "chromium", ("chrome.exe",),
                 (("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
                  ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
                  ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe")),
                 "LOCALAPPDATA", "Google/Chrome/User Data"),
    _BrowserSpec("Microsoft Edge", "chromium", ("msedge.exe",),
                 (("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
                  ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
                  ("LOCALAPPDATA", "Microsoft/Edge/Application/msedge.exe")),
                 "LOCALAPPDATA", "Microsoft/Edge/User Data"),
    _BrowserSpec("Brave", "chromium", ("brave.exe",),
                 (("PROGRAMFILES", "BraveSoftware/Brave-Browser/Application/brave.exe"),
                  ("PROGRAMFILES(X86)", "BraveSoftware/Brave-Browser/Application/brave.exe"),
                  ("LOCALAPPDATA", "BraveSoftware/Brave-Browser/Application/brave.exe")),
                 "LOCALAPPDATA", "BraveSoftware/Brave-Browser/User Data"),
    _BrowserSpec("Vivaldi", "chromium", ("vivaldi.exe",),
                 (("LOCALAPPDATA", "Vivaldi/Application/vivaldi.exe"),
                  ("PROGRAMFILES", "Vivaldi/Application/vivaldi.exe"),
                  ("PROGRAMFILES(X86)", "Vivaldi/Application/vivaldi.exe")),
                 "LOCALAPPDATA", "Vivaldi/User Data"),
    _BrowserSpec("Opera", "chromium", ("opera.exe",),
                 (("LOCALAPPDATA", "Programs/Opera/launcher.exe"),
                  ("LOCALAPPDATA", "Programs/Opera/opera.exe"),
                  ("PROGRAMFILES", "Opera/launcher.exe"),
                  ("PROGRAMFILES", "Opera/opera.exe"),
                  ("PROGRAMFILES(X86)", "Opera/launcher.exe"),
                  ("PROGRAMFILES(X86)", "Opera/opera.exe")),
                 "APPDATA", "Opera Software/Opera Stable", True),
    _BrowserSpec("Opera GX", "chromium", ("opera_gx.exe",),
                 (("LOCALAPPDATA", "Programs/Opera GX/launcher.exe"),
                  ("LOCALAPPDATA", "Programs/Opera GX/opera.exe"),
                  ("PROGRAMFILES", "Opera GX/launcher.exe")),
                 "APPDATA", "Opera Software/Opera GX Stable", True),
    _BrowserSpec("Mozilla Firefox", "firefox", ("firefox.exe",),
                 (("PROGRAMFILES", "Mozilla Firefox/firefox.exe"),
                  ("PROGRAMFILES(X86)", "Mozilla Firefox/firefox.exe"),
                  ("LOCALAPPDATA", "Mozilla Firefox/firefox.exe")),
                 "APPDATA", "Mozilla/Firefox"),
)


def _path_key(path: Path) -> str:
    return str(path.resolve()).casefold()


def _identifier(prefix: str, value: str) -> str:
    return prefix + "-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def _registry_executables(executable_name: str, warnings: list[str]) -> Iterable[str]:
    try:
        import winreg
    except ImportError:
        return
    key_path = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | view) as key:
                    value, value_type = winreg.QueryValueEx(key, None)
                if value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) and isinstance(value, str):
                    yield value
            except FileNotFoundError:
                pass
            except OSError:
                warnings.append(f"Cannot read an App Paths registry entry for {executable_name}.")


def _metadata_text(path: Path, label: str, warnings: list[str]) -> str | None:
    try:
        # Profile metadata is small. Bound reads without opening credential stores.
        with path.open("r", encoding="utf-8-sig") as stream:
            data = stream.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            warnings.append(f"{label} metadata exceeds the discovery size limit.")
            return None
        return data
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError):
        warnings.append(f"Cannot read {label} metadata; it may be locked or damaged.")
        return None


def _safe_component(value: object) -> bool:
    return (isinstance(value, str) and bool(value) and value not in (".", "..")
            and not any(char in value for char in ("/", "\\", ":", "\x00")))


def _display_name(raw: object, fallback: str) -> str:
    # An account email is not required to identify an automation participant.
    if not isinstance(raw, str) or "@" in raw:
        return fallback
    cleaned = " ".join(raw.split())[:100]
    return cleaned or fallback


def _profile(browser: BrowserInstallation, directory: Path, component: str, name: str) -> BrowserProfile:
    directory = directory.resolve()
    return BrowserProfile(_identifier("profile", browser.id + ":" + _path_key(directory)),
                          browser.id, name, directory, component)


def _chromium_profiles(browser: BrowserInstallation, root: Path, warnings: list[str],
                       *, root_profile: bool = False, managed: bool = False) -> list[BrowserProfile]:
    if not root.is_dir():
        return []
    text = _metadata_text(root / "Local State", browser.name, warnings)
    cache: dict = {}
    if text is not None:
        try:
            payload = json.loads(text)
            profile_data = payload.get("profile", {})
            cache = profile_data.get("info_cache", {})
            if not isinstance(cache, dict):
                raise ValueError("invalid profile cache")
        except (ValueError, AttributeError):
            warnings.append(f"{browser.name} profile metadata is malformed; checking profile directories.")
            cache = {}
    components = set()
    for component in cache:
        if _safe_component(component):
            components.add(component)
        else:
            warnings.append(f"{browser.name} profile metadata contains an invalid directory name.")
    try:
        for child in root.iterdir():
            if child.is_dir() and (child.name == "Default" or re.fullmatch(r"Profile \d+", child.name)):
                components.add(child.name)
    except OSError:
        warnings.append(f"Cannot enumerate {browser.name} profile directories.")
    profiles = []
    for component in sorted(components, key=lambda value: (value != "Default", value.casefold())):
        directory = root / component
        if not directory.is_dir():
            warnings.append(f"{browser.name} has a profile metadata entry without an available directory.")
            continue
        # Do not follow a metadata entry or junction outside this browser's root.
        if not directory.resolve().is_relative_to(root.resolve()):
            warnings.append(f"{browser.name} has a profile directory outside its configured root; skipped.")
            continue
        info = cache.get(component, {})
        name = _display_name(info.get("name") if isinstance(info, dict) else None, component)
        if managed:
            name = f"Brainless managed: {name}"
        profiles.append(_profile(browser, directory, component, name))
    # Older Opera versions keep their only profile directly in the roaming root.
    if root_profile and not profiles and (root / "Preferences").is_file():
        profiles.append(_profile(browser, root, "", "Default"))
    return profiles


def _firefox_profiles(browser: BrowserInstallation, warnings: list[str]) -> list[BrowserProfile]:
    root = browser.user_data_dir
    text = _metadata_text(root / "profiles.ini", browser.name, warnings)
    if text is None:
        return []
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except configparser.Error:
        warnings.append("Mozilla Firefox profiles.ini is malformed.")
        return []
    profiles = []
    for section in parser.sections():
        if not re.fullmatch(r"Profile\d+", section, flags=re.IGNORECASE):
            continue
        path_text = parser.get(section, "Path", fallback="").strip()
        if not path_text or "\x00" in path_text:
            warnings.append("Mozilla Firefox has a profile entry without a valid path.")
            continue
        relative = parser.get(section, "IsRelative", fallback="1")
        if relative not in ("0", "1"):
            warnings.append("Mozilla Firefox has an invalid IsRelative profile flag.")
            continue
        directory = Path(path_text)
        if relative == "1":
            directory = root / directory
            if not directory.resolve().is_relative_to(root.resolve()):
                warnings.append("Mozilla Firefox has a relative profile outside its root; skipped.")
                continue
        elif not directory.is_absolute():
            warnings.append("Mozilla Firefox has a non-absolute external profile path; skipped.")
            continue
        if not directory.is_dir():
            warnings.append("Mozilla Firefox has a profile entry without an available directory.")
            continue
        name = _display_name(parser.get(section, "Name", fallback=""), section)
        profiles.append(_profile(browser, directory, directory.name, name))
    return profiles


def discover_browsers(*, env: Mapping[str, str] | None = None,
                      registry_reader: Callable[[str], Iterable[str | Path]] | None = None,
                      path_lookup: Callable[[str], str | Path | None] | None = None,
                      managed_profile: Path | None = None) -> BrowserInventory:
    """Discover browser installations and existing profiles without launching them.

    ``registry_reader(exe_name)`` and ``path_lookup(exe_name)`` can be injected for
    deterministic tests. Environment keys are case-insensitive. One executable
    per browser/profile root is used when both per-user and machine installations
    exist; this avoids opening the same physical profile twice. ``managed_profile``
    is an optional Chromium user-data root belonging to the existing app runtime.
    """
    environment = {key.upper(): value for key, value in (os.environ if env is None else env).items()}
    warnings: list[str] = []
    registry_reader = registry_reader or (lambda executable: _registry_executables(executable, warnings))
    if path_lookup is None:
        path_lookup = lambda executable: shutil.which(executable, path=environment.get("PATH", ""))
    browsers = []
    profiles = []
    seen_executables = set()
    seen_roots = set()
    for spec in _SPECS:
        candidates: list[str | Path] = []
        for executable_name in spec.executables:
            try:
                candidates.extend(registry_reader(executable_name))
            except (OSError, ValueError, TypeError):
                warnings.append(f"Cannot query executable registration for {spec.name}.")
        candidates.extend(Path(environment[key]) / suffix for key, suffix in spec.install_paths
                          if environment.get(key))
        for executable_name in spec.executables:
            try:
                path_candidate = path_lookup(executable_name)
                if path_candidate:
                    candidates.append(path_candidate)
            except (OSError, ValueError):
                warnings.append(f"Cannot query the executable search path for {spec.name}.")
        executable = None
        for candidate in candidates:
            raw_path = re.sub(r"%([^%]+)%", lambda match: environment.get(match[1].upper(), match[0]),
                              str(candidate).strip().strip('"'))
            path = Path(raw_path)
            try:
                if path.is_absolute() and path.is_file() and _path_key(path) not in seen_executables:
                    executable = path.resolve()
                    break
            except (OSError, ValueError):
                warnings.append(f"Cannot inspect an executable candidate for {spec.name}.")
        if executable is None:
            continue
        if not environment.get(spec.profile_env):
            warnings.append(f"Cannot locate {spec.name} profiles: {spec.profile_env} is unavailable.")
            continue
        root = (Path(environment[spec.profile_env]) / spec.profile_path).resolve()
        if _path_key(root) in seen_roots:
            continue
        browser = BrowserInstallation(_identifier("browser", _path_key(executable)),
                                      spec.name, spec.family, executable, root)
        browsers.append(browser)
        seen_executables.add(_path_key(executable))
        seen_roots.add(_path_key(root))
        found = (_firefox_profiles(browser, warnings) if spec.family == "firefox" else
                 _chromium_profiles(browser, root, warnings, root_profile=spec.root_profile))
        if spec.name == "Google Chrome" and managed_profile is not None:
            managed_root = Path(managed_profile).resolve()
            if _path_key(managed_root) not in seen_roots:
                found.extend(_chromium_profiles(browser, managed_root, warnings, managed=True))
                seen_roots.add(_path_key(managed_root))
        if not found:
            warnings.append(f"{spec.name} is installed but has no available profile directories.")
        profiles.extend(found)
    # Firefox profiles.ini may contain aliases to one physical profile directory.
    unique_profiles = {}
    for profile in profiles:
        unique_profiles.setdefault(_path_key(profile.directory), profile)
    return BrowserInventory(browsers, list(unique_profiles.values()), list(dict.fromkeys(warnings)))


def managed_leader_profile(inventory: BrowserInventory, root: Path) -> BrowserProfile | None:
    """Select the profile Chrome opens for the app's --user-data-dir command."""
    root = Path(root).resolve()
    chrome_ids = {browser.id for browser in inventory.browsers if browser.name == 'Google Chrome'}
    candidates = {profile.profile_directory: profile for profile in inventory.profiles
                  if profile.browser_id in chrome_ids and profile.directory.parent.resolve() == root}
    text = _metadata_text(root / 'Local State', 'Google Chrome', [])
    try:
        state = json.loads(text) if text else {}
        last_used = state.get('profile', {}).get('last_used', 'Default')
    except (ValueError, AttributeError):
        last_used = 'Default'
    return candidates.get(last_used) if isinstance(last_used, str) else None


def profile_launch_arguments(browser: BrowserInstallation, profile: BrowserProfile,
                             urls: list[str]) -> list[str]:
    """Return argv for one visible window; never add remote-debugging flags.

    Callers must launch with ``shell=False``. Chromium uses the existing profile
    root and directory. Firefox explicitly selects the profile by filesystem path
    so duplicate human-readable profile names cannot select the wrong profile.
    """
    if profile.browser_id != browser.id:
        raise ValueError("The profile does not belong to this browser installation")
    if not urls:
        raise ValueError("At least one web URL is required")
    for url in urls:
        # The native-window owner uses this one inert page to identify its new
        # window before navigating to the two providers. Never permit arbitrary
        # data URLs or executable content from a planner as launch arguments.
        if url.startswith("data:text/html,") and re.fullmatch(
                r"<!doctype html><title>Brainless-Team-[a-f0-9]{32}</title><p>Browser team starting</p>",
                unquote(url.removeprefix("data:text/html,"))):
            continue
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or any(character.isspace() for character in url)):
            raise ValueError("Only absolute HTTP(S) URLs without credentials are supported")
    if browser.family == "firefox":
        # Firefox interprets each -new-window as a separate window. Additional
        # URLs must be -new-tab to keep this participant in a single window.
        # Without -no-remote Firefox can route the marker to an unrelated
        # running profile. A locked selected profile must fail visibly instead.
        arguments = [str(browser.executable), "-no-remote", "-profile", str(profile.directory), "-new-window", urls[0]]
        for url in urls[1:]:
            arguments.extend(("-new-tab", url))
        return arguments
    if browser.family != "chromium":
        raise ValueError(f"Unsupported browser family: {browser.family}")
    if profile.profile_directory and not _safe_component(profile.profile_directory):
        raise ValueError("Invalid Chromium profile directory")
    root = profile.directory.parent if profile.profile_directory else profile.directory
    if profile.profile_directory and profile.directory.name != profile.profile_directory:
        raise ValueError("Chromium profile path and profile directory do not match")
    arguments = [str(browser.executable), f"--user-data-dir={root}", "--new-window",
                 "--force-renderer-accessibility"]
    if profile.profile_directory:
        arguments.append(f"--profile-directory={profile.profile_directory}")
    return [*arguments, *urls]
