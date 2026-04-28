#!/usr/bin/env python3
"""
build_circular_logo.py — Generate the circular crest version of the Jersey Mark logo.

Reads:  ../images/jersey-mark-seal.svg  (your existing seal)
Writes: ../images/jersey-mark-seal-circular.svg  (new logo with URL ring)

The new logo wraps your seal inside a decorative ring with
"JourneysWithJerseyMark.com" curving across the top and
"ON THE ROAD SINCE MMXXI" on the bottom — matching the bottom
rule on your business cards. Transparent background, scales to any size.

Usage:
    python build_circular_logo.py
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_SEAL = HERE.parent / "images" / "jersey-mark-seal.svg"
OUTPUT_LOGO = HERE.parent / "images" / "jersey-mark-seal-circular.svg"

def main() -> None:
    if not SOURCE_SEAL.exists():
        sys.exit(f"ERROR: source seal not found at {SOURCE_SEAL}")

    seal_raw = SOURCE_SEAL.read_text(encoding="utf-8")
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', seal_raw, re.DOTALL)
    if not m:
        sys.exit("ERROR: couldn't parse seal SVG (no viewBox/svg block found)")

    seal_inner = m.group(2)

    logo = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        'viewBox="0 0 900 900" xmlns:xlink="http://www.w3.org/1999/xlink">\n'
        '  <defs>\n'
        '    <symbol id="seal" viewBox="0 0 500 500">' + seal_inner + '</symbol>\n'
        '    <path id="topArc" d="M 50,450 A 400,400 0 0,1 850,450" fill="none"/>\n'
        '    <path id="bottomArc" d="M 40,450 A 410,410 0 0,0 860,450" fill="none"/>\n'
        '  </defs>\n'
        '\n'
        '  <circle cx="450" cy="450" r="440" fill="none" stroke="#2c1a08" stroke-width="4"/>\n'
        '  <circle cx="450" cy="450" r="375" fill="none" stroke="#2c1a08" stroke-width="2.5"/>\n'
        '  <circle cx="450" cy="450" r="370" fill="none" stroke="#2c1a08" stroke-width="1"/>\n'
        '\n'
        '  <text font-family="Cinzel, Georgia, serif" font-size="44" font-weight="700" '
        'fill="#2c1a08" letter-spacing="2">\n'
        '    <textPath href="#topArc" startOffset="50%" text-anchor="middle">'
        'JourneysWithJerseyMark.com</textPath>\n'
        '  </text>\n'
        '  <text font-family="Cinzel, Georgia, serif" font-size="24" font-weight="700" '
        'fill="#2c1a08" letter-spacing="6">\n'
        '    <textPath href="#bottomArc" startOffset="50%" text-anchor="middle">'
        'ON THE ROAD SINCE MMXXI</textPath>\n'
        '  </text>\n'
        '\n'
        '  <g fill="#2c1a08">\n'
        '    <polygon points="20,450 48,440 48,460"/>\n'
        '    <polygon points="880,450 852,440 852,460"/>\n'
        '  </g>\n'
        '\n'
        '  <use href="#seal" x="90" y="90" width="720" height="720"/>\n'
        '</svg>\n'
    )

    OUTPUT_LOGO.write_text(logo, encoding="utf-8")
    size_kb = OUTPUT_LOGO.stat().st_size / 1024
    print(f"✓ Wrote {OUTPUT_LOGO.name} ({size_kb:.1f} KB)")
    print(f"  Location: {OUTPUT_LOGO}")

if __name__ == "__main__":
    main()
