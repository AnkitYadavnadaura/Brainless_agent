"""Optional local OCR fallback for screenshots when DOM extraction is unavailable."""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
from typing import Any
import shutil
import subprocess


class OcrUnavailable(RuntimeError):
    pass


class OcrReader:
    def __init__(self, *, timeout_seconds: float = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def read(self, image_path: Path) -> str:
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        return self.read_bytes(image_path.read_bytes())

    def read_bytes(self, image_bytes: bytes) -> str:
        """Read a captured viewport without retaining a screenshot on disk."""
        try:
            from PIL import Image
        except ImportError as error:
            raise OcrUnavailable("Install Pillow to enable OCR fallback") from error
        command = self._tesseract_command()
        if not command:
            raise OcrUnavailable("Install the local Tesseract executable to enable OCR fallback")
        # Pass arguments directly: pytesseract's Windows config parser preserves
        # quotes around tessdata paths, which prevents language data from loading.
        # stdin/stdout also avoids temporary screenshots containing private text.
        arguments = [command, "stdin", "stdout", "-l", "eng"]
        local_data = Path(__file__).resolve().parents[2] / "data" / "tessdata"
        if not os.environ.get("TESSDATA_PREFIX") and (local_data / "eng.traineddata").is_file():
            arguments.extend(["--tessdata-dir", str(local_data)])
        with Image.open(BytesIO(image_bytes)) as image:
            source = BytesIO()
            image.convert("RGB").save(source, format="PNG")
        try:
            result = subprocess.run(arguments, input=source.getvalue(), capture_output=True,
                timeout=self.timeout_seconds, shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except OSError as error:
            raise OcrUnavailable("Install the local Tesseract executable to enable OCR fallback") from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Tesseract timed out while reading the current screen") from error
        if result.returncode:
            raise OcrUnavailable("Tesseract could not read the image. Check its language data; "
                                 "English data belongs in data/tessdata/eng.traineddata or TESSDATA_PREFIX.")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def read_elements(self, image_bytes: bytes, min_confidence: float = 30.0, partitioned: bool = False) -> list[dict[str, Any]]:
        """Extract words and text blocks with bounding boxes: left, top, width, height, conf, text."""
        if partitioned:
            return self.read_elements_partitioned(image_bytes, min_confidence=min_confidence)
        try:
            from PIL import Image
        except ImportError as error:
            raise OcrUnavailable("Install Pillow to enable OCR fallback") from error
        command = self._tesseract_command()
        if not command:
            raise OcrUnavailable("Install the local Tesseract executable to enable OCR fallback")
        arguments = [command, "stdin", "stdout", "-l", "eng", "-c", "tessedit_create_tsv=1"]
        local_data = Path(__file__).resolve().parents[2] / "data" / "tessdata"
        if not os.environ.get("TESSDATA_PREFIX") and (local_data / "eng.traineddata").is_file():
            arguments.extend(["--tessdata-dir", str(local_data)])
        with Image.open(BytesIO(image_bytes)) as image:
            source = BytesIO()
            image.convert("RGB").save(source, format="PNG")
        try:
            result = subprocess.run(arguments, input=source.getvalue(), capture_output=True,
                timeout=self.timeout_seconds, shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except OSError as error:
            raise OcrUnavailable("Install the local Tesseract executable to enable OCR fallback") from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Tesseract timed out while reading the current screen") from error
        if result.returncode != 0:
            return []

        lines = result.stdout.decode("utf-8", errors="replace").strip().splitlines()
        if len(lines) <= 1:
            return []

        raw_words: list[dict[str, Any]] = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 12:
                continue
            text = parts[11].strip()
            if not text:
                continue
            try:
                conf = float(parts[10])
                left = int(parts[6])
                top = int(parts[7])
                width = int(parts[8])
                height = int(parts[9])
                block_num = int(parts[2])
                par_num = int(parts[3])
                line_num = int(parts[4])
            except (ValueError, IndexError):
                continue
            if conf < min_confidence or width <= 0 or height <= 0:
                continue
            raw_words.append({
                "text": text, "left": left, "top": top, "width": width, "height": height,
                "conf": conf, "block": block_num, "par": par_num, "line": line_num,
            })

        elements: list[dict[str, Any]] = []
        i = 0
        while i < len(raw_words):
            current = raw_words[i]
            phrase_words = [current["text"]]
            total_left = current["left"]
            total_top = current["top"]
            current_right = current["left"] + current["width"]
            max_bottom = current["top"] + current["height"]
            min_top = current["top"]
            conf_sum = current["conf"]
            count = 1

            j = i + 1
            while j < len(raw_words):
                next_word = raw_words[j]
                if (next_word["block"] == current["block"]
                        and next_word["par"] == current["par"]
                        and next_word["line"] == current["line"]
                        and 0 <= (next_word["left"] - current_right) <= 35):
                    phrase_words.append(next_word["text"])
                    current_right = next_word["left"] + next_word["width"]
                    max_bottom = max(max_bottom, next_word["top"] + next_word["height"])
                    min_top = min(min_top, next_word["top"])
                    conf_sum += next_word["conf"]
                    count += 1
                    j += 1
                else:
                    break

            phrase_text = " ".join(phrase_words)
            elements.append({
                "text": phrase_text,
                "left": total_left,
                "top": min_top,
                "width": current_right - total_left,
                "height": max_bottom - min_top,
                "conf": conf_sum / count,
            })
            if len(phrase_words) > 1:
                elements.append({
                    "text": current["text"],
                    "left": current["left"],
                    "top": current["top"],
                    "width": current["width"],
                    "height": current["height"],
                    "conf": current["conf"],
                })
            i = j
        return elements


    def read_elements_partitioned(
        self,
        image_bytes: bytes,
        min_confidence: float = 30.0,
        grid: tuple[int, int] = (2, 2),
        overlap_ratio: float = 0.15,
    ) -> list[dict[str, Any]]:
        """Divide the screenshot into multiple smaller parts/tiles to detect exact coordinates of text, buttons, etc.

        Args:
            image_bytes: Raw PNG/JPEG screenshot bytes.
            min_confidence: Minimum OCR confidence threshold (0-100).
            grid: (columns, rows) partition count, e.g. (2, 2) creates 4 quadrants.
            overlap_ratio: Overlap percentage (e.g. 0.15 = 15%) to avoid cutting words at seams.
        """
        try:
            from PIL import Image
        except ImportError as error:
            raise OcrUnavailable("Install Pillow to enable OCR fallback") from error

        with Image.open(BytesIO(image_bytes)) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                return []

            cols, rows = max(1, grid[0]), max(1, grid[1])
            if (cols == 1 and rows == 1) or width < 400 or height < 300:
                return self.read_elements(image_bytes, min_confidence=min_confidence)

            tile_w = width / cols
            tile_h = height / rows
            pad_x = int(tile_w * overlap_ratio)
            pad_y = int(tile_h * overlap_ratio)

            all_elements: list[dict[str, Any]] = []

            for r in range(rows):
                for c in range(cols):
                    x1 = max(0, int(c * tile_w) - pad_x)
                    y1 = max(0, int(r * tile_h) - pad_y)
                    x2 = min(width, int((c + 1) * tile_w) + pad_x)
                    y2 = min(height, int((r + 1) * tile_h) + pad_y)

                    tile_img = image.crop((x1, y1, x2, y2))
                    tile_buf = BytesIO()
                    tile_img.convert("RGB").save(tile_buf, format="PNG")
                    tile_elements = self.read_elements(tile_buf.getvalue(), min_confidence=min_confidence)

                    for elem in tile_elements:
                        all_elements.append({
                            "text": elem["text"],
                            "left": elem["left"] + x1,
                            "top": elem["top"] + y1,
                            "width": elem["width"],
                            "height": elem["height"],
                            "conf": elem["conf"],
                            "partition": f"{c}x{r}",
                        })

        # Also run whole-image extraction for wide banners or cross-tile headings
        full_elements = self.read_elements(image_bytes, min_confidence=min_confidence)
        for elem in full_elements:
            all_elements.append({**elem, "partition": "full"})

        # Deduplicate overlapping detections (IoU > 0.35 and matching text)
        return self._deduplicate_elements(all_elements)

    @staticmethod
    def _deduplicate_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate overlapping elements across tiles and full-image scans."""
        if not elements:
            return []

        sorted_elements = sorted(elements, key=lambda x: x.get("conf", 0.0), reverse=True)
        unique: list[dict[str, Any]] = []

        def iou(box1, box2):
            x1 = max(box1["left"], box2["left"])
            y1 = max(box1["top"], box2["top"])
            x2 = min(box1["left"] + box1["width"], box2["left"] + box2["width"])
            y2 = min(box1["top"] + box1["height"], box2["top"] + box2["height"])
            inter_w = max(0, x2 - x1)
            inter_h = max(0, y2 - y1)
            inter_area = inter_w * inter_h
            area1 = box1["width"] * box1["height"]
            area2 = box2["width"] * box2["height"]
            union_area = area1 + area2 - inter_area
            return inter_area / union_area if union_area > 0 else 0.0

        for candidate in sorted_elements:
            cand_text = candidate["text"].strip().casefold()
            duplicate = False
            for kept in unique:
                overlap = iou(candidate, kept)
                kept_text = kept["text"].strip().casefold()
                if overlap > 0.35 and (cand_text == kept_text or cand_text in kept_text or kept_text in cand_text):
                    duplicate = True
                    break
            if not duplicate:
                unique.append(candidate)

        return sorted(unique, key=lambda x: (x["top"], x["left"]))

    @staticmethod
    def _tesseract_command() -> str | None:
        configured = os.environ.get("TESSERACT_CMD")
        if configured:
            if not Path(configured).is_file():
                raise OcrUnavailable("TESSERACT_CMD does not point to a local Tesseract executable")
            return configured
        found = shutil.which("tesseract")
        if found:
            return found
        if os.name == "nt":
            for directory in (os.environ.get("ProgramFiles", "C:/Program Files"),
                              os.environ.get("LOCALAPPDATA", "") + "/Programs"):
                candidate = Path(directory) / "Tesseract-OCR" / "tesseract.exe"
                if candidate.is_file():
                    return str(candidate)
        return None
