"""Embed Euro asset images as Base64 data URIs into web/arbeitsblatt.html.

Replaces everything between the markers
    /* BEGIN_ASSETS */
    /* END_ASSETS */
with a JavaScript object literal mapping filename -> data URI.

Run once after pulling the repo, or whenever assets change.

Usage: python tools/build_web_assets.py
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets" / "euro"
HTML_PATH = ROOT / "web" / "arbeitsblatt.html"

EXT_TO_MIME = {
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def file_to_data_uri(path: Path) -> str:
    mime = EXT_TO_MIME.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"Unsupported asset extension: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def collect_assets() -> dict[str, str]:
    assets: dict[str, str] = {}
    for sub in ("coins", "banknotes"):
        sub_dir = ASSETS_DIR / sub
        if not sub_dir.is_dir():
            continue
        for path in sorted(sub_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in EXT_TO_MIME:
                key = f"{sub}/{path.name}"
                assets[key] = file_to_data_uri(path)
    return assets


def render_block(assets: dict[str, str]) -> str:
    lines = ["/* BEGIN_ASSETS */", "const ASSETS = {"]
    for key, uri in assets.items():
        # data URIs contain no single quotes so we can wrap them safely.
        lines.append(f"  '{key}': '{uri}',")
    lines.append("};")
    lines.append("/* END_ASSETS */")
    return "\n".join(lines)


def main() -> None:
    if not HTML_PATH.is_file():
        raise SystemExit(f"Expected file not found: {HTML_PATH}")
    assets = collect_assets()
    if not assets:
        raise SystemExit(f"No assets found under {ASSETS_DIR}")
    html = HTML_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"/\* BEGIN_ASSETS \*/.*?/\* END_ASSETS \*/", re.DOTALL
    )
    if not pattern.search(html):
        raise SystemExit(
            "Could not find /* BEGIN_ASSETS */ ... /* END_ASSETS */ markers in HTML"
        )
    new_block = render_block(assets)
    html = pattern.sub(new_block, html)
    HTML_PATH.write_text(html, encoding="utf-8")
    total_kb = sum(len(v) for v in assets.values()) // 1024
    print(f"Embedded {len(assets)} assets (~{total_kb} KB base64) into {HTML_PATH}")


if __name__ == "__main__":
    main()
