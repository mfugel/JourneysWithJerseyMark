"""Render the embroidery seal SVG to PNGs at the sizes Printify wants."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
SVG  = ROOT / "images" / "jersey-mark-seal-embroidery.svg"
SIZES = [500, 1500, 3000]  # px square; 3000 px @ 300 DPI = 10" — plenty for Printify

HTML = """<!doctype html><html><head><style>
html,body{{margin:0;padding:0;background:transparent}}
body{{display:flex;align-items:center;justify-content:center}}
svg{{width:{px}px;height:{px}px;display:block}}
</style></head><body>{svg}</body></html>"""

def main():
    svg_text = SVG.read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for px in SIZES:
            page = browser.new_page(viewport={"width": px, "height": px})
            page.set_content(HTML.format(px=px, svg=svg_text))
            out = ROOT / "images" / f"jersey-mark-seal-embroidery-{px}.png"
            page.screenshot(path=str(out), omit_background=True, full_page=False,
                            clip={"x":0,"y":0,"width":px,"height":px})
            print(f"wrote {out.name}  ({px}x{px})")
        browser.close()

if __name__ == "__main__":
    main()
