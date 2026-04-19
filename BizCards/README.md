# Jersey Mark Business Card — Print Conversion

Four files, one script, two PDFs out. That's the whole thing.

## The layout

- **Front (QR side)** — Jersey Mark seal, name, aka line, role tagline, and a large QR code linking to JourneysWithJerseyMark.com. This is the "identity" side.
- **Back (Contact side)** — "One Man's Quest for Health & Happiness" quote header, then all 8 unique contact methods: Dispatch (email), Telegraph (phone), WhatsApp, Voyage (YouTube), Facebook, Chart (FindPenguins), Vessel (RV), Post (mailing address). The web page isn't listed separately because the QR already points there.

## What's in this bundle

| File | Purpose |
|---|---|
| `render_cards.py`      | Render script — run this |
| `print_front.html`     | Print-ready front template (3.61" × 2.11" with bleed) |
| `print_back.html`      | Print-ready back template (3.61" × 2.11" with bleed) |
| `capture_front.html`   | Your original file — needed so the script can pull out the embedded seal logo |

`capture_back.html` is not needed for rendering (the print_back.html is already complete and standalone).

## Setup (one time)

You'll need Python 3.9+ and these two packages:

```bash
pip install playwright "qrcode[pil]"
playwright install chromium
```

The `playwright install chromium` step downloads a headless browser (~150 MB). This is what renders the HTML to PDF with real Google Fonts.

## Run

From the folder containing all four files:

```bash
python render_cards.py
```

Expected output:

```
Extracting logo from original HTML...
  ok (57,070 chars)
Generating QR code for: https://JourneysWithJerseyMark.com
  ok (~6,000 chars)
[front] launching Chromium...
[front] loading HTML + fonts...
[front] rendering PDF -> jersey-mark-card-front.pdf
[front] done — ~80 KB
[back ] launching Chromium...
[back ] loading HTML + fonts...
[back ] rendering PDF -> jersey-mark-card-back.pdf
[back ] done — ~40 KB

✓ All done.
```

Two PDFs land next to the script: `jersey-mark-card-front.pdf` and `jersey-mark-card-back.pdf`.

## Eyeball the PDFs before uploading

Open them in any PDF viewer. Check:
- The parchment background reaches all four edges (no white borders)
- The decorative brown border is visible and complete, well inside the page
- Name, email, phone, QR code — all look correct and aren't touching edges
- QR code: scan it with your phone. It should open `JourneysWithJerseyMark.com`

A handy mental model: VistaPrint will trim 1/16" (≈1.6 mm) off every edge. Anything that crosses the outer edge of your PDF is bleed and will be cut away. That's intentional — it's what prevents white slivers if the cut drifts.

## Upload to VistaPrint

1. Go to Standard Business Cards → Upload Your Complete Design
2. Choose **Matte** finish (your vintage aesthetic calls for it)
3. Choose 3.5 × 2 in, standard rectangle, 14pt stock (or upgrade as you like)
4. When asked to upload, their flow has two slots:
   - **Front**: upload `jersey-mark-card-front.pdf`
   - **Back**: upload `jersey-mark-card-back.pdf`
5. VistaPrint's preview will show the bleed / trim / safe guides over your design. Verify:
   - Parchment fills the full bleed area (to the outermost guide)
   - All text and the QR code sit inside the innermost (safe) guide
6. Accept and order.

## If something looks off

- **Fonts look generic (Times-like instead of Cinzel)** → Make sure your machine has internet while the script runs. The templates fetch Google Fonts at render time. No connection = fallback serif.
- **QR code missing or blank** → `qrcode[pil]` didn't install. Re-run the pip line; the `[pil]` part matters.
- **PDF is blank or tiny** → `playwright install chromium` didn't finish. Re-run it; it needs to actually download the browser.
- **Want a different QR target** → Edit `QR_URL` near the top of `render_cards.py` and re-run.

## Specs baked into the PDFs

- Page size: 3.61 × 2.11 in (trim 3.5 × 2 in + 1/16 in bleed per VistaPrint)
- Safe zone: 3.36 × 1.86 in — all critical content sits inside this
- Color mode: RGB (VistaPrint converts to CMYK at print time)
- Fonts: embedded by Chromium's PDF engine, so the files are self-contained
- Backgrounds: set with `print-color-adjust: exact` so the parchment color prints
