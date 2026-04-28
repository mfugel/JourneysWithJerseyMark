#!/usr/bin/env python3
"""
render_cards.py — Generate print-ready VistaPrint PDFs from the Jersey Mark
business card HTML templates.

Requirements (one-time setup):
    pip install playwright qrcode[pil]
    playwright install chromium

Run:
    python render_cards.py

Outputs (in the same folder as this script):
    jersey-mark-card-front.pdf   — 3.61" × 2.11", 1/16" bleed, 300+ DPI equivalent
    jersey-mark-card-back.pdf    — 3.61" × 2.11", 1/16" bleed, 300+ DPI equivalent

Upload BOTH to VistaPrint:
    - "Front" slot  → jersey-mark-card-front.pdf
    - "Back" slot   → jersey-mark-card-back.pdf
    Trim size: 3.5 × 2 in, bleed: 1/16 in all around, safe zone: 3.36 × 1.86 in.
"""

import base64
import io
import re
import sys
from pathlib import Path

# ---- Dependencies -----------------------------------------------------------

try:
    import qrcode
except ImportError:
    sys.exit(
        "ERROR: `qrcode` is not installed.\n"
        "  Run:  pip install qrcode[pil]"
    )

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "ERROR: `playwright` is not installed.\n"
        "  Run:  pip install playwright\n"
        "  Then: playwright install chromium"
    )

# ---- Config ----------------------------------------------------------------

HERE = Path(__file__).resolve().parent

FRONT_TEMPLATE = HERE / "print_front.html"
BACK_TEMPLATE  = HERE / "print_back.html"
LOGO_SVG       = HERE.parent / "images" / "jersey-mark-seal.svg"  # clean vector seal

FRONT_PDF = HERE / "jerseymarkcardfront.pdf"
BACK_PDF  = HERE / "jerseymarkcardback.pdf"

QR_URL = "https://JourneysWithJerseyMark.com"

# ---- Helpers ---------------------------------------------------------------

def load_logo_svg(svg_path: Path) -> str:
    """Read the SVG file and return it as inline markup for crisp vector rendering at any size."""
    if not svg_path.exists():
        sys.exit(f"ERROR: expected SVG logo at {svg_path}.")
    svg = svg_path.read_text(encoding="utf-8")
    # Strip any XML declaration so it embeds cleanly inside an HTML document.
    svg = re.sub(r'<\?xml[^?]*\?>\s*', '', svg)
    # Strip any DOCTYPE if present.
    svg = re.sub(r'<!DOCTYPE[^>]*>\s*', '', svg)
    return svg.strip()

def generate_qr_data_uri(url: str) -> str:
    """Generate a high-resolution QR code as a base64 PNG data URI."""
    qr = qrcode.QRCode(
        version=None,                       # auto-select smallest version that fits
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,                        # high-res: yields ~600-800px image
        border=0,                           # we provide our own parchment frame
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2c1a08", back_color="#f5ead0")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def render_pdf(html: str, out_path: Path, label: str) -> None:
    """Render a self-contained HTML string to a print-ready PDF at 3.61x2.11in."""
    print(f"[{label}] launching Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1083, "height": 633},     # 3.61 x 2.11 in at 300 DPI
            device_scale_factor=1,
        )
        page = context.new_page()
        print(f"[{label}] loading HTML + fonts...")
        page.set_content(html, wait_until="networkidle")

        # Give webfonts an extra beat to paint after load.
        page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(400)

        print(f"[{label}] rendering PDF -> {out_path.name}")
        page.pdf(
            path=str(out_path),
            width="3.61in",
            height="2.11in",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()
    size_kb = out_path.stat().st_size / 1024
    print(f"[{label}] done — {size_kb:.1f} KB")

# ---- Main ------------------------------------------------------------------

def main() -> None:
    if not FRONT_TEMPLATE.exists() or not BACK_TEMPLATE.exists():
        sys.exit(
            f"ERROR: missing templates.\n"
            f"  Expected: {FRONT_TEMPLATE.name} and {BACK_TEMPLATE.name} next to this script."
        )

    print("Loading SVG logo...")
    logo_svg = load_logo_svg(LOGO_SVG)
    print(f"  ok ({len(logo_svg):,} chars)")

    print(f"Generating QR code for: {QR_URL}")
    qr_uri = generate_qr_data_uri(QR_URL)
    print(f"  ok ({len(qr_uri):,} chars)")

    front_html = FRONT_TEMPLATE.read_text(encoding="utf-8")
    front_html = front_html.replace("__LOGO_SVG__",    logo_svg)
    front_html = front_html.replace("__QR_DATA_URI__", qr_uri)

    back_html = BACK_TEMPLATE.read_text(encoding="utf-8")

    render_pdf(front_html, FRONT_PDF, "front")
    render_pdf(back_html,  BACK_PDF,  "back ")

    print("\n✓ All done.")
    print(f"  {FRONT_PDF}")
    print(f"  {BACK_PDF}")
    print("\nUpload both to VistaPrint's 'Standard Business Cards' product,")
    print("choose the Matte finish, and you're set.")

if __name__ == "__main__":
    main()
