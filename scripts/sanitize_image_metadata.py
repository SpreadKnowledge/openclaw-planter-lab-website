#!/usr/bin/env python3
"""Strip metadata from public images in this repository.

Uses only the Python standard library.
- JPEG: strips APP1 Exif segments
- PNG: strips eXIf / tEXt / iTXt / zTXt chunks
"""

from __future__ import annotations

from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = [
    ROOT / "content" / "images",
    ROOT / "docs" / "assets" / "images",
]
JPEG_EXTS = {".jpg", ".jpeg", ".png"}
PNG_EXTS = {".png"}
PNG_STRIP_CHUNKS = {b"eXIf", b"tEXt", b"iTXt", b"zTXt"}


def strip_jpeg_exif(data: bytes) -> tuple[bytes, bool]:
    if not data.startswith(b"\xff\xd8"):
        return data, False
    out = bytearray(data[:2])
    i = 2
    changed = False
    while i < len(data):
        if data[i] != 0xFF:
            out.extend(data[i:])
            break
        j = i
        while j < len(data) and data[j] == 0xFF:
            j += 1
        if j >= len(data):
            out.extend(data[i:])
            break
        marker = data[j]
        if marker == 0xD9 or marker == 0xDA:
            out.extend(data[i:])
            break
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:
            out.extend(data[i : j + 1])
            i = j + 1
            continue
        if j + 2 >= len(data):
            out.extend(data[i:])
            break
        seg_len = struct.unpack(">H", data[j + 1 : j + 3])[0]
        seg_end = j + 1 + seg_len
        if seg_end > len(data):
            out.extend(data[i:])
            break
        payload = data[j + 3 : seg_end]
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            changed = True
        else:
            out.extend(data[i:seg_end])
        i = seg_end
    return bytes(out), changed


def strip_png_metadata(data: bytes) -> tuple[bytes, bool]:
    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig):
        return data, False
    out = bytearray(sig)
    i = len(sig)
    changed = False
    while i + 8 <= len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        ctype = data[i + 4 : i + 8]
        end = i + 12 + length
        if end > len(data):
            out.extend(data[i:])
            break
        chunk = data[i:end]
        if ctype in PNG_STRIP_CHUNKS:
            changed = True
        else:
            out.extend(chunk)
        i = end
        if ctype == b"IEND":
            break
    return bytes(out), changed


def sanitize_file(path: Path) -> bool:
    data = path.read_bytes()
    lower = path.suffix.lower()
    changed = False
    new_data = data
    if data.startswith(b"\xff\xd8") and lower in JPEG_EXTS:
        new_data, changed = strip_jpeg_exif(data)
    elif data.startswith(b"\x89PNG\r\n\x1a\n") and lower in PNG_EXTS:
        new_data, changed = strip_png_metadata(data)
    if changed and new_data != data:
        path.write_bytes(new_data)
    return changed


def iter_targets(paths: list[Path]):
    for base in paths:
        if base.is_file():
            yield base
            continue
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                yield path


def main() -> int:
    args = [Path(arg).resolve() for arg in sys.argv[1:]]
    targets = args if args else DEFAULT_TARGETS
    changed_paths: list[Path] = []
    for path in iter_targets(targets):
        try:
            if sanitize_file(path):
                changed_paths.append(path)
        except Exception as exc:
            print(f"ERROR {path}: {exc}", file=sys.stderr)
            return 1
    if changed_paths:
        for path in changed_paths:
            print(path.relative_to(ROOT))
    else:
        print("No metadata changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
