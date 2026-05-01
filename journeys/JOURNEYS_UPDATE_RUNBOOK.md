# Journeys Map Update Runbook

**Audience:** future-Mark, doing this once every month or two.
**Last updated:** May 2026.
**Estimated time per run:** 30-90 minutes of mostly waiting (script time), 5-10 minutes of your active attention.

---

## The 30-second version

1. Get a Takeout zip (or zips) from Google → drop into `E:\GooglePhotosTakeouts\`
2. Open PowerShell, `cd` to the repo, run `.\run_pipeline.ps1`
3. Look at the printed summaries
4. Open GitHub Desktop, review changes, commit, push — Vercel deploys automatically

That's it. Everything below is the detail you might forget between runs.

---

## What this process does

You're a nomad with photos on your phone. Periodically:

- Google Photos has new geotagged photos from where you've been
- You want those to show up on `journeys.html` (the interactive travel map at https://www.journeyswithjerseymark.com/journeys.html) as new "stays"
- You want each stay to have a place name, a date range, and a couple of representative thumbnails

The pipeline does this in four stages:

1. **Ingest** — pull new photos from Takeout zip(s) into your photo archive on the E: drive, skipping anything you already have.
2. **Thumbnails** — pick 3 representative photos per stay and shrink them to 200px JPEGs that live in the repo.
3. **Geocode** — call OpenStreetMap to turn each stay's coordinates into a place name like "Boulder, CO".
4. **Build the page** — read everything above and write a fresh `journeys.html`.

Then you commit & push from GitHub Desktop. Vercel auto-deploys.

---

## Folders involved (memorize this map)

```
E:\GooglePhotosTakeouts\                  ← drop new Takeout .zip files HERE
└── takeout-*.zip

E:\MyPhotoArchive\                        ← master photo archive (NEVER in git)
├── Albums\                               ← album-organized photos
├── Unalbumed\                            ← where new ingest puts photos, by YYYY-MM
│   ├── 2024-09\
│   ├── 2026-04\
│   └── ...                               ← new month folders appear here over time
├── _misc\                                ← untitled / copy_of / print_orders / people_tags
├── _index\
│   ├── hashes.json                       ← SHA-1 hash of every photo (for dedup)
│   ├── all_photos.json                   ← list of every photo with hash, path, taken, lat, lng
│   ├── zip_progress.json                 ← extraction checkpoints
│   └── log.txt                           ← run log
├── _staging\                             ← temp extraction merge tree
└── _quarantine\                          ← duplicates / hash failures / orphan sidecars
    ├── hash_failed\
    └── orphan_sidecars\

C:\Users\mfuge\OneDrive\Desktop\ClaudeDesktop\PhotoMap\   ← THE PIPELINE SCRIPTS
├── extract_to_ssd_v2.py                  ← step 1: ingest
├── build_journey_thumbs.py               ← step 2: thumbnails
├── build_journey_places.py               ← step 3: geocoding
├── reconcile_thumbs.py                   ← post-deletion cleanup helper
└── _obsolete\STATE_OF_PLAY.md            ← ground-truth doc

C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark\   ← THE REPO
├── run_pipeline.ps1                      ← one-command launcher (steps 1-4)
├── build_journeys_page.py                ← step 4: render the page
├── journeys\                             ← what gets pushed to the live site
│   ├── thumbs\                           ← 200px JPEG thumbnails (committed)
│   ├── stay_thumbs.json                  ← manifest: thumbs + place names (committed)
│   ├── .thumbs_ignore.json               ← list of deleted-on-purpose thumbs (committed)
│   ├── place_cache.json                  ← geocoder cache (gitignored)
│   └── JOURNEYS_UPDATE_RUNBOOK.md        ← this file
├── journeys.html                         ← the actual map page (committed)
├── index.html, wallpapers.html, ...      ← rest of the site
└── .gitignore
```

---

## The four scripts (run in this order)

| Script | What it does | First-run time | Re-run time |
|---|---|---|---|
| `extract_to_ssd_v2.py` | Extract zip(s), hash-dedup (SHA-1), file new photos into `Unalbumed/` and `Albums/` and `_misc/` | 5-30 min depending on zip size | same |
| `build_journey_thumbs.py` | Detect stays, pick 3 photos per stay, make 200px JPEGs, update manifest | 5-15 min | 1-2 min (only new stays) |
| `build_journey_places.py` | Reverse-geocode stay coordinates to place names | 5-10 min | <1 min (cache hits) |
| `build_journeys_page.py` | Render the final `journeys.html` | <30 sec | <30 sec |

All four are idempotent — running them twice in a row produces the same result the second time as the first. The `run_pipeline.ps1` wrapper runs all four in order with summaries between.

---

## The one-command procedure (recommended)

### Step 1 — Get a Takeout from Google

1. Go to **https://takeout.google.com**
2. Click **Deselect all**, then check ONLY **Google Photos**
3. Click "All photo albums included" — you can be selective here, or just leave it alone (dedup will skip what you already have).
4. Click **Next step**
5. Choose **Send download link via email**, file type **.zip**, file size **50 GB** (largest available — minimizes the number of zips)
6. Click **Create export**
7. Wait — anywhere from minutes to a day to email you the link
8. Download the zip(s) into:

   ```
   E:\GooglePhotosTakeouts\
   ```

   Multiple zips? Drop them all in that folder. The ingest script handles them in one pass.

### Step 2 — Run the pipeline

Open PowerShell, `cd` to the repo, run the script:

```powershell
cd C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark
.\run_pipeline.ps1
```

That's it for the script side. It will:

1. Run `extract_to_ssd_v2.py` (ingest)
2. Run `build_journey_thumbs.py` (thumbnails)
3. Run `build_journey_places.py` (geocoding)
4. Run `build_journeys_page.py` (render the page)

If any step fails, the pipeline stops and tells you which step. Earlier steps are idempotent, so you can fix the issue and just re-run.

### Step 3 — Spot-check the page (optional but recommended)

Don't double-click `journeys.html` — `file://` URLs block the JS that loads thumbnails and place names. Run a tiny local server instead:

```powershell
cd C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark
python -m http.server 8000
```

Open `http://localhost:8000/journeys.html`. Click a few stay circles — popups should show place names, dates, and thumbnails. `Ctrl+C` in PowerShell to stop the server.

### Step 4 — Commit and push (in GitHub Desktop)

1. Open GitHub Desktop. It will auto-detect the changes:
   - `modified: journeys.html`
   - `modified: journeys/stay_thumbs.json`
   - `new file: journeys/thumbs/stay-XXXX-a.jpg` (etc., for new stays)
2. Review the changes panel, write a commit message like "Update journeys map (May 2026 ingest)"
3. Click **Commit** then **Push origin**
4. Vercel picks up the push and deploys within a minute or two
5. Visit https://www.journeyswithjerseymark.com/journeys.html

**What should NOT show up in GitHub Desktop:**
- Anything in `E:\` (different drive entirely — not in repo)
- Anything in `_takeout_inbox/` (this folder is leftover from old workflow; it's gitignored anyway)
- `journeys/place_cache.json` (gitignored)

---

## Removing sensitive thumbs (when needed)

If a generated thumbnail turns out to be something you don't want public — a mail document, a screenshot of something private, etc. — the workflow is:

1. **Delete the thumbnail file** from `journeys\thumbs\` in File Explorer
2. Open PowerShell:

   ```powershell
   cd C:\Users\mfuge\OneDrive\Desktop\ClaudeDesktop\PhotoMap
   python reconcile_thumbs.py
   ```

3. The reconcile script removes the entry from `stay_thumbs.json` AND adds the filename to `journeys\.thumbs_ignore.json`
4. The ignore list is consulted on every future thumbs build, so the deleted thumb will never come back even if you re-ingest the source photo
5. Open GitHub Desktop, commit and push the changes

**Important:** `journeys\.thumbs_ignore.json` IS tracked in git. If your repo ever gets cloned to a new machine, that file comes along and protects the new copy too. Never `.gitignore` it.

---

## Cleanup (every few months)

The `_staging\` folder under `E:\MyPhotoArchive\` is meant to be cleaned up automatically by Phase 3 of the ingest, but it can grow large if a run was interrupted. Once you're confident a recent ingest worked end-to-end:

```powershell
Remove-Item -Recurse "E:\MyPhotoArchive\_staging"
```

Quarantine folders accumulate over time. Once you've confirmed an ingest went well, you can delete old quarantine subfolders:

```powershell
# Look at what's there
dir E:\MyPhotoArchive\_quarantine

# Delete a specific reason bucket (only when you're sure)
Remove-Item -Recurse "E:\MyPhotoArchive\_quarantine\hash_failed"
Remove-Item -Recurse "E:\MyPhotoArchive\_quarantine\orphan_sidecars"
```

Old Takeout zips can be deleted from the inbox once their ingest is committed:

```powershell
Remove-Item E:\GooglePhotosTakeouts\*.zip
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'PIL'"
Run: `pip install pillow`

### "ERROR: photo archive not found: E:\MyPhotoArchive"
The E: drive isn't mounted. Check drive letter assignment (Disk Management).

### Geocoder returns lots of failures
Probably an internet hiccup or Nominatim is down. Wait a few minutes and re-run — cached entries get reused, only failures are retried. The script saves cache every 10 lookups so progress isn't lost on interruption.

### Map shows old data after push
Vercel takes 30-60 seconds to deploy. Hard-refresh (Ctrl+F5). If it still looks old after 5 minutes, check Vercel's deployment dashboard for errors.

### Thumbnails missing for new stays
Check the `build_journey_thumbs.py` output for "Source missing" count. That means the photo file isn't where `all_photos.json` says it should be — usually means the archive was modified outside the pipeline. Worst case, regenerate by deleting `stay_thumbs.json` and re-running.

### "I forgot which scripts to run"
Just run `.\run_pipeline.ps1` from the repo. It runs them all in order.

If you want to run them manually:

```powershell
cd C:\Users\mfuge\OneDrive\Desktop\ClaudeDesktop\PhotoMap
python extract_to_ssd_v2.py        # only when you have new zip(s) in E:\GooglePhotosTakeouts
python build_journey_thumbs.py     # always
python build_journey_places.py     # always

cd C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark
python build_journeys_page.py      # always
```

---

## When something goes really wrong

The whole archive is on E:, separate from the repo. Worst case:

1. **Hash index corrupted?** Delete `E:\MyPhotoArchive\_index\hashes.json` and the next ingest rebuilds it from scratch (slow, but recoverable). Note: HASH ALGORITHM IS SHA-1, NOT SHA-256.
2. **Manifest corrupted?** Delete `journeys\stay_thumbs.json`, re-run thumbs + places + page builder. The thumbnail JPEGs themselves are still on disk so most of it is fast.
3. **Wrong things committed?** Use GitHub Desktop's history view to revert the offending commit.
4. **Repo and archive out of sync?** Re-running the build pipeline always re-derives everything from the archive on E:. The repo's journey files are derived data — they can be regenerated.

The archive on E: is the source of truth. Everything else can be rebuilt.

---

## Quick reference

```
INBOX:    E:\GooglePhotosTakeouts\                 ← drop zips here
ARCHIVE:  E:\MyPhotoArchive\                       ← master photos (NOT in git)
SCRIPTS:  C:\...\ClaudeDesktop\PhotoMap\           ← extract, thumbs, places, reconcile
REPO:     C:\...\Github\JourneysWithJerseyMark\    ← page builder, run_pipeline.ps1, journeys/

CMD:      .\run_pipeline.ps1                       ← from the repo, runs all 4 steps

PUSH:     GitHub Desktop                           ← review, commit, push
```
