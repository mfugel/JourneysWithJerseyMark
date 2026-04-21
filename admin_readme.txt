JOURNEYS WITH JERSEY MARK
Admin Guide: Adding Photos to the Memories Slideshow
=====================================================

OVERVIEW
--------
The Memories slideshow on your site is driven by albums.json in your GitHub
repo. To add a new album, you need a list of photo URLs — one per line — to
paste into the admin page. Here is the full process from start to finish.


STEP 1 — CREATE A SHARED GOOGLE PHOTOS ALBUM
---------------------------------------------
1. Open Google Photos on your phone or at photos.google.com
2. Tap the + button and create a new album
3. Give it a descriptive name that includes the location and date, e.g.:
     "Yellowstone National Park · June 2025"
   (This becomes the dropdown label on your site)
4. Add your best photos — aim for 20-25 photos max for best results
5. Tap Share and set it to "Anyone with the link"
6. Copy the share link (looks like: https://photos.app.goo.gl/XXXXXXX)

TIP: Keep albums focused and under 25 photos. Claude can only see photos
that appear in the initial page load — larger albums may get cut off.


STEP 2 — GET THE PHOTO URLs FROM CLAUDE
----------------------------------------
1. Open a new conversation with Claude at claude.ai
2. Type exactly:
     "add a new memory to my site https://photos.app.goo.gl/YOURLINK"
3. Claude will fetch the album, extract all photo URLs, skip any videos,
   and give you a ready-to-paste list of URLs

Claude will also provide a suggested album title you can use or edit.

NOTE: Claude saves a copy of the URL list to your Google Drive
(JourneysWithJerseyMark folder) as a .txt file for your records.


STEP 3 — ADD THE ALBUM VIA THE ADMIN PAGE
------------------------------------------
1. Go to: https://journeyswithjerseymark.com/admin.html
2. Enter your GitHub Personal Access Token and click "Enter the Chart Room"
   (Check "Remember on this device" so you only need to do this once per device)
3. In the "Add a New Album" section, fill in:
     - Album Title: use the title Claude suggested, or edit it
     - Google Photos Share Link: paste the photos.app.goo.gl URL
     - Photo URLs: paste the full list of URLs Claude provided
4. Click "+ Add Album"
5. Verify the album appears in the "Current Albums on Site" list
6. Click "Save & Publish to Site"
7. Wait about 30 seconds — your site updates automatically


STEP 4 — VERIFY ON THE LIVE SITE
----------------------------------
1. Go to journeyswithjerseymark.com
2. Scroll to the "Memories from the Road" section
3. Open the dropdown — your new album should appear
4. Select it and confirm photos load and cycle correctly


MANAGING EXISTING ALBUMS
-------------------------
From the admin page you can also:

  REORDER  Use the up/down arrows (▲ ▼) next to each album to change
           the order they appear in the dropdown

  REMOVE   Click the ✕ button to delete an album entirely

  EDIT     Click "✎ Edit Photos" to update the photo URLs for an album
           (useful if Google Photos links expire or you want to swap photos)

Always click "Save & Publish to Site" after making any changes.


TROUBLESHOOTING
---------------
ONLY 2 ALBUMS SHOWING IN DROPDOWN
  The albums.json file likely has a broken URL — often a URL that got
  truncated when pasting. Open admin.html, check the photo list for each
  album, and look for any URL that appears cut off (doesn't end in -no).
  Fix it by clicking Edit Photos on the affected album, removing the
  truncated URL, and saving.

PHOTOS NOT LOADING (shows alt text instead)
  The photo URL may have expired. Google Photos direct image links are
  stable but can occasionally stop working. Ask Claude to re-fetch the
  album and get fresh URLs, then use Edit Photos to update.

SAVE & PUBLISH SHOWS AN ERROR
  Your GitHub token may have expired. Go to github.com/settings/tokens,
  regenerate it, and re-enter it on the admin page. Make sure the token
  has the "repo" scope.

DUPLICATE ALBUM IN DROPDOWN
  Open admin.html, find the duplicate in the Current Albums list,
  click ✕ to remove it, then Save & Publish.

SPECIAL CHARACTERS SHOWING GARBLED (e.g. · shows as Ã‚Â·)
  This was a known bug that has been fixed. If you see this on old albums,
  open admin.html and re-save — the fixed admin page will correct the
  encoding when it writes the file.


GITHUB TOKEN SETUP (one time per device)
-----------------------------------------
If you need to create a new GitHub Personal Access Token:
1. Go to: github.com/settings/tokens/new
2. Note: "Jersey Mark Admin"
3. Expiration: No expiration (or set a long one)
4. Scope: Check only "repo"
5. Click "Generate token" and copy it immediately (only shown once)
6. Paste it into the admin page and check "Remember on this device"


YOUR KEY LINKS
--------------
  Site:        https://journeyswithjerseymark.com
  Admin page:  https://journeyswithjerseymark.com/admin.html
  GitHub repo: https://github.com/mfugel/JourneysWithJerseyMark
  Token page:  https://github.com/settings/tokens


---
Last updated: April 2026