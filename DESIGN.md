# DESIGN.md — Journeys with Jersey Mark brand & UI contract

A single source of truth for how **journeyswithjerseymark.com** looks and feels.
Read this before building or changing any UI so new work matches the site and
doesn't drift toward a generic template.

> **Pattern note:** this is a lightweight "brand contract" (idea borrowed from
> nexu-io/open-design, 2026-06-26) — plain Markdown, no tooling. It just keeps
> the design system written down in one place.

---

## 1. Essence

A **vintage parchment / antique-cartography** theme — the site reads like an
old explorer's map and field journal. Voice is poetic, contemplative, unhurried
(*"Nomad · Adventurer · Chronicler of Roads"*; motto **"Codiwomple"** — to travel
purposefully toward a vague destination). Image-forward, introspective, warm.

This aesthetic is **deliberate and distinct** — do **not** borrow styles from the
sibling sites (TapIntoYourJoy's clean cream editorial). Keep them separate.

---

## 2. Typography (Google Fonts)

- **Display / titles / nav / labels:** **Cinzel** — `'Cinzel', serif`, usually
  `font-weight:700`, UPPERCASE, wide letter-spacing (0.06–0.15em). Engraved,
  monumental, map-cartouche feel.
- **Subtitles / mottos / captions / "voice":** **IM Fell English** —
  `'IM Fell English', serif`, almost always *italic*. The antique, hand-set
  flavor.
- **Body / prose:** **Crimson Text** — `'Crimson Text', serif`. Readable old-
  style book serif.

Keep the three roles consistent: Cinzel = signage, IM Fell English = voice,
Crimson Text = reading.

---

## 3. Color — the parchment palette

There is no CSS-variable token system here; colors are hardcoded hex in the
inline `<style>`. Stay within this palette (warm browns + parchment + a little
gilt):

| Role | Hex |
|---|---|
| Parchment background | `#dfc99a` |
| Near-black ink (headings/strong) | `#0f0800` |
| Dark sepia ink (body/secondary) | `#1a0f00` |
| Light cream (text on dark, seals) | `#f5ead0` |
| Rule / border / frame | `#7a4e20` |
| Mid leather (buttons, thumbs bg) | `#5a3510` |
| Darkest leather (button borders, tips) | `#3a1f08` |
| Gilt accent (coffee/support links) | `#f8d568` (hover `#ffe89a`) |
| Tinted fills | `rgba(160,110,50,0.1–0.3)` over parchment |

Backgrounds layer two fixed overlays for texture: a faint grid
`.parchment-bg` and a `.vignette` radial darkening at the edges. Keep them.

---

## 4. Motifs (the cartography vocabulary)

These recurring devices ARE the brand — reuse them rather than inventing new chrome:

- **Cartouche borders** (`.cartouche-border`) — elliptical map-label frames with
  `— ✦ —` flourishes.
- **Compass rose** (`.compass-rose`) and **corner ornaments**.
- **Divider rules** (`.divider-rule`) — centered hairline rules with spaced glyphs.
- **Legend boxes** (`.legend-box`) — framed panels with a small Cinzel caption
  notched into the top border, like a map legend.
- **Symbolic markers:** ✦ and ✕ as ornaments/bullets.
- **Seals & footer** in IM Fell English italic.

---

## 5. Components & conventions

- **Single-file deploy.** The whole page is `index.html` with inline `<style>`
  and `<script>`. **Don't split CSS/JS into separate files** unless asked.
- Sticky top nav (`.site-nav`) on a translucent leather bar
  (`rgba(90,53,16,0.96)` + blur), Cinzel uppercase links.
- Support/commerce CTAs (`.coffee-btn`, `.shop-btn`) are leather buttons with the
  gilt accent for the Ko-fi link.
- Galleries use framed thumbnails (`.gallery-item`, 1px `#7a4e20` border) and a
  dark lightbox.
- Note: this repo is more than the static page — there's a Python pipeline
  (`build_journeys_page.py`, `build_travel_heatmap.py`) that regenerates
  `journeys.html`/data, plus `admin.html` for the Google-Photos slideshow
  workflow. Prefer editing the build scripts over hand-editing generated HTML.

---

## 6. Hard rules

- **`.gitattributes` enforces LF** — preserve Unix line endings even on Windows.
- **Don't cross-pollinate** the TapIntoYourJoy aesthetic into this site.
- Keep the poetic, map-maker voice in public-facing copy (plain/direct is fine
  for admin tooling).

---

*Keep this file in sync if the theme changes. Pairs with the project notes in
the repo's `CLAUDE.md`/`README`.*
