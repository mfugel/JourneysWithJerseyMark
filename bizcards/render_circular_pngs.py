#!/usr/bin/env python3
"""
render_circular_pngs.py — Render the circular crest logo to transparent PNGs.

Reads:  ../images/jersey-mark-seal-circular.svg
Writes: ../images/jersey-mark-seal-circular-500.png
        ../images/jersey-mark-seal-circular-1500.png
        ../images/jersey-mark-seal-circular-3000.png

Uses Playwright (already installed for render_cards.py) to render the SVG
through Chromium — this loads Google Fonts properly so the Cinzel text
appears as it does in the browser, not as a fallback serif.

Usage:
    python render_circular_pngs.py
"""

import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "ERROR: playwright is not installed.\n"
        "  Run:  pip install playwright\n"
        "  Then: playwright install chromium"
    )

HERE = Path(__file__).resolve().parent
SVG_PATH = HERE.parent / "images" / "jersey-mark-seal-circular.svg"
IMAGES_DIR = HERE.parent / "images"
SIZES = [500, 1500, 3000]

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&display=swap" rel="stylesheet">
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; }}
  .wrap {{ width: {size}px; height: {size}px; }}
  .wrap svg {{ width: 100%; height: 100%; display: block; }}
</style>
</head><body>
<div class="wrap">{svg}</div>
</body></html>
"""

def main() -> None:
    if not SVG_PATH.exists():
        sys.exit(
            f"ERROR: source SVG not found at {SVG_PATH}\n"
            f"  Run `python build_circular_logo.py` first to generate it."
        )

    svg_markup = SVG_PATH.read_text(encoding="utf-8")
    # Strip XML declaration so it embeds cleanly inside HTML.
    if svg_markup.lstrip().startswith("<?xml"):
        svg_markup = svg_markup.split("?>", 1)[1].lstrip()

    print("Launching Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for size in SIZES:
            html = HTML_TEMPLATE.format(size=size, svg=svg_markup)
            context = browser.new_context(
                viewport={"width": size, "height": size},
                device_scale_factor=1,
            )
            page = context.new_page()
            page.set_content(html, wait_until="networkidle")
            # Wait for fonts to be ready before snapshot.
            page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
            page.wait_for_timeout(500)

            out_path = IMAGES_DIR / f"jersey-mark-seal-circular-{size}.png"
            page.screenshot(
                path=str(out_path),
                omit_background=True,    # transparent PNG
                full_page=False,
                clip={"x": 0, "y": 0, "width": size, "height": size},
            )
            context.close()
            kb = out_path.stat().st_size / 1024
            print(f"  ✓ {out_path.name} ({size}x{size}, {kb:.1f} KB)")

        browser.close()

    print("\nDone. Files written to:")
    print(f"  {IMAGES_DIR}")

if __name__ == "__main__":
    main()
