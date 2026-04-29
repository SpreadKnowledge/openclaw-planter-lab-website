#!/usr/bin/env python3
"""Basic public-repo safety checks for OpenClaw Planter Lab."""

from __future__ import annotations

from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".codex", ".venv", "__pycache__"}
FORBIDDEN_BASENAME_PATTERNS = [
    re.compile(r"^\.env($|\.)"),
    re.compile(r"^config\.(local|private)\.", re.I),
    re.compile(r"^settings\.(local|private)\.", re.I),
    re.compile(r"^credentials(\.|$)", re.I),
    re.compile(r"^secrets?(\.|$)", re.I),
]
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
STRONG_SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
IMAGE_DIRS = [ROOT / "content" / "images", ROOT / "docs" / "assets" / "images"]


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def has_forbidden_path(path: Path) -> str | None:
    name = path.name
    for pattern in FORBIDDEN_BASENAME_PATTERNS:
        if pattern.search(name):
            return f"forbidden filename pattern: {name}"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return f"forbidden sensitive suffix: {path.suffix.lower()}"
    return None


def looks_binary(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:2048]
    return b"\x00" in sample


def scan_text_for_secrets(path: Path) -> list[str]:
    findings: list[str] = []
    data = path.read_bytes()
    if looks_binary(data):
        return findings
    text = data.decode("utf-8", errors="ignore")
    for pattern in STRONG_SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"strong secret pattern matched: {pattern.pattern}")
    return findings


def jpeg_has_exif_or_gps(path: Path) -> tuple[bool, bool]:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        return False, False
    i = 2
    has_exif = False
    has_gps = False
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        i += 2
        if marker in (0xD9, 0xDA):
            break
        if i + 2 > len(data):
            break
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        seg = data[i + 2 : i + seg_len]
        if marker == 0xE1 and seg.startswith(b"Exif\x00\x00"):
            has_exif = True
            exif = seg[6:]
            if len(exif) >= 8 and exif[:2] in (b"II", b"MM"):
                le = exif[:2] == b"II"
                u16 = (lambda b: struct.unpack("<H", b)[0]) if le else (lambda b: struct.unpack(">H", b)[0])
                u32 = (lambda b: struct.unpack("<I", b)[0]) if le else (lambda b: struct.unpack(">I", b)[0])
                ifd0 = u32(exif[4:8])
                if 0 <= ifd0 + 2 <= len(exif):
                    n = u16(exif[ifd0 : ifd0 + 2])
                    base = ifd0 + 2
                    for idx in range(n):
                        off = base + idx * 12
                        if off + 12 > len(exif):
                            break
                        tag = u16(exif[off : off + 2])
                        if tag == 0x8825:
                            has_gps = True
                            break
        i += seg_len
    return has_exif, has_gps


def scan_images() -> list[str]:
    findings: list[str] = []
    for base in IMAGE_DIRS:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()[:8]
            if data.startswith(b"\xff\xd8"):
                has_exif, has_gps = jpeg_has_exif_or_gps(path)
                if has_exif or has_gps:
                    findings.append(
                        f"image metadata remains in {path.relative_to(ROOT)} (exif={has_exif}, gps={has_gps})"
                    )
    return findings


def main() -> int:
    findings: list[str] = []
    for path in iter_files():
        problem = has_forbidden_path(path)
        if problem:
            findings.append(f"{path.relative_to(ROOT)}: {problem}")
        findings.extend(f"{path.relative_to(ROOT)}: {item}" for item in scan_text_for_secrets(path))
    findings.extend(scan_images())
    if findings:
        print("Public safety check failed:")
        for item in findings:
            print(f"- {item}")
        return 1
    print("Public safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
