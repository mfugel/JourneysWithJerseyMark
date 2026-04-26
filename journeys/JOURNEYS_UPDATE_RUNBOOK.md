# Journeys Map Update Runbook

**Audience:** future-Mark, doing this once every month or two.
**Last updated:** April 2026.
**Estimated time per run:** 30-90 minutes of mostly waiting (script time), 5-10 minutes of your active attention.

---

## The 30-second version

1. Get a Takeout zip from Google → drop it in `_takeout_inbox/`
2. Run four Python scripts in order
3. Look at the printed summaries
4. `git add ... && git commit && git push`

That's it. Everything below is the detail you might forget between runs.

---

## What this process does

You're a nomad with photos on your phone. Periodically:

- Google Photos has new geotagged photos from where you've been
- You want those to show up on `journeys.html` (the interactive travel map at https://www.journeyswithjerseymark.com/journeys.html) as new "stays"
- You want each stay to have a place name, a date range, and a couple of representative thumbnails

The pipeline does this in four stages:

1. **Ingest** — pull new photos from a Takeout zip into your photo archive on the E: drive, skipping anything you already have.
2. **Thumbnails** — pick 3 representative photos per stay and shrink them to 200px JPEGs that live in the repo.
3. **Geocode** — call OpenStreetMap to turn each stay's coordinates into a place name like "Boulder, CO".
4. **Build the page** — read everything above and write a fresh `journeys.html`.

Then you commit & push. Vercel auto-deploys.

---

## Folders involved (memorize this map)

```
E:\MyPhotoArchive\                        ← your master photo archive (NEVER in git)
├── Albums\                               ← (existing) album-organized photos
├── Unalbumed\                            ← where new ingest puts photos, by YYYY-MM
│   ├── 2024-09\
│   ├── 2025-03\
│   └── ...                               ← new month folders appear here over time
├── _index\
│   ├── hashes.json                       ← SHA-256 hash of every photo (for dedup)
│   └── ingest_<runid>.txt                ← per-run report
├── _staging\                             ← temp extraction (auto-cleaned)
└── _quarantine\<runid>\                  ← duplicates from each ingest, for review

C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark\   ← THE REPO
├── _takeout_inbox\                       ← drop new Takeout .zip files HERE (gitignored)
│   └── README.txt
├── journeys\                             ← what gets pushed to the live site
│   ├── thumbs\                           ← 200px JPEG thumbnails (committed)
│   │   ├── stay-0001-a.jpg
│   │   └── ...
│   ├── stay_thumbs.json                  ← manifest: stay → thumbs + place names (committed)
│   ├── .thumbs_ignore.json               ← list of deleted-on-purpose thumbs (committed)
│   └── place_cache.json                  ← geocoder cache (gitignored, local only)
├── journeys.html                         ← the actual map page (committed)
├── index.html, wallpapers.html, ...      ← rest of the site
└── .gitignore
```

The Python scripts are not currently in the repo. Keep them somewhere predictable — a folder like `C:\Users\mfuge\Scripts\journeys\` works well. Path doesn't matter as long as you can `cd` to it.

---

## The four scripts

| Script | What it does | First-run time | Re-run time |
|---|---|---|---|
| `ingest_takeout.py` | Extract zip, hash-dedup, file new photos into Unalbumed/ | 5-30 min depending on zip size | same |
| `build_journey_thumbs.py` | Make 200px thumbnails for each stay, update manifest | 5-15 min | 1-2 min (only new stays) |
| `build_journey_places.py` | Reverse-geocode stay coordinates to place names | 5-10 min | <1 min (cache hits) |
| `build_journeys_page.py` | Render the final `journeys.html` | <30 sec | <30 sec |

All four are idempotent — running them twice in a row produces the same result the second time as the first.

---

## The actual procedure (every 1-2 months)

### Step 1 — Get a Takeout from Google

1. Go to **https://takeout.google.com**
2. Click **Deselect all**, then check ONLY **Google Photos**
3. Click "All photo albums included" — this is where you can be selective. The simplest move is to leave it alone and grab everything; the dedup will skip things you already have. **OR** if you want to keep the zip small, deselect everything and select only the recent year-month folders ("Photos from 2026", etc.) you haven't ingested before.
4. Click **Next step**
5. Choose **Send download link via email**, file type **.zip**, file size **50 GB** (largest available — minimizes the number of zips you have to handle)
6. Click **Create export**
7. Wait — Google takes anywhere from minutes to a day to email you the link
8. Download the zip(s) into:

   ```
   C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark\_takeout_inbox\
   ```

   Multiple zips? Drop them all in that folder. The ingest script processes one at a time — see "Multiple zips" note below.

### Step 2 — Run the ingest

Open PowerShell and `cd` to wherever your scripts live:

```powershell
cd C:\Users\mfuge\Scripts\journeys     # adjust to your actual path
python ingest_takeout.py
```

If you didn't pass a zip path, it grabs the **newest** zip in `_takeout_inbox/` automatically.

**What you'll see:**

```
Auto-detected newest zip: ...\takeout-20260415T120000Z-001.zip

=== Extracting ... ===
  members: 12,847   uncompressed: 23.4 GB
  extracted in 142 sec

=== Loading hash index ===
  existing hashes: 73,422

=== Hashing & deduping ===
  media files found: 11,203
  ...500/11,203  (new 218, dup 282)
  ...
  ...11,000/11,203  (new 487, dup 10,513)

=== Saving hash index ===

======================================================================
INGEST SUMMARY
======================================================================
  Source zip          : takeout-20260415T120000Z-001.zip
  Media examined      : 11,203
  New files imported  : 487
  Duplicates -> quar. : 10,716
  Sidecar orphans     : 0
  Hash failures       : 0
  Total archive hashes: 73,909
  ...
```

**What to look at:**

- **"New files imported"** — should be roughly the number of photos you took since your last ingest. If it's zero or one, something's wrong (or you literally took no new photos).
- **"Duplicates -> quar."** — expected to be high if your Takeout overlaps with previous ones. These are quarantined, not deleted. Files at `E:\MyPhotoArchive\_quarantine\<runid>\`.
- **"Hash failures"** — should be 0. Anything else means a corrupt file in the zip.

### Step 3 — Multiple zips? (only if applicable)

If Google split your Takeout into several zips (`-001.zip`, `-002.zip`, etc.), run the ingest once per zip, passing the path explicitly:

```powershell
python ingest_takeout.py "C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark\_takeout_inbox\takeout-20260415T120000Z-002.zip"
python ingest_takeout.py "...\takeout-20260415T120000Z-003.zip"
```

Each run produces its own `_quarantine\<runid>\` folder and `_index\ingest_<runid>.txt` report. Order doesn't matter; dedup handles overlap.

### Step 4 — Build thumbnails

```powershell
python build_journey_thumbs.py
```

**What it does:**
- Re-detects all stays from your full archive (~5-10 sec)
- For new stays only, picks 3 representative photos and creates 200px JPEGs in `journeys\thumbs\`
- Skips any thumbnail filename listed in `journeys\.thumbs_ignore.json` (your deletion list — see "Removing sensitive thumbs" below)
- Re-writes `journeys\stay_thumbs.json` (preserving existing place names)

**What you'll see:**

```
Honoring ignore list: 14 filenames will not be regenerated
Scanning E:\MyPhotoArchive ...
  ...152,647 sidecars scanned
After dedup: 14,234 unique points.
Qualified stays: 305
  stay 50 / 305 (new 12, skip 138, miss 0, ignored 4, fail 0)
  ...

Thumbnails created   : 41
Already existed      : 643
Skipped (ignore list): 14
Stays with thumbs    : 297 / 305
Thumbs folder size   : 3.8 MB
```

**What to look at:**

- **"Thumbnails created"** — small positive number. The big positive number from the original 73K-file run won't repeat.
- **"Skipped (ignore list)"** — same number as last time, hopefully. If it grew, check `journeys\.thumbs_ignore.json` to make sure you actually meant to add to it.
- **"Stays with thumbs"** — should be close to "Qualified stays" (within a few of each other).

### Step 5 — Geocode places

```powershell
python build_journey_places.py
```

**What it does:**
- Re-detects stays (same logic as the thumbs builder)
- For any stay whose centroid is NOT in the geocoder cache, calls OpenStreetMap's Nominatim API once (rate-limited to 1.1 sec per call)
- Saves results to `journeys\place_cache.json` and merges into `journeys\stay_thumbs.json`

**Time:** roughly 1.1 sec × number of NEW stays. So 14 new stays ≈ 16 seconds. The first time you ran it on the full 291 stays took ~5 minutes; subsequent runs are mostly cache hits.

**What you'll see:**

```
Cache entries: 287
Stays: 305
  [   3 new] #298: Sedona, AZ
  [   6 new] #301: Joshua Tree, CA
  [  10 new] #303: Twentynine Palms, CA
  ...
Cache hits          : 287
New lookups         : 18
Failures            : 0
```

**What to look at:**

- **"Failures"** — should be 0 or very close. If the internet was flaky, re-run; cached entries get reused, only failures are retried.
- The place names that print as new lookups happen — sanity check a couple. If you see "Tokyo" when you've been in California, something is off (but unlikely — geocoders are reliable).

### Step 6 — Build the page

```powershell
python build_journeys_page.py
```

Fast — runs in seconds. Re-writes `journeys.html` with the latest data.

**What you'll see:**

```
Scanning E:\MyPhotoArchive ...
After dedup: 14,234 unique points.
Stays: 305
Hex cells: 1,243
Fetching US state polygons ...
  matching 13,801 points to states ...
Wrote C:\...\JourneysWithJerseyMark\journeys.html  (1,832 KB)

Done. To deploy:
  cd C:\...\JourneysWithJerseyMark
  git add journeys.html index.html wallpapers.html
  git commit -m "Add interactive journeys map"
  git push
```

### Step 7 — Spot check (optional but recommended)

Before pushing, open `journeys.html` to do a sanity check.

**However:** opening it directly with double-click won't show thumbnails or place names because browsers block `fetch()` from `file://` URLs. To preview properly, run a tiny local server:

```powershell
cd C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark
python -m http.server 8000
```

Then open `http://localhost:8000/journeys.html` in your browser. You should see new stay circles in places you visited recently. Click one — popup shows place name, dates, photo count, thumbnails. Press Ctrl+C in PowerShell to stop the local server when done.

If anything looks wrong, fix it before pushing. Common issues:

- **Stays in weird places?** Check the new ingest's photos — sometimes phone GPS gets confused indoors and writes coordinates from blocks away. Usually self-corrects with multiple photos averaged.
- **Place name is in the wrong country?** Re-run `build_journey_places.py` — sometimes Nominatim hiccups. If it persists for one specific stay, you can manually edit `journeys\stay_thumbs.json` and change just that entry.

### Step 8 — Commit and push

```powershell
cd C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark
git add journeys.html journeys/
git status                                  # review what's about to ship
git commit -m "Update journeys map (April 2026 ingest)"
git push
```

Vercel will pick this up and deploy automatically — usually within a minute. Visit https://www.journeyswithjerseymark.com/journeys.html to see it live.

**What `git status` should show before commit:**

- `modified: journeys.html` ← new map page
- `modified: journeys/stay_thumbs.json` ← updated manifest
- `new file: journeys/thumbs/stay-XXXX-a.jpg` etc. ← new thumbnails
- `modified: journeys/.thumbs_ignore.json` ← only if you deliberately deleted thumbs this round

**What `git status` should NOT show:**

- ❌ Anything in `_takeout_inbox/` (gitignored)
- ❌ The Takeout zip itself (gitignored)
- ❌ Anything in `E:\MyPhotoArchive\` (different drive entirely)
- ❌ `journeys/place_cache.json` (gitignored — local only)

If those things show up, your `.gitignore` got broken and we need to fix it before pushing.

---

## Removing sensitive thumbs (when needed)

If a generated thumbnail turns out to be something you don't want public — a mail document, a screenshot of something private, etc. — the workflow is:

1. **Delete the thumbnail file** from `journeys\thumbs\` in File Explorer
2. **Run** `python reconcile_thumbs.py`
3. The reconcile script removes the entry from `stay_thumbs.json` AND adds the filename to `journeys\.thumbs_ignore.json`
4. The ignore list is consulted on every future thumbs build, so the deleted thumb will never come back even if you re-ingest the source photo
5. Commit and push

**Important:** `journeys\.thumbs_ignore.json` IS tracked in git. If your repo ever gets cloned to a new machine, that file comes along and protects the new copy too. Never `.gitignore` it.

---

## Cleanup (every few months)

Quarantine folders accumulate. Each ingest creates `E:\MyPhotoArchive\_quarantine\<runid>\` with the duplicates from that run. Once you've confirmed an ingest went well (a few weeks later), you can delete old quarantine folders:

```powershell
# Look at what's there
dir E:\MyPhotoArchive\_quarantine

# Delete one specific run
Remove-Item -Recurse "E:\MyPhotoArchive\_quarantine\20240315_142200"

# Or nuke them all (only after you're confident every recent ingest worked)
Remove-Item -Recurse E:\MyPhotoArchive\_quarantine\*
```

The `_takeout_inbox/` folder also fills up with old zips. Once an ingest is committed and pushed, the zip is no longer needed:

```powershell
Remove-Item C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark\_takeout_inbox\*.zip
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'PIL'"
The thumbnails script needs Pillow. Run: `pip install pillow`

### "ERROR: photo archive not found: E:\MyPhotoArchive"
The E: drive isn't mounted. Check drive letter assignment.

### Geocoder returns lots of failures
Probably an internet issue or Nominatim is down. Wait a few minutes and re-run — cache hits make the retry fast.

### "git push" rejected
Probably someone (you, on another machine) committed something via the Vercel/GitHub web UI. Run `git pull --rebase` then `git push` again.

### Map shows old data after push
Vercel takes 30-60 seconds to deploy. Hard-refresh the browser (Ctrl+F5). If it still looks old after 5 minutes, check Vercel's deployment dashboard for errors.

### Thumbnails missing for new stays
You probably deleted the source photo from `E:\MyPhotoArchive\` (or it never made it in). Check the build_journey_thumbs.py output for "Missing source" count.

### "I forgot which scripts to run"
Quick reference, in order:

```powershell
python ingest_takeout.py          # only when you have a new zip
python build_journey_thumbs.py    # always
python build_journey_places.py    # always
python build_journeys_page.py     # always
```

If you don't have a new zip and just want to refresh the map (e.g., you tweaked the page builder), skip the first one.

---

## When something goes really wrong

The whole archive is on E:, separate from the repo. Worst case:

1. **Hash index corrupted?** Delete `E:\MyPhotoArchive\_index\hashes.json` and the next ingest will re-build it from scratch (slow, but recoverable).
2. **Manifest corrupted?** Delete `journeys\stay_thumbs.json`, re-run thumbs + places + page builder. The thumbnail JPEGs themselves are still on disk so it'll be fast.
3. **Wrong things committed?** `git revert <commit-hash>` then push. Or harder: `git reset --hard <last-good-commit>` and force-push (only if you're sure no one else has pulled).
4. **Repo and archive out of sync?** Re-running the build pipeline always re-derives everything from the archive on E:. The repo's journey files are derived data — they can be regenerated.

The archive on E: is the source of truth. Everything else can be rebuilt.
