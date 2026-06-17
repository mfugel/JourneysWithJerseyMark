# Add a New Memory — Workflow Guide
### Journeys with Jersey Mark · journeyswithjerseymark.com

---

## Overview

This is the procedure for adding a new photo album to the "Memories from the Road" slideshow on the website.

The admin page handles everything automatically — no Chrome extension, no Claude Desktop, no copy/pasting URLs.

---

## Step 1 — Open the Admin Page

1. Go to: **https://journeyswithjerseymark.com/admin.html**
2. Enter your GitHub Personal Access Token → click **"✦ Enter the Chart Room"**
   *(Check "Remember on this device" so you only need to do this once per device)*

---

## Step 2 — Fetch the Album

1. Scroll down to the **green "Add a New Album" section**
2. Paste your Google Photos share link into the **Google Photos Share Link** field
3. Click **🔍 Fetch Photos**
4. The admin page calls the site's own API to fetch the album — within a few seconds:
   - **Album Title** is filled in automatically (edit it if you want)
   - **Photo URLs** are populated automatically (25–30 photos)

> **Note:** Always verify photo URLs end in `=w1200-h900-no`. Truncated URLs cause silent JSON parse failures.
> **Note:** Google Photos URLs expire after a few weeks — always fetch fresh URLs rather than reusing old ones.

---

## Step 3 — Publish

1. Click **+ Add Album** (green button)
2. Verify the album appears in the **"Current Albums on Site"** list above
3. Click **💾 Save & Publish to Site**
4. Wait about 30 seconds — the site updates automatically via Vercel

---

## Step 4 — Verify on the Live Site

1. Go to **journeyswithjerseymark.com**
2. Scroll to the **"Memories from the Road"** section
3. Find your new album in the cover photo grid — it will show a **New!** badge
4. Click it and confirm photos load and cycle correctly
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

**Fetch Photos returns an error or 0 photos**
The admin page's fetch API was unable to read the album — the album may be set to private, or the share link may have expired. Make sure the album is shared publicly in Google Photos and try again with a fresh share link.

**Photos not loading / blank slideshow**
The photo URLs have likely expired (Google Photos URLs expire after a few weeks). Open admin.html, click "✎ Edit Photos" for the affected album, delete all URLs, click Fetch Photos with the original share link to get fresh ones, then Save & Publish.

**Wrong photos showing (e.g. previous album's photos)**
The album was saved with stale URLs. Use Edit Photos in admin.html, delete all URLs, and use Fetch Photos to get fresh ones.

**Only 2 albums showing in the dropdown**
The `albums.json` file likely has a broken (truncated) URL. Open admin.html, check each album's photo list for any URL that doesn't end in `-no`, fix it via Edit Photos, and save.

**A photo is sideways / wrong rotation**
Google Photos sometimes loses EXIF rotation data when serving via URL. Go into Edit Photos for that album, find the offending URL and delete it, then save. You can't force rotation via the URL.

**Save & Publish shows an error**
Your GitHub token may have expired. Go to `github.com/settings/tokens`, regenerate it with the `repo` scope, and re-enter it on the admin page.

**Duplicate album in the dropdown**
Open admin.html, find the duplicate in the Current Albums list, click ✕ to remove it, then Save & Publish.

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
| Joshua Tree National Park 2025 | Added May 2026 |
| Kings Canyon 2025 | Added May 2026 |
| Redwoods · Gold Bluffs Beach Campground 2024 | Added May 2026 |
| Chasing Dolphins 2024 | Added May 2026 |
| Glacier National Park · Montana 2021 | Added May 2026 |
| Tonto National Monument · Arizona 2023 | Added May 2026 |
| Lassen National Park · CA 2022 | Added May 2026 |
| Yosemite National Park · CA 2025 | Added May 2026 |
| Wildlife & Snorkeling · Isle of Coronado · Baja 2024 | Added May 2026 |
| Antelope Lake · CA · 2025 | Added June 2026 — 30 photos |

---

*Last updated: June 2026*
