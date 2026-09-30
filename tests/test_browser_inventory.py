import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from urllib.parse import quote

import pytest

from app.browser.fleet_discovery import (
    BrowserInstallation,
    BrowserInventory,
    BrowserProfile,
    discover_browsers,
    managed_leader_profile,
    profile_launch_arguments,
)


def test_managed_leader_matches_chrome_last_used_profile_not_another_browser(tmp_path):
    root = tmp_path / 'data/browser-profile'
    root.mkdir(parents=True)
    chrome = BrowserInstallation('chrome', 'Google Chrome', 'chromium', tmp_path / 'chrome.exe', tmp_path / 'Personal')
    edge = BrowserInstallation('edge', 'Microsoft Edge', 'chromium', tmp_path / 'edge.exe', root)
    profiles = [BrowserProfile('default', 'chrome', 'Default', root / 'Default', 'Default'),
                BrowserProfile('chosen', 'chrome', 'Chosen', root / 'Profile 1', 'Profile 1'),
                BrowserProfile('edge', 'edge', 'Edge', root / 'Profile 1', 'Profile 1'),
                BrowserProfile('personal', 'chrome', 'Personal', tmp_path / 'Personal/Default', 'Default')]
    inventory = BrowserInventory([chrome, edge], profiles, [])
    (root / 'Local State').write_text(json.dumps({'profile': {'last_used': 'Profile 1'}}))
    assert managed_leader_profile(inventory, root).id == 'chosen'
    (root / 'Local State').write_text(json.dumps({'profile': {'last_used': 'Missing'}}))
    assert managed_leader_profile(inventory, root) is None


@pytest.fixture
def environment(tmp_path):
    paths = {"LOCALAPPDATA": tmp_path / "local", "APPDATA": tmp_path / "roaming",
             "PROGRAMFILES": tmp_path / "programs", "PROGRAMFILES(X86)": tmp_path / "programs32"}
    for path in paths.values():
        path.mkdir()
    return {key: str(path) for key, path in paths.items()}


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def chrome(environment, profiles=("Default",)):
    executable = touch(Path(environment["LOCALAPPDATA"]) / "Google/Chrome/Application/chrome.exe")
    root = Path(environment["LOCALAPPDATA"]) / "Google/Chrome/User Data"
    for profile in profiles:
        (root / profile).mkdir(parents=True)
    return executable, root


def discover(environment, **kwargs):
    return discover_browsers(env=environment, registry_reader=kwargs.pop("registry_reader", lambda _: ()),
                             path_lookup=kwargs.pop("path_lookup", lambda _: None), **kwargs)


def test_installed_browsers_and_real_profiles_are_read_only_metadata(environment, monkeypatch):
    executable, root = chrome(environment, ("Default", "Profile 1", "Profile 2", "Work"))
    (root / "Local State").write_text(json.dumps({"profile": {"info_cache": {
        "Default": {"name": "Personal", "user_name": "private@example.test"},
        "Profile 1": {"name": "private@example.test"},
        "Work": {"name": "Work"},
    }}}), encoding="utf-8")
    # These files must never be opened, even when they exist.
    for filename in ("Login Data", "Cookies", "History"):
        (root / "Default" / filename).write_text("DO NOT READ", encoding="utf-8")
    opened = []
    original_open = Path.open

    def track_open(path, *args, **kwargs):
        opened.append(path.name)
        assert path.name not in ("Login Data", "Cookies", "History")
        assert args[0] == "r" if args else kwargs.get("mode", "r") == "r"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", track_open)
    inventory = discover(environment)
    assert len(inventory.browsers) == 1
    assert inventory.browsers[0].executable == executable
    assert {profile.profile_directory for profile in inventory.profiles} == {"Default", "Profile 1", "Profile 2", "Work"}
    assert {profile.name for profile in inventory.profiles} == {"Personal", "Profile 1", "Profile 2", "Work"}
    assert "private@example.test" not in repr(inventory)
    assert opened == ["Local State"]
    assert inventory.warnings == []
    assert inventory == discover(environment)
    with pytest.raises(FrozenInstanceError):
        inventory.browsers[0].name = "Changed"


def test_registry_and_known_path_and_path_lookup_candidates_are_deduplicated(environment, tmp_path):
    executable, root = chrome(environment)
    # An installation in Program Files shares the same original user profiles.
    touch(Path(environment["PROGRAMFILES"]) / "Google/Chrome/Application/chrome.exe")
    inventory = discover(environment, registry_reader=lambda name: [str(executable), str(executable)] if name == "chrome.exe" else (),
                         path_lookup=lambda name: executable if name == "chrome.exe" else None)
    assert len(inventory.browsers) == 1
    assert len(inventory.profiles) == 1
    assert inventory.profiles[0].directory == root / "Default"


def test_registry_path_expansion_and_case_insensitive_environment(environment, tmp_path):
    executable = touch(Path(environment["PROGRAMFILES"]) / "Custom Browser/chrome.exe")
    profile = Path(environment["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default"
    profile.mkdir(parents=True)
    lower_env = {key.lower(): value for key, value in environment.items()}
    inventory = discover(lower_env, registry_reader=lambda name: ['"%ProgramFiles%/Custom Browser/chrome.exe"'] if name == "chrome.exe" else ())
    assert inventory.browsers[0].executable == executable
    assert inventory.profiles[0].directory == profile


def test_path_can_discover_nonstandard_installation(environment, tmp_path):
    executable = touch(tmp_path / "portable/msedge.exe")
    profile = Path(environment["LOCALAPPDATA"]) / "Microsoft/Edge/User Data/Profile 3"
    profile.mkdir(parents=True)
    inventory = discover(environment, path_lookup=lambda name: executable if name == "msedge.exe" else None)
    assert inventory.browsers[0].name == "Microsoft Edge"
    assert inventory.profiles[0].profile_directory == "Profile 3"


@pytest.mark.parametrize("state", ["not-json", "[]", '{"profile": null}', '{"profile":{"info_cache":[]}}'])
def test_corrupt_local_state_falls_back_to_existing_directories(environment, state):
    _, root = chrome(environment, ("Default", "Profile 2"))
    (root / "Local State").write_text(state, encoding="utf-8")
    inventory = discover(environment)
    assert len(inventory.profiles) == 2
    assert any("malformed" in warning for warning in inventory.warnings)


def test_locked_local_state_is_warning_and_directory_discovery_continues(environment, monkeypatch):
    _, root = chrome(environment)
    original_open = Path.open

    def locked(path, *args, **kwargs):
        if path == root / "Local State":
            raise PermissionError("locked")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", locked)
    inventory = discover(environment)
    assert len(inventory.profiles) == 1
    assert any("locked" in warning for warning in inventory.warnings)


def test_metadata_paths_cannot_escape_profile_root(environment, tmp_path):
    _, root = chrome(environment)
    (tmp_path / "escape").mkdir()
    (root / "Local State").write_text(json.dumps({"profile": {"info_cache": {
        "../../escape": {"name": "Escape"}, str(tmp_path / "escape"): {},
        "Missing": {}, "Guest Profile": {"name": "Stale"},
    }}}), encoding="utf-8")
    inventory = discover(environment)
    assert [profile.profile_directory for profile in inventory.profiles] == ["Default"]
    assert any("invalid directory" in warning for warning in inventory.warnings)
    assert any("without an available directory" in warning for warning in inventory.warnings)


def test_firefox_relative_absolute_and_aliased_profiles(environment, tmp_path):
    touch(Path(environment["PROGRAMFILES"]) / "Mozilla Firefox/firefox.exe")
    root = Path(environment["APPDATA"]) / "Mozilla/Firefox"
    relative = root / "Profiles/abcd.default-release"
    relative.mkdir(parents=True)
    external = tmp_path / "external firefox"
    external.mkdir()
    (root / "profiles.ini").write_text(
        "[General]\nStartWithLastProfile=1\n"
        "[Profile0]\nName=default-release\nIsRelative=1\nPath=Profiles/abcd.default-release\n"
        f"[Profile1]\nName=External\nIsRelative=0\nPath={external}\n"
        "[Profile2]\nName=Alias\nIsRelative=1\nPath=Profiles/abcd.default-release\n"
        "[Profile3]\nName=Gone\nIsRelative=1\nPath=Profiles/missing\n"
        "[InstallABC]\nDefault=Profiles/abcd.default-release\n", encoding="utf-8")
    inventory = discover(environment)
    assert len(inventory.browsers) == 1
    assert len(inventory.profiles) == 2
    assert {profile.directory for profile in inventory.profiles} == {relative, external}
    assert any("without an available directory" in warning for warning in inventory.warnings)


def test_firefox_corrupt_and_invalid_relative_entries_are_reported(environment):
    touch(Path(environment["PROGRAMFILES"]) / "Mozilla Firefox/firefox.exe")
    root = Path(environment["APPDATA"]) / "Mozilla/Firefox"
    root.mkdir(parents=True)
    ini = root / "profiles.ini"
    ini.write_text("[bad", encoding="utf-8")
    assert any("malformed" in warning for warning in discover(environment).warnings)
    ini.write_text("[Profile0]\nPath=../../elsewhere\nIsRelative=1\n"
                   "[Profile1]\nPath=somewhere\nIsRelative=0\n"
                   "[Profile2]\nPath=somewhere\nIsRelative=oops\n", encoding="utf-8")
    inventory = discover(environment)
    assert not inventory.profiles
    assert any("outside its root" in warning for warning in inventory.warnings)
    assert any("non-absolute" in warning for warning in inventory.warnings)
    assert any("IsRelative" in warning for warning in inventory.warnings)


def test_all_supported_browser_roots_and_legacy_opera(environment):
    installations = [
        ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe", "LOCALAPPDATA", "Google/Chrome/User Data"),
        ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe", "LOCALAPPDATA", "Microsoft/Edge/User Data"),
        ("PROGRAMFILES", "BraveSoftware/Brave-Browser/Application/brave.exe", "LOCALAPPDATA", "BraveSoftware/Brave-Browser/User Data"),
        ("LOCALAPPDATA", "Vivaldi/Application/vivaldi.exe", "LOCALAPPDATA", "Vivaldi/User Data"),
        ("LOCALAPPDATA", "Programs/Opera/launcher.exe", "APPDATA", "Opera Software/Opera Stable"),
        ("LOCALAPPDATA", "Programs/Opera GX/launcher.exe", "APPDATA", "Opera Software/Opera GX Stable"),
    ]
    for exe_env, executable, profile_env, profile_path in installations:
        touch(Path(environment[exe_env]) / executable)
        root = Path(environment[profile_env]) / profile_path
        if "Opera" in profile_path:
            touch(root / "Preferences")
        else:
            (root / "Default").mkdir(parents=True)
    inventory = discover(environment)
    assert len(inventory.browsers) == len(installations)
    assert len(inventory.profiles) == len(installations)
    assert not inventory.warnings
    opera_ids = {browser.id for browser in inventory.browsers if browser.name.startswith("Opera")}
    assert all(profile.profile_directory == "" for profile in inventory.profiles if profile.browser_id in opera_ids)


def test_optional_managed_profile_keeps_separate_root_and_stable_identity(environment, tmp_path):
    _, root = chrome(environment)
    managed = tmp_path / "managed"
    (managed / "Default").mkdir(parents=True)
    inventory = discover(environment, managed_profile=managed)
    assert len(inventory.browsers) == 1
    assert len(inventory.profiles) == 2
    profile = next(profile for profile in inventory.profiles if profile.directory.parent == managed)
    assert profile.name.startswith("Brainless managed:")
    assert f"--user-data-dir={managed}" in profile_launch_arguments(inventory.browsers[0], profile, ["https://chatgpt.com/"])
    assert len(discover(environment, managed_profile=root).profiles) == 1


def test_missing_browsers_or_uninitialized_profiles_are_not_created(environment):
    assert discover(environment).browsers == []
    assert discover(environment).profiles == []
    executable = touch(Path(environment["LOCALAPPDATA"]) / "Google/Chrome/Application/chrome.exe")
    inventory = discover(environment)
    assert inventory.browsers[0].executable == executable
    assert not inventory.profiles
    assert any("no available profile" in warning for warning in inventory.warnings)
    assert not inventory.browsers[0].user_data_dir.exists()


def test_chromium_launch_preserves_profile_and_opens_one_visible_window(environment):
    executable, root = chrome(environment, ("Profile 1",))
    inventory = discover(environment)
    urls = ["https://chatgpt.com/", "https://gemini.google.com/app"]
    argv = profile_launch_arguments(inventory.browsers[0], inventory.profiles[0], urls)
    assert argv[0] == str(executable)
    assert argv.count("--new-window") == 1
    assert f"--user-data-dir={root}" in argv
    assert "--profile-directory=Profile 1" in argv
    assert "--force-renderer-accessibility" in argv
    assert argv[-2:] == urls
    assert not any("remote-debugging" in arg or "headless" in arg or "disable" in arg for arg in argv)


def test_firefox_launch_selects_exact_profile_and_one_window(tmp_path):
    browser = BrowserInstallation("firefox", "Firefox", "firefox", tmp_path / "firefox.exe", tmp_path)
    profile = BrowserProfile("profile", browser.id, "Personal", tmp_path / "actual-profile", "actual-profile")
    assert profile_launch_arguments(browser, profile, ["https://chatgpt.com/", "https://gemini.google.com/app"]) == [
        str(browser.executable), "-no-remote", "-profile", str(profile.directory),
        "-new-window", "https://chatgpt.com/", "-new-tab", "https://gemini.google.com/app"]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///private", "--no-sandbox", "https://a:b@example.com/", "https://example.com/\n"])
def test_launch_rejects_non_web_urls_and_flags(environment, url):
    chrome(environment)
    inventory = discover(environment)
    with pytest.raises(ValueError):
        profile_launch_arguments(inventory.browsers[0], inventory.profiles[0], [url])


def test_launch_rejects_a_profile_from_another_installation(environment):
    chrome(environment)
    inventory = discover(environment)
    browser = inventory.browsers[0]
    other = BrowserProfile("other", "wrong-browser", "Other", browser.user_data_dir / "Default", "Default")
    with pytest.raises(ValueError, match="does not belong"):
        profile_launch_arguments(browser, other, ["https://chatgpt.com/"])


def test_native_owner_marker_is_allowed_but_other_data_pages_are_rejected(environment):
    chrome(environment)
    inventory = discover(environment)
    browser, profile = inventory.browsers[0], inventory.profiles[0]
    marker = "data:text/html," + quote("<!doctype html><title>Brainless-Team-" + "a" * 32
                                      + "</title><p>Browser team starting</p>", safe="")
    assert profile_launch_arguments(browser, profile, [marker])[-1] == marker
    for url in ("data:text/html,<script>alert(1)</script>", marker + quote("<script>alert(1)</script>"),
                marker.replace("a" * 32, "not-a-token")):
        with pytest.raises(ValueError):
            profile_launch_arguments(browser, profile, [url])
