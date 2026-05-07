"""Render the worksheet HTML at A4 print size and emit:
- one PDF (using Chrome's print pipeline)
- per-page PNG screenshots that mirror the printed layout
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


# A4 in CSS pixels at 96 DPI: 210mm x 297mm
A4_WIDTH_PX = 794
A4_HEIGHT_PX = 1123


def render(html_path: Path, out_prefix: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": A4_WIDTH_PX, "height": A4_HEIGHT_PX})
        page = context.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")

        # Capture screen-media view (what the user sees in a browser)
        screen_png = out_prefix.parent / f"{out_prefix.stem}_screen.png"
        page.screenshot(path=str(screen_png), full_page=True)

        # Force print-media CSS rules so @page applies in screenshots too
        page.emulate_media(media="print")

        pdf_path = out_prefix.with_suffix(".pdf")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            prefer_css_page_size=True,
        )

        full_png = out_prefix.parent / f"{out_prefix.stem}_full.png"
        page.screenshot(path=str(full_png), full_page=True)

        body_height = page.evaluate("document.documentElement.scrollHeight")
        page_count = max(1, -(-body_height // A4_HEIGHT_PX))
        for i in range(page_count):
            png_path = out_prefix.parent / f"{out_prefix.stem}_page{i + 1}.png"
            page.set_viewport_size({"width": A4_WIDTH_PX, "height": A4_HEIGHT_PX})
            page.evaluate(f"window.scrollTo(0, {i * A4_HEIGHT_PX})")
            page.screenshot(path=str(png_path), full_page=False)
        browser.close()
        print(f"Wrote {pdf_path}; {page_count} screenshot(s) at {out_prefix.parent}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: screenshot_a4.py <input.html> <out_prefix_without_ext>")
        sys.exit(1)
    render(Path(sys.argv[1]), Path(sys.argv[2]))
