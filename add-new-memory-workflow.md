# Add a New Memory — Workflow Guide
### Journeys with Jersey Mark · journeyswithjerseymark.com

---

## Overview

This is the procedure for adding a new photo album to the "Memories from the Road" slideshow on the website.

> **Important:** The old web_fetch method no longer works. Google Photos stopped embedding photo URLs in the initial HTML. The correct method uses the **Claude in Chrome** browser extension to extract URLs from the live rendered page.

---

## Requirements

- **Chrome** browser (must be Chrome — not DuckDuckGo, Firefox, Safari, etc.)
- **Claude in Chrome** extension installed and connected
- **Claude.ai must be open in Chrome** (not another browser) for the extension to pair

---

## Step 1 — Connect the Chrome Extension

1. Open **Chrome** and navigate to **claude.ai** — open this conversation there
2. Click the **puzzle piece icon** (Extensions) in the Chrome toolbar
3. Click the **Claude** extension to open its popup
4. Click **Connect** in the popup
5. Tell Claude "try now" — Claude will confirm the connection

> If Claude can't connect, check that the extension is enabled at chrome://extensions

---

## Step 2 — Give Claude the Album Link

Type something like:

```
add a new memory to my site https://photos.app.goo.gl/YOURLINK
```

Claude will:
1. Navigate to the full photos.google.com album URL via the Chrome extension
2. Wait for the page to load and scroll to trigger lazy-loaded photos
3. Run JavaScript to extract all lh3.googleusercontent.com/pw/ URLs from the page's script data
4. Pick **25 evenly spaced photos** from the full album
5. Strip existing size suffixes and append =w1200-h900-no to each URL
6. **Trigger a browser download** of a .txt file with all 25 URLs

> Note: Short photos.app.goo.gl links are blocked by the extension — Claude resolves the full URL automatically.
> Note: Always verify photo URLs end in `-no`. Truncated URLs cause silent JSON parse failures.
> Note: Google Photos URLs expire after a few weeks — always get fresh URLs from the live page, never reuse old ones.

---

## Step 3 — Add the Album via the Admin Page

1. Open the downloaded .txt file in Notepad — Ctrl+A, Ctrl+C to copy all
2. Go to: **https://journeyswithjerseymark.com/admin.html**
3. Enter your GitHub Personal Access Token → click **"Enter the Chart Room"**
   *(Check "Remember on this device" so you only need to do this once per device)*
4. Fill in:
   - **Album Title** — use Claude's suggestion or edit it
   - **Google Photos Share Link** — the photos.app.goo.gl URL
   - **Photo URLs** — paste the full list from the downloaded .txt file
5. Click **+ Add Album**
6. Verify the album appears in the **"Current Albums on Site"** list
7. Click **Save & Publish to Site**
8. Wait about 30 seconds — the site updates automatically

---

## Step 4 — Verify on the Live Site

1. Go to **journeyswithjerseymark.com**
2. Scroll to the **"Memories from the Road"** section
3. Open the dropdown — your new album should appear
4. Select it and confirm photos load and cycle correctly

---

## Managing Existing Albums

From the admin page you can also:

| Action | How |
|--------|-----|
| **Reorder** | Use the ▲ ▼ arrows next to each album |
| **Remove** | Click the ✕ button to delete an album |
| **Edit photos** | Click "✎ Edit Photos" to update the photo URLs for an album |

Always click **Save & Publish to Site** after making any changes.

---

## Troubleshooting

**Photos not loading / blank slideshow**
The photo URLs have likely expired (Google Photos URLs expire after a few weeks). Ask Claude to re-fetch the album using the Chrome extension procedure above to get fresh URLs, then use Edit Photos in admin.html to replace them.

**Only 2 albums showing in the dropdown**
The albums.json file likely has a broken (truncated) URL. Open admin.html, check each album's photo list for any URL that doesn't end in -no, fix it via Edit Photos, and save.

**Save & Publish shows an error**
Your GitHub token may have expired. Go to github.com/settings/tokens, regenerate it with the repo scope, and re-enter it on the admin page.

**Duplicate album in the dropdown**
Open admin.html, find the duplicate in the Current Albums list, click ✕ to remove it, then Save & Publish.

**Chrome extension not connecting**
- Make sure Claude.ai is open in Chrome (not another browser)
- Click the extension puzzle piece → Claude → Connect in the popup
- Check chrome://extensions that the Claude extension is enabled
- Try refreshing the Claude.ai tab and reconnecting

---

## GitHub Token Setup (one time per device)

1. Go to: **github.com/settings/tokens/new**
2. Note: `Jersey Mark Admin`
3. Expiration: No expiration (or set a long one)
4. Scope: Check only **repo**
5. Click **Generate token** — copy it immediately (only shown once)
6. Paste it into the admin page and check **"Remember on this device"**

---

## Key Links

| | |
|--|--|
| **Site** | https://journeyswithjerseymark.com |
| **Admin page** | https://journeyswithjerseymark.com/admin.html |
| **GitHub repo** | https://github.com/mfugel/JourneysWithJerseyMark |
| **Token page** | https://github.com/settings/tokens |

---

## Albums Added to Date

| Album Title | Notes |
|-------------|-------|
| Painted Rocks Michigan 2023 | |
| Fortuna Lake Yuma Arizona 2023 | |
| McCarthy/Kennecott/Root Glacier Alaska 2023 | |
| Baja Mexico 2023 | |
| Idaho Summer 2025 | |
| Grayton Beach Florida 2024 | |
| The Gulf Florabama/Mississippi/Louisiana 2022 | |
| Whale Magic Baja Mexico 2023 | |
| Joshua Tree National Park 2025 | Added May 2026 — 25 photos via Chrome extension method |

---

*Last updated: May 2026*
