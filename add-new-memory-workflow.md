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
- **Claude.ai must be open in Chrome** — this is critical. The extension only pairs with Claude when you are chatting in Chrome, not in another browser.

---

## Step 1 — Open Claude.ai in Chrome

1. Open **Chrome**
2. Go to **claude.ai** and open (or continue) your conversation with Claude
3. Click the **puzzle piece icon** (Extensions) in the Chrome toolbar
4. Click the **Claude** extension to open its popup
5. Click **Connect** in the popup
6. Tell Claude "try now" — Claude will confirm the connection

> **If Claude says it's not connected:** Go to `chrome://extensions`, find Claude, click Details, make sure the extension is enabled and "Allow access to file URLs" is toggled on. Then click the extension icon → Connect again.

> **If the connection drops mid-session:** Just click the extension icon → Connect again, then tell Claude "try now." This happens occasionally and is a quick fix.

---

## Step 2 — Give Claude the Album Link

In the Claude.ai chat (in Chrome), type something like:

```
add a new memory to my site https://photos.app.goo.gl/YOURLINK
```

Or just paste the Google Photos link and Claude will know what to do.

Claude will automatically:
1. Resolve the short link to the full `photos.google.com` URL
2. Navigate to the album in your Chrome browser via the extension
3. Wait for the page to fully load and scroll to trigger lazy-loaded photos
4. Run JavaScript to extract all `lh3.googleusercontent.com/pw/` URLs from the page's script data
5. Pick **25 evenly spaced photos** from the full album
6. Strip existing size suffixes and append `=w1200-h900-no` to each URL
7. **Trigger a browser download** of a `.txt` file named after the album

> **Note:** Short `photos.app.goo.gl` links are blocked by the extension — Claude resolves the full URL automatically via a quick web fetch first.
> **Note:** Always verify photo URLs end in `-no`. Truncated URLs cause silent JSON parse failures.
> **Note:** Google Photos URLs expire after a few weeks — always get fresh URLs from the live page, never reuse old ones from a previous session.

---

## Step 3 — Add the Album via the Admin Page

1. Open the downloaded `.txt` file in Notepad — **Ctrl+A** → **Ctrl+C** to copy all
2. Go to: **https://journeyswithjerseymark.com/admin.html**
3. Enter your GitHub Personal Access Token → click **"Enter the Chart Room"**
   *(Check "Remember on this device" so you only need to do this once per device)*
4. Scroll down to the **green "Add a New Album" section** and fill in:
   - **Album Title** — use Claude's suggestion or edit it
   - **Google Photos Share Link** — the `photos.app.goo.gl` URL
   - **Photo URLs** — paste the full list from the downloaded `.txt` file
5. Click **+ Add Album** (green button)
6. Verify the album appears in the **"Current Albums on Site"** list above
7. Click **💾 Save & Publish to Site**
8. Wait about 30 seconds — the site updates automatically via Vercel

---

## Step 4 — Verify on the Live Site

1. Go to **journeyswithjerseymark.com**
2. Scroll to the **"Memories from the Road"** section
3. Open the dropdown — your new album should appear
4. Select it and confirm photos load and cycle correctly
5. Click **"Open Album ↗"** to confirm the Google Photos link works

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

**Wrong photos showing (e.g. previous album's photos)**
The album was saved with stale URLs from a previous session. Use Edit Photos in admin.html, delete all URLs, and paste in the fresh ones from a new `.txt` download.

**Only 2 albums showing in the dropdown**
The `albums.json` file likely has a broken (truncated) URL. Open admin.html, check each album's photo list for any URL that doesn't end in `-no`, fix it via Edit Photos, and save.

**A photo is sideways / wrong rotation**
Google Photos sometimes loses EXIF rotation data when serving via URL. Go into Edit Photos for that album, find the offending URL and delete it, then save. You can't force rotation via the URL.

**Save & Publish shows an error**
Your GitHub token may have expired. Go to `github.com/settings/tokens`, regenerate it with the `repo` scope, and re-enter it on the admin page.

**Duplicate album in the dropdown**
Open admin.html, find the duplicate in the Current Albums list, click ✕ to remove it, then Save & Publish.

**Chrome extension not connecting**
- Make sure Claude.ai is open **in Chrome** (not DuckDuckGo or another browser)
- Click the extension puzzle piece → Claude → Connect in the popup
- Check `chrome://extensions` that the Claude extension is enabled
- Click Details on the extension and make sure "Allow access to file URLs" is on
- Try refreshing the Claude.ai tab in Chrome and reconnecting
- The extension disconnects periodically — just reconnect and continue

---

## GitHub Token Setup (one time per device)

1. Go to: **github.com/settings/tokens/new**
2. Note: `Jersey Mark Admin`
3. Expiration: No expiration (so this doesn't happen again)
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
| Kings Canyon 2025 | Added May 2026 |
| Redwoods · Gold Bluffs Beach Campground 2024 | Added May 2026 |
| Chasing Dolphins 2024 | Added May 2026 |
| Glacier National Park · Montana 2021 | Added May 2026 |
| Tonto National Monument · Arizona 2023 | Added May 2026 |
| Lassen National Park · CA 2022 | Added May 2026 |
| Yosemite National Park · CA 2025 | Added May 2026 |
| Wildlife & Snorkeling · Isle of Coronado · Baja 2024 | Added May 2026 |

---

*Last updated: May 2026*
