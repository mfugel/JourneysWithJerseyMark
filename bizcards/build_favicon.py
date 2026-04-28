#!/usr/bin/env python3
"""
build_favicon.py — Generate the full favicon set for journeyswithjerseymark.com.

Design: uses the actual Jersey Mark seal (../images/jersey-mark-seal.svg)
shrunk to favicon sizes. The fine detail (text, banners) won't be readable
at 16-32px, but the silhouette and color signature stay recognizable. At
180/192/512 (home screen / PWA sizes) the full seal reads cleanly.

Writes to ../images/:
  favicon-16.png              (browser tab)
  favicon-32.png              (browser tab, HiDPI)
  favicon-180.png             (iOS home screen / Apple touch icon)
  favicon-192.png             (Android home screen)
  favicon-512.png             (PWA / app icon)
  favicon.ico                 (16/32/48 multi-res ICO for legacy browsers)

Note: no favicon.svg is generated — your existing jersey-mark-seal.svg
serves as the master vector source.

Uses Playwright (already installed for render_cards.py) to render PNGs through
Chromium — no extra system libraries needed.

Requires:
  pip install playwright pillow
  playwright install chromium

Usage:
  python build_favicon.py
"""

import sys
import io
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "ERROR: playwright not installed.\n"
        "  Run:  pip install playwright\n"
        "  Then: playwright install chromium"
    )

try:
    from PIL import Image
except ImportError:
    sys.exit("ERROR: Pillow not installed.  Run:  pip install pillow")

HERE = Path(__file__).resolve().parent
IMAGES_DIR = HERE.parent / "images"
SOURCE_SEAL = IMAGES_DIR / "jersey-mark-seal.svg"

PNG_SIZES = [16, 32, 180, 192, 512]
ICO_SIZES = [16, 32, 48]

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; }}
  .wrap {{
    width: {size}px;
    height: {size}px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .wrap svg {{
    width: 100%;
    height: 100%;
    display: block;
  }}
</style>
</head><body>
<div class="wrap">{svg}</div>
</body></html>
"""

def render_png(browser, svg_str: str, size: int) -> bytes:
    """Render the SVG at the given size as a transparent PNG via Chromium."""
    # Strip XML declaration so the SVG embeds cleanly inside HTML.
    svg_for_html = svg_str
    if svg_for_html.lstrip().startswith("<?xml"):
        svg_for_html = svg_for_html.split("?>", 1)[1].lstrip()
    # Strip DOCTYPE if present
    if svg_for_html.lstrip().startswith("<!DOCTYPE"):
        svg_for_html = svg_for_html.split(">", 1)[1].lstrip()

    html = HTML_TEMPLATE.format(size=size, svg=svg_for_html)
    context = browser.new_context(
        viewport={"width": size, "height": size},
        device_scale_factor=1,
    )
    page = context.new_page()
    page.set_content(html, wait_until="networkidle")
    png_bytes = page.screenshot(
        omit_background=True,
        full_page=False,
        clip={"x": 0, "y": 0, "width": size, "height": size},
    )
    context.close()
    return png_bytes

def main() -> None:
    if not IMAGES_DIR.exists():
        sys.exit(f"ERROR: images folder not found at {IMAGES_DIR}")
    if not SOURCE_SEAL.exists():
        sys.exit(f"ERROR: source seal not found at {SOURCE_SEAL}")

    seal_svg = SOURCE_SEAL.read_text(encoding="utf-8")
    print(f"Source: {SOURCE_SEAL.name} ({SOURCE_SEAL.stat().st_size:,} B)")

    print("Launching Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Render each PNG size
        for size in PNG_SIZES:
            png_bytes = render_png(browser, seal_svg, size)
            out_path = IMAGES_DIR / f"favicon-{size}.png"
            out_path.write_bytes(png_bytes)
            print(f"  \u2713 {out_path.name} ({size}x{size}, {len(png_bytes):,} B)")

        # Build the multi-resolution favicon.ico (16/32/48 in one file)
        ico_images = []
        for size in ICO_SIZES:
            png_bytes = render_png(browser, seal_svg, size)
            ico_images.append(Image.open(io.BytesIO(png_bytes)).convert("RGBA"))

        ico_path = IMAGES_DIR / "favicon.ico"
        ico_images[0].save(
            ico_path,
            format="ICO",
            sizes=[(s, s) for s in ICO_SIZES],
            append_images=ico_images[1:],
        )
        print(f"  \u2713 {ico_path.name} (multi-res {ICO_SIZES}, {ico_path.stat().st_size:,} B)")

        browser.close()

    print()
    print("Done.")
    print()
    print("To wire these up, add to <head> in index.html:")
    print('  <link rel="icon" type="image/svg+xml" href="/images/jersey-mark-seal.svg">')
    print('  <link rel="icon" type="image/x-icon" href="/images/favicon.ico">')
    print('  <link rel="icon" type="image/png" sizes="32x32" href="/images/favicon-32.png">')
    print('  <link rel="icon" type="image/png" sizes="16x16" href="/images/favicon-16.png">')
    print('  <link rel="apple-touch-icon" sizes="180x180" href="/images/favicon-180.png">')

if __name__ == "__main__":
    main()
