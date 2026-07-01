"""
build_journeys_page.py
======================
Generates `journeys.html` for the Journeys With Jersey Mark website.

Output goes directly into the GitHub repo folder so a `git commit` deploys it.
The page matches the site's parchment / cartographer aesthetic: same fonts,
colors, nav bar, vignette, ornaments. The map itself sits inside a
"legend box" with seven toggleable layers and a year-range slider.

Layers:
  1. Heatmap            (default ON)
  2. Hex grid
  3. Clustered markers
  4. Raw dots
  5. Stays              (default ON; one circle per stay, colored by year)
  6. Chronological path (default ON; faint dashed line connecting stays)
  7. US state choropleth

Output:
  C:\\...\\Github\\JourneysWithJerseyMark\\journeys.html
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, date
from pathlib import Path

# ------------------------------------------------------------------ config
ARCHIVE_ROOT = Path(r"E:\MyPhotoArchive")
SITE_ROOT    = Path(r"C:\Users\mfuge\OneDrive\Desktop\Github\JourneysWithJerseyMark")
OUT_PATH     = SITE_ROOT / "journeys.html"
MANIFEST     = SITE_ROOT / "journeys" / "stay_thumbs.json"
MANUAL_STAYS = SITE_ROOT / "journeys" / "manual_stays.json"

# North America bounding box
NA_BBOX = {"min_lat": 7.0, "max_lat": 75.0,
           "min_lon": -170.0, "max_lon": -50.0}

COORD_ROUND = 4
TIME_BUCKET = 300

STAY_RADIUS_KM = 25
MIN_NIGHTS = 1
HEX_SIZE_DEG = 0.5

US_STATES_GEOJSON_URL = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)


def is_valid(lat, lon):
    if lat is None or lon is None: return False
    if lat == 0.0 and lon == 0.0:  return False
    if not (-90 <= lat <= 90):     return False
    if not (-180 <= lon <= 180):   return False
    return True

def in_na(lat, lon):
    return (NA_BBOX["min_lat"] <= lat <= NA_BBOX["max_lat"]
            and NA_BBOX["min_lon"] <= lon <= NA_BBOX["max_lon"])

def extract_gps(d):
    for key in ("geoData", "geoDataExif"):
        g = d.get(key) or {}
        lat, lon = g.get("latitude"), g.get("longitude")
        if is_valid(lat, lon):
            return lat, lon
    return None

def extract_ts(d):
    pt = d.get("photoTakenTime") or {}
    try:    return int(pt.get("timestamp"))
    except (TypeError, ValueError): return None

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def point_in_ring(lon, lat, ring):
    inside = False
    n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside

def point_in_feature(lon, lat, feat):
    geom = feat["geometry"]
    if geom["type"] == "Polygon":
        rings = geom["coordinates"]
        if not rings: return False
        if not point_in_ring(lon, lat, rings[0]): return False
        for hole in rings[1:]:
            if point_in_ring(lon, lat, hole): return False
        return True
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            if not poly: continue
            if point_in_ring(lon, lat, poly[0]):
                if not any(point_in_ring(lon, lat, h) for h in poly[1:]):
                    return True
        return False
    return False


# --------------------------------------------------------------------- main
def main():
    if not ARCHIVE_ROOT.exists():
        print(f"ERROR: photo archive not found: {ARCHIVE_ROOT}")
        sys.exit(1)
    if not SITE_ROOT.exists():
        print(f"ERROR: site folder not found: {SITE_ROOT}")
        sys.exit(1)

    print(f"Scanning {ARCHIVE_ROOT} ...")
    points = []
    json_count = 0
    for dirpath, _d, filenames in os.walk(ARCHIVE_ROOT):
        for fname in filenames:
            if not fname.lower().endswith(".json"):
                continue
            json_count += 1
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if "photoTakenTime" not in data and "geoData" not in data:
                continue
            gps = extract_gps(data)
            if gps is None: continue
            lat, lon = gps
            if not in_na(lat, lon): continue
            ts = extract_ts(data)
            points.append({
                "lat": lat, "lon": lon, "ts": ts,
                "title": data.get("title")
                         or os.path.basename(fpath).replace(".json", ""),
            })
            if json_count % 10000 == 0:
                print(f"  ...{json_count:,} sidecars scanned, "
                      f"{len(points):,} kept (NA + valid GPS)")
    print(f"\nScanned {json_count:,} sidecars. "
          f"Kept {len(points):,} points in North America.")

    seen = {}
    for p in points:
        key = (round(p["lat"], COORD_ROUND), round(p["lon"], COORD_ROUND),
               (p["ts"] // TIME_BUCKET) if p["ts"] else None)
        if key not in seen:
            seen[key] = p
    deduped = list(seen.values())
    print(f"After dedup: {len(deduped):,} unique points.")

    timed = [p for p in deduped if p["ts"]]
    timed.sort(key=lambda p: p["ts"])
    for p in timed:
        p["date"] = datetime.fromtimestamp(p["ts"], tz=timezone.utc).date()

    # ---- stay detection ----
    stays_raw = []
    cur = None
    for p in timed:
        if cur is None:
            cur = {"lat_sum": p["lat"], "lon_sum": p["lon"], "n": 1,
                   "points": [p], "start": p["date"], "end": p["date"]}
            continue
        c_lat = cur["lat_sum"] / cur["n"]; c_lon = cur["lon_sum"] / cur["n"]
        if haversine_km(p["lat"], p["lon"], c_lat, c_lon) <= STAY_RADIUS_KM:
            cur["lat_sum"] += p["lat"]; cur["lon_sum"] += p["lon"]; cur["n"] += 1
            cur["points"].append(p)
            if p["date"] < cur["start"]: cur["start"] = p["date"]
            if p["date"] > cur["end"]:   cur["end"]   = p["date"]
        else:
            stays_raw.append(cur)
            cur = {"lat_sum": p["lat"], "lon_sum": p["lon"], "n": 1,
                   "points": [p], "start": p["date"], "end": p["date"]}
    if cur is not None: stays_raw.append(cur)

    stays = []
    for s in stays_raw:
        nights = (s["end"] - s["start"]).days
        if nights >= MIN_NIGHTS:
            stays.append({
                "id": len(stays) + 1,
                "lat": s["lat_sum"] / s["n"],
                "lon": s["lon_sum"] / s["n"],
                "start": str(s["start"]), "end": str(s["end"]),
                "nights": nights, "photos": s["n"],
                "year": s["start"].year,
            })
    print(f"Stays: {len(stays):,}")

    # ---- merge in manually-added stays from journeys/manual_stays.json ----
    if MANUAL_STAYS.exists():
        try:
            mdata = json.loads(MANUAL_STAYS.read_text(encoding="utf-8-sig"))
            mlist = mdata.get("stays", []) or []
            added = 0
            for m in mlist:
                place = m.get("place")
                lat = m.get("lat")
                lon = m.get("lon")
                sd = m.get("start_date")
                ed = m.get("end_date") or sd
                if not (place and lat is not None and lon is not None and sd):
                    continue
                try:
                    sd_d = date.fromisoformat(sd)
                    ed_d = date.fromisoformat(ed)
                except Exception:
                    continue
                nights = max(1, (ed_d - sd_d).days)
                stays.append({
                    "id": len(stays) + 1,
                    "lat": float(lat), "lon": float(lon),
                    "start": str(sd_d), "end": str(ed_d),
                    "nights": nights, "photos": 0,
                    "year": sd_d.year,
                    "manual": True,
                    "place": place,
                    "note": m.get("note", ""),
                })
                added += 1
            if added:
                print(f"  Added {added} manual stay(s) from {MANUAL_STAYS.name}")
        except Exception as e:
            print(f"  WARN: could not load manual stays: {e}")

    # ---- merge place names + thumbs from journeys/stay_thumbs.json ----
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            mstays = manifest.get("stays", {}) or {}
            placed = thumbed = 0
            for st in stays:
                entry = mstays.get(str(st["id"])) or {}
                if isinstance(entry, list):
                    entry = {"thumbs": entry}
                place = entry.get("place")
                if place:
                    st["place"] = place
                    placed += 1
                thumbs = entry.get("thumbs") or []
                if thumbs:
                    st["thumbs"] = thumbs
                    thumbed += 1
            print(f"  Merged places={placed} thumbs_for={thumbed} from manifest")
        except Exception as e:
            print(f"  WARN: could not merge manifest: {e}")
    else:
        print(f"  (no manifest at {MANIFEST}; map will lack places/thumbs)")

    # ---- hex bins (precomputed for default; recomputed live in JS on filter) ----
    hex_counts = defaultdict(int)
    for p in deduped:
        gx = round(p["lon"] / HEX_SIZE_DEG)
        gy = round(p["lat"] / HEX_SIZE_DEG)
        cx = (gx if gy % 2 == 0 else gx + 0.5) * HEX_SIZE_DEG
        cy = gy * HEX_SIZE_DEG
        hex_counts[(round(cx, 4), round(cy, 4))] += 1
    print(f"Hex cells: {len(hex_counts):,}")

    # ---- US state choropleth ----
    print("Fetching US state polygons ...")
    state_geo = None
    try:
        import urllib.request
        with urllib.request.urlopen(US_STATES_GEOJSON_URL, timeout=20) as r:
            state_geo = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  could not fetch ({e}); choropleth will be empty.")

    if state_geo:
        candidates = [p for p in deduped if 24 <= p["lat"] <= 50
                      and -125 <= p["lon"] <= -66]
        print(f"  matching {len(candidates):,} points to states ...")
        state_counts = defaultdict(int)
        for i, p in enumerate(candidates):
            for feat in state_geo["features"]:
                if point_in_feature(p["lon"], p["lat"], feat):
                    name = (feat["properties"].get("name")
                            or feat["properties"].get("NAME") or "?")
                    state_counts[name] += 1
                    break
            if i and i % 2000 == 0:
                print(f"    {i:,} / {len(candidates):,}")
        for feat in state_geo["features"]:
            name = (feat["properties"].get("name")
                    or feat["properties"].get("NAME") or "?")
            feat["properties"]["photo_count"] = state_counts.get(name, 0)

    if timed:
        year_min = datetime.fromtimestamp(timed[0]["ts"], tz=timezone.utc).year
        year_max = datetime.fromtimestamp(timed[-1]["ts"], tz=timezone.utc).year
    else:
        year_min = year_max = datetime.now().year

    # Extend year range to include manual stays so they show in slider filter
    if stays:
        all_years = [s["year"] for s in stays if "year" in s]
        if all_years:
            year_min = min(year_min, min(all_years))
            year_max = max(year_max, max(all_years))

    payload = {
        "points": [{"lat": p["lat"], "lon": p["lon"],
                    "ts": p["ts"], "title": p["title"]}
                   for p in deduped],
        "stays": stays,
        "hex_size_deg": HEX_SIZE_DEG,
        "states": state_geo,
        "year_min": year_min, "year_max": year_max,
        "bbox": NA_BBOX,
        "stats": {
            "total_photos": len(deduped),
            "total_stays": len(stays),
            "year_min": year_min, "year_max": year_max,
        }
    }

    print("Writing journeys.html ...")
    html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload))
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUT_PATH}  ({size_kb:,.0f} KB)")
    print(f"\nDone. To deploy:")
    print(f"  cd {SITE_ROOT}")
    print(f"  git add journeys.html index.html wallpapers.html")
    print(f"  git commit -m \"Add interactive journeys map\"")
    print(f"  git push")


# ------------------------------------------------------------ HTML template
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>My Journeys | Interactive Travel Map · Journeys with Jersey Mark</title>
<meta name="description" content="An interactive map of every place I've traveled in North America — heatmap, stays, chronological path, and more. Filter by year and explore the journey.">
<meta name="author" content="Mark Fugel">
<link rel="canonical" href="https://www.journeyswithjerseymark.com/journeys.html">
<link rel="icon" href="/images/seal.jpg" type="image/jpeg">

<meta property="og:type" content="website">
<meta property="og:url" content="https://www.journeyswithjerseymark.com/journeys.html">
<meta property="og:title" content="My Journeys — Interactive Travel Map">
<meta property="og:description" content="An interactive map of every place I've traveled across North America. Heatmap, stays, chronological path, year filter — explore the road.">
<meta property="og:image" content="https://www.journeyswithjerseymark.com/images/seal.jpg">
<meta property="og:site_name" content="Journeys with Jersey Mark">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Cinzel:wght@400;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-padding-top:3rem;}
html,body{width:100%;min-height:100vh;}
body{background:#dfc99a;font-family:'Crimson Text',serif;color:#0f0800;position:relative;overflow-x:hidden;}
.parchment-bg{position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 28px,rgba(101,67,33,0.04) 29px),repeating-linear-gradient(90deg,transparent,transparent 28px,rgba(101,67,33,0.04) 29px);pointer-events:none;z-index:0;}
.vignette{position:fixed;inset:0;background:radial-gradient(ellipse at center,transparent 40%,rgba(80,40,10,0.35) 100%);pointer-events:none;z-index:0;}
.content{position:relative;z-index:1;width:100%;padding:2rem 3rem 3rem;}
.outer-border{border:3px solid #5a3510;border-radius:4px;padding:4px;position:relative;max-width:1100px;margin:0 auto;}
.inner-border{border:1.5px solid #7a4e20;border-radius:2px;padding:1.8rem 1.8rem 2.2rem;}
.corner-ornament{position:absolute;font-size:20px;color:#1a0f00;line-height:1;}
.corner-tl{top:10px;left:10px;}
.corner-tr{top:10px;right:10px;transform:scaleX(-1);}
.corner-bl{bottom:10px;left:10px;transform:scaleY(-1);}
.corner-br{bottom:10px;right:10px;transform:scale(-1);}
.cartouche{text-align:center;margin-bottom:1.5rem;}
.cartouche-border{border:2px solid #5a3510;border-radius:50% / 30%;padding:1.2rem 2.5rem 1.4rem;display:inline-block;min-width:80%;background:rgba(180,130,70,0.3);position:relative;}
.cartouche-border::before,.cartouche-border::after{content:'— ✦ —';display:block;font-size:13px;color:#1a0f00;letter-spacing:0.2em;}
.cartouche-border::before{margin-bottom:0.4rem;}
.cartouche-border::after{margin-top:0.4rem;}
.logo-seal{width:140px;height:140px;object-fit:contain;margin:0 auto 0.8rem;display:block;filter:sepia(0.55) saturate(0.85) contrast(1.05) brightness(0.97) hue-rotate(-5deg);mix-blend-mode:multiply;}
.map-title{font-family:'Cinzel',serif;font-size:1.9rem;font-weight:700;color:#0f0800;line-height:1.15;text-align:center;letter-spacing:0.04em;}
.map-subtitle{font-family:'IM Fell English',serif;font-style:italic;font-size:1.15rem;color:#1a0f00;text-align:center;margin-top:0.4rem;}
.map-motto{font-family:'IM Fell English',serif;font-style:italic;font-size:1rem;color:#1a0f00;text-align:center;margin-top:0.6rem;letter-spacing:0.03em;}
.divider-rule{display:flex;align-items:center;gap:8px;margin:1.3rem 0;color:#1a0f00;font-size:14px;letter-spacing:0.15em;}
.divider-rule::before,.divider-rule::after{content:'';flex:1;height:1px;background:#7a4e20;}
.legend-box{border:1.5px solid #7a4e20;border-radius:3px;padding:1.1rem;background:rgba(160,110,50,0.15);margin-bottom:1.2rem;position:relative;}
.legend-box-title{font-family:'Cinzel',serif;font-size:0.84rem;font-weight:700;letter-spacing:0.15em;color:#1a0f00;background:#dfc99a;padding:0 6px;position:absolute;top:-9px;left:16px;text-transform:uppercase;}
.footer-seal{text-align:center;margin-top:1.5rem;font-family:'IM Fell English',serif;font-style:italic;font-size:1.07rem;color:#1a0f00;letter-spacing:0.05em;}
.compass-rose{font-size:52px;color:#1a0f00;line-height:1;margin-bottom:0.3rem;}
.stats-row{display:flex;justify-content:space-around;text-align:center;margin:0.5rem 0;flex-wrap:wrap;}
.stat-item{flex:1;min-width:90px;border-right:1px solid rgba(90,53,16,0.3);padding:0.5rem 0.5rem;}
.stat-item:last-child{border-right:none;}
.stat-num{font-family:'Cinzel',serif;font-size:1.5rem;font-weight:700;color:#0f0800;}
.stat-lbl{font-family:'IM Fell English',serif;font-style:italic;font-size:0.90rem;color:#1a0f00;}

/* ── Nav ── */
.site-nav{position:sticky;top:0;z-index:500;background:rgba(90,53,16,0.96);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);border-bottom:1px solid rgba(220,192,137,0.25);}
.nav-inner{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:0;min-height:2.6rem;padding:0 1rem;}
.site-nav a{font-family:'Cinzel',serif;font-size:0.72rem;letter-spacing:0.13em;text-transform:uppercase;color:rgba(245,234,208,0.82);text-decoration:none;padding:0.6rem 0.65rem;transition:color 0.2s;white-space:nowrap;}
.site-nav a:hover,.site-nav a.nav-active{color:#f5ead0;}
.site-nav a.nav-active{border-bottom:1px solid rgba(220,192,137,0.5);}
.nav-dot{color:rgba(220,192,137,0.35);font-size:0.5rem;line-height:1;align-self:center;}
.nav-hamburger{display:none;background:none;border:1px solid rgba(220,192,137,0.35);border-radius:3px;color:#f5ead0;cursor:pointer;padding:0.3rem 0.55rem;font-size:1rem;line-height:1;margin-left:auto;}
.nav-hamburger:hover{border-color:rgba(220,192,137,0.7);}
.nav-brand{font-family:'Cinzel',serif;font-size:0.72rem;letter-spacing:0.13em;text-transform:uppercase;color:rgba(245,234,208,0.82);text-decoration:none;padding:0.6rem 0.65rem;white-space:nowrap;}
.nav-brand:hover{color:#f5ead0;}
.nav-links{display:flex;align-items:center;flex-wrap:wrap;justify-content:center;}
.nav-drawer{display:none;}
.site-nav a.nav-coffee{color:#f8d568;}
.site-nav a.nav-coffee:hover{color:#ffe89a;}
.nav-drawer a.nav-coffee{color:#f8d568;}
@media(max-width:860px){.site-nav a{font-size:0.55rem;padding:0.5rem 0.45rem;letter-spacing:0.08em;}.nav-dot{display:none;}}
@media(max-width:600px){
  .nav-inner{justify-content:space-between;flex-wrap:nowrap;}
  .nav-links{display:none;}
  .nav-hamburger{display:block;}
  .nav-drawer{display:block;max-height:0;overflow:hidden;transition:max-height 0.3s ease;}
  .nav-drawer.open{max-height:30rem;}
  .nav-drawer a{display:block;font-family:'Cinzel',serif;font-size:0.74rem;letter-spacing:0.12em;text-transform:uppercase;color:rgba(245,234,208,0.82);text-decoration:none;padding:0.7rem 1.2rem;border-top:1px solid rgba(220,192,137,0.12);transition:background 0.2s,color 0.2s;}
  .nav-drawer a:hover,.nav-drawer a.nav-active{background:rgba(220,192,137,0.08);color:#f5ead0;}
  .nav-drawer a.nav-active{border-left:2px solid rgba(220,192,137,0.6);}
}

/* ── Support Me dropdown (desktop nav) ── */
.nav-dropdown{position:relative;display:inline-block;}
.nav-dropdown-trigger{font-family:'Cinzel',serif;font-size:0.72rem;letter-spacing:0.13em;text-transform:uppercase;color:#f8d568;background:none;border:none;cursor:pointer;padding:0.6rem 0.65rem;white-space:nowrap;display:inline-flex;align-items:center;gap:0.3rem;transition:color 0.2s;}
.nav-dropdown-trigger:hover,.nav-dropdown.open .nav-dropdown-trigger{color:#ffe89a;}
.nav-dropdown-caret{font-size:0.55rem;transition:transform 0.2s;}
.nav-dropdown.open .nav-dropdown-caret{transform:rotate(180deg);}
.nav-dropdown-menu{position:absolute;top:100%;left:50%;transform:translateX(-50%);background:rgba(90,53,16,0.98);border:1px solid rgba(220,192,137,0.35);border-radius:3px;box-shadow:0 6px 18px rgba(15,8,0,0.45);padding:0.35rem 0;min-width:13rem;opacity:0;pointer-events:none;transition:opacity 0.18s ease;z-index:600;}
.nav-dropdown.open .nav-dropdown-menu{opacity:1;pointer-events:auto;}
.nav-dropdown-menu a{display:block;font-family:'Cinzel',serif;font-size:0.72rem;letter-spacing:0.13em;text-transform:uppercase;color:#f8d568;text-decoration:none;padding:0.55rem 1.1rem;transition:background 0.2s,color 0.2s;white-space:nowrap;}
.nav-dropdown-menu a:hover{background:rgba(220,192,137,0.12);color:#ffe89a;}
@media(max-width:860px){
  .nav-dropdown-trigger{font-size:0.55rem;padding:0.5rem 0.45rem;letter-spacing:0.08em;}
  .nav-dropdown-menu a{font-size:0.6rem;letter-spacing:0.1em;}
}
/* Mobile drawer: Support Me group label */
.nav-drawer-group-label{display:block;font-family:'Cinzel',serif;font-size:0.62rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:rgba(248,213,104,0.85);padding:0.9rem 1.2rem 0.35rem;border-top:1px solid rgba(220,192,137,0.18);margin-top:0.1rem;}

/* ── Map specific ── */
#mapHost{position:relative;}
#map{
  width:100%;
  height:560px;
  border:1.5px solid #7a4e20;
  border-radius:3px;
  background:#f5ead0;
}
.map-controls{
  display:flex;flex-wrap:wrap;align-items:center;gap:0.8rem;
  padding:0.75rem 0.8rem;margin-top:0.7rem;
  border:1.5px solid #7a4e20;border-radius:3px;
  background:rgba(245,234,208,0.55);
}
.layer-toggles{display:flex;flex-wrap:wrap;gap:0.45rem 0.7rem;flex:1;}
.layer-toggles label{
  font-family:'IM Fell English',serif;font-style:italic;font-size:0.95rem;
  color:#1a0f00;display:inline-flex;align-items:center;gap:0.35rem;
  cursor:pointer;user-select:none;
  padding:0.15rem 0.5rem;border:1px dashed transparent;border-radius:3px;
}
.layer-toggles label:hover{border-color:rgba(90,53,16,0.35);}
.layer-toggles input[type=checkbox]{accent-color:#5a3510;cursor:pointer;}
.slider-wrap{
  display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;
  width:100%;
}
.slider-wrap h4{
  font-family:'Cinzel',serif;font-size:0.72rem;font-weight:700;
  letter-spacing:0.12em;text-transform:uppercase;color:#1a0f00;
  margin-right:0.3rem;flex-shrink:0;
}
.slider-row{display:flex;align-items:center;gap:0.55rem;flex:1;min-width:240px;}
.slider-row input[type=range]{flex:1;accent-color:#5a3510;}
.year-label{
  font-family:'Cinzel',serif;font-variant-numeric:tabular-nums;
  font-size:0.85rem;color:#1a0f00;min-width:3rem;text-align:center;font-weight:700;
}
.reset-btn{
  font-family:'Cinzel',serif;font-size:0.7rem;letter-spacing:0.1em;
  text-transform:uppercase;background:transparent;border:1px solid #7a4e20;
  border-radius:2px;color:#1a0f00;padding:0.3rem 0.7rem;cursor:pointer;
  transition:all 0.2s;
}
.reset-btn:hover{background:#5a3510;color:#f5ead0;}
.live-stats{
  font-family:'IM Fell English',serif;font-style:italic;font-size:0.97rem;
  color:#1a0f00;text-align:center;margin-top:0.5rem;
}
.live-stats b{font-family:'Cinzel',serif;font-style:normal;font-weight:700;color:#0f0800;}

.leaflet-popup-content-wrapper,.leaflet-popup-tip{
  background:#f5ead0;color:#1a0f00;border:1.5px solid #7a4e20;
  font-family:'Crimson Text',serif;
}
.leaflet-popup-content{
  font-size:0.92rem;line-height:1.5;
}
.leaflet-popup-content b{font-family:'Cinzel',serif;letter-spacing:0.05em;}
.leaflet-tooltip{
  background:#f5ead0;color:#1a0f00;border:1px solid #7a4e20;
  font-family:'IM Fell English',serif;font-style:italic;
}
.leaflet-tooltip-top:before,.leaflet-tooltip-bottom:before,
.leaflet-tooltip-left:before,.leaflet-tooltip-right:before{border-top-color:#7a4e20;}
.legend-grad{
  background:white;padding:7px 9px;border-radius:3px;
  border:1.5px solid #7a4e20;font-family:'Crimson Text',serif;
  font-size:0.8rem;line-height:1.5;color:#1a0f00;
  max-height:none;overflow:hidden;cursor:default;
}
.legend-grad b{font-family:'Cinzel',serif;font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;}
.legend-grad i{display:inline-block;width:12px;height:12px;margin-right:5px;vertical-align:middle;border-radius:2px;}
.legend-grad .legend-toggle{display:none;}
.legend-grad .legend-body{display:block;}
@media(max-width:600px){
  .legend-grad{padding:0;cursor:pointer;font-size:0.75rem;}
  .legend-grad .legend-toggle{
    display:block;padding:5px 9px;
    font-family:'Cinzel',serif;font-size:0.65rem;letter-spacing:0.1em;
    text-transform:uppercase;color:#1a0f00;white-space:nowrap;user-select:none;
  }
  .legend-grad .legend-body{display:none;padding:5px 9px 7px;border-top:1px solid #7a4e20;}
  .legend-grad.open .legend-body{display:block;}
  .legend-grad.open .legend-toggle{border-bottom:1px solid #7a4e20;}
}

@media(max-width:600px){
  .content{padding:1rem 0.75rem 2rem;}
  .inner-border{padding:1.2rem 1rem 1.6rem;}
  .cartouche-border{padding:1rem 0.8rem 1.2rem;min-width:98%;border-radius:40% / 20%;}
  .logo-seal{width:110px;height:110px;}
  .map-title{font-size:1.45rem;}
  .map-subtitle{font-size:1rem;}
  .map-motto{font-size:1.04rem;}
  #map{height:440px;}
  .map-controls{flex-direction:column;align-items:stretch;}
  .layer-toggles{justify-content:flex-start;}
  .stat-num{font-size:1.25rem;}
  .stat-lbl{font-size:0.84rem;}
}
@media(max-width:380px){
  .content{padding:0.75rem 0.5rem 1.5rem;}
  .inner-border{padding:0.9rem 0.7rem 1.2rem;}
  .map-title{font-size:1.2rem;}
  .logo-seal{width:90px;height:90px;}
  #map{height:380px;}
  .stats-row{flex-direction:column;}
  .stat-item{border-right:none;border-bottom:1px solid rgba(90,53,16,0.3);}
  .stat-item:last-child{border-bottom:none;}
}
@media(min-width:601px) and (max-width:900px){
  .content{padding:1.5rem 1.5rem 2.5rem;}
  .map-title{font-size:1.65rem;}
  .logo-seal{width:125px;height:125px;}
  #map{height:520px;}
}
@media(min-width:901px){
  .content{padding:2.5rem 4rem 3rem;}
  .inner-border{padding:2rem 2.5rem 2.5rem;}
  .map-title{font-size:2.1rem;}
  .logo-seal{width:155px;height:155px;}
  #map{height:620px;}
}
</style>

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-G9H0YG26NY"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-G9H0YG26NY');
</script>
</head>
<body>

<div class="parchment-bg"></div>
<div class="vignette"></div>

<!-- ── Nav ── -->
<nav class="site-nav" id="siteNav">
  <div class="nav-inner">
    <div class="nav-links">
      <a href="index.html">✦ Home</a>
      <span class="nav-dot">✦</span>
      <div class="nav-dropdown">
        <button type="button" class="nav-dropdown-trigger" onclick="toggleDropdown(event,this)" aria-haspopup="true" aria-expanded="false">Explore <span class="nav-dropdown-caret">▾</span></button>
        <div class="nav-dropdown-menu" role="menu">
          <a href="index.html#waypoints" role="menuitem">Ports of Call</a>
          <a href="index.html#gallery" role="menuitem">Codiwomple</a>
          <a href="index.html#memories" role="menuitem">Memories</a>
          <a href="journeys.html" class="nav-active" role="menuitem">🗺 My Journeys</a>
          <a href="index.html#track" role="menuitem">Track Me</a>
        </div>
      </div>
      <span class="nav-dot">✦</span>
      <div class="nav-dropdown">
        <button type="button" class="nav-dropdown-trigger" onclick="toggleDropdown(event,this)" aria-haspopup="true" aria-expanded="false">Life on the Road <span class="nav-dropdown-caret">▾</span></button>
        <div class="nav-dropdown-menu" role="menu">
          <a href="nomad-guide.html" role="menuitem">⛺ Nomad Guide</a>
          <a href="gear.html" role="menuitem">🎒 Gear &amp; Goods</a>
          <a href="music.html" role="menuitem">🎵 Music for the Road</a>
        </div>
      </div>
      <span class="nav-dot">✦</span>
      <a href="wallpapers.html">🎁 Gift from the Road</a>
      <span class="nav-dot">✦</span>
      <div class="nav-dropdown">
        <button type="button" class="nav-dropdown-trigger" onclick="toggleDropdown(event,this)" aria-haspopup="true" aria-expanded="false">Connect <span class="nav-dropdown-caret">▾</span></button>
        <div class="nav-dropdown-menu" role="menu">
          <a href="index.html#contact" role="menuitem">Contact</a>
          <a href="index.html#bizcard" role="menuitem">Business Card</a>
        </div>
      </div>
      <span class="nav-dot">✦</span>
      <div class="nav-dropdown" id="supportDropdown">
        <button type="button" class="nav-dropdown-trigger" onclick="toggleDropdown(event,this)" aria-haspopup="true" aria-expanded="false">✦ Support Me <span class="nav-dropdown-caret">▾</span></button>
        <div class="nav-dropdown-menu" role="menu">
          <a href="https://ko-fi.com/U7U3RUSTZ" target="_blank" rel="noopener" role="menuitem">☕ Buy Me a Coffee</a>
          <a href="https://jersey-mark-mercantile.printify.me/" target="_blank" rel="noopener" role="menuitem">🛍 Shop Merch</a>
        </div>
      </div>
    </div>
    <a href="index.html" class="nav-brand">✦ Jersey Mark</a>
    <button class="nav-hamburger" onclick="toggleNav()" aria-label="Menu">☰</button>
  </div>
  <div class="nav-drawer" id="navDrawer">
    <a href="index.html">✦ Home</a>
    <span class="nav-drawer-group-label">✦ Explore</span>
    <a href="index.html#waypoints">Ports of Call</a>
    <a href="index.html#gallery">Codiwomple</a>
    <a href="index.html#memories">Memories</a>
    <a href="journeys.html" class="nav-active">🗺 My Journeys</a>
    <a href="index.html#track">Track Me</a>
    <span class="nav-drawer-group-label">✦ Life on the Road</span>
    <a href="nomad-guide.html">⛺ Nomad Guide</a>
    <a href="gear.html">🎒 Gear &amp; Goods</a>
    <a href="music.html">🎵 Music for the Road</a>
    <a href="wallpapers.html">🎁 Gift from the Road</a>
    <span class="nav-drawer-group-label">✦ Connect</span>
    <a href="index.html#contact">Contact</a>
    <a href="index.html#bizcard">Business Card</a>
    <span class="nav-drawer-group-label">✦ Support Me</span>
    <a href="https://ko-fi.com/U7U3RUSTZ" target="_blank" rel="noopener" class="nav-coffee">☕ Buy Me a Coffee</a>
    <a href="https://jersey-mark-mercantile.printify.me/" target="_blank" rel="noopener" class="nav-coffee">🛍 Shop Merch</a>
  </div>
</nav>

<div class="content">
  <div class="outer-border">
    <div class="corner-ornament corner-tl">✦</div>
    <div class="corner-ornament corner-tr">✦</div>
    <div class="corner-ornament corner-bl">✦</div>
    <div class="corner-ornament corner-br">✦</div>
    <div class="inner-border">

      <div class="cartouche">
        <div class="cartouche-border">
          <img src="images/seal.jpg" alt="Journeys with Jersey Mark" class="logo-seal" />
          <div class="map-title">My Journeys</div>
          <div class="map-subtitle">An Interactive Map of the Road</div>
          <div class="map-motto">Every mile, every memory, every place I've laid my head</div>
        </div>
      </div>

      <div class="legend-box" style="text-align:center;">
        <div class="legend-box-title">Vital Statistics</div>
        <div class="stats-row" id="statsRow">
          <div class="stat-item"><div class="stat-num" id="statPhotos">—</div><div class="stat-lbl">Geotagged photos</div></div>
          <div class="stat-item"><div class="stat-num" id="statStays">—</div><div class="stat-lbl">Stays detected</div></div>
          <div class="stat-item"><div class="stat-num" id="statYears">—</div><div class="stat-lbl">Years on record</div></div>
        </div>
      </div>

      <div class="divider-rule">✦ The Map ✦</div>
      <div class="legend-box">
        <div class="legend-box-title">Interactive Atlas</div>
        <p style="font-family:'IM Fell English',serif;font-style:italic;font-size:1.05rem;color:#1a0f00;text-align:center;margin-bottom:0.8rem;line-height:1.55;">
          Toggle layers to switch between views. Drag the year handles to filter by date.<br>
          Click any circle for details &middot; pinch or scroll to zoom.
        </p>

        <div id="mapHost">
          <div id="map"></div>
        </div>

        <div class="map-controls">
          <div class="layer-toggles" id="layerToggles">
            <!-- populated by JS -->
          </div>
        </div>
        <div class="map-controls">
          <div class="slider-wrap">
            <h4>✦ Year Range</h4>
            <div class="slider-row">
              <span id="yMinLbl" class="year-label"></span>
              <input id="yMin" type="range" />
              <input id="yMax" type="range" />
              <span id="yMaxLbl" class="year-label"></span>
              <button id="resetBtn" class="reset-btn">Reset</button>
            </div>
          </div>
        </div>
        <div class="live-stats" id="liveStats"></div>
      </div>

      <div class="divider-rule">✦ Reading the Map ✦</div>
      <div class="legend-box">
        <div class="legend-box-title">A Cartographer's Note</div>
        <p style="font-family:'Crimson Text',serif;font-size:1rem;color:#1a0f00;line-height:1.7;text-align:left;">
          Each point on this map is a photograph I took, plotted by the GPS coordinates the camera
          recorded at the moment of the shutter. The <em>Heatmap</em> reveals where I've spent the most
          time. <em>Stays</em> are clusters where I lingered overnight or longer — the dashed
          <em>Chronological Path</em> traces my route between them in time order. The <em>State Choropleth</em>
          paints each state by photo count. Toggle the layers, drag the year slider, and the road will
          show you where it has taken me.
        </p>
      </div>

      <div class="footer-seal">
        <div class="compass-rose">✤</div>
        <p>The road is long &middot; the chart grows longer still.</p>
        <p style="margin-top:0.6rem;">Anno Domini MMXXVI &middot; Home is wherever the road leads</p>
      </div>

    </div>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<script>
const DATA = __PAYLOAD__;

// ---------- helpers ----------
function tsToYear(ts){ return ts ? new Date(ts*1000).getUTCFullYear() : null; }
function tsToDateStr(ts){ if(!ts) return ''; return new Date(ts*1000).toISOString().slice(0,10); }
const PALETTE = ["#3b4cc0","#5977e3","#7b9ff9","#a3c2fc","#c9d7f0","#f0c4c0","#f6a385","#e7745b","#cb3e38","#a02226"];
function colorForYear(y){
  if(DATA.year_min===DATA.year_max) return PALETTE[5];
  const t=(y-DATA.year_min)/(DATA.year_max-DATA.year_min);
  return PALETTE[Math.min(PALETTE.length-1, Math.floor(t*(PALETTE.length-1)))];
}

// ---------- map ----------
const map = L.map('map', { preferCanvas: true })
  .fitBounds([[DATA.bbox.min_lat, DATA.bbox.min_lon],
              [DATA.bbox.max_lat, DATA.bbox.max_lon]]);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{
  attribution:'&copy; OpenStreetMap, &copy; CartoDB', subdomains:'abcd', maxZoom:19
}).addTo(map);

// ---------- year filter state ----------
let curMin = DATA.year_min, curMax = DATA.year_max;
function filteredPoints(){
  return DATA.points.filter(p=>{
    if(!p.ts) return curMin<=DATA.year_min && curMax>=DATA.year_max;
    const y=tsToYear(p.ts);
    return y>=curMin && y<=curMax;
  });
}
function filteredStays(){
  return DATA.stays.filter(s=>s.year>=curMin && s.year<=curMax);
}

// ---------- layer builders ----------
function buildHeat(pts){
  return L.heatLayer(pts.map(p=>[p.lat,p.lon,0.5]),
    {radius:18,blur:22,minOpacity:0.35,maxZoom:12});
}
function buildHex(pts){
  const counts=new Map(); const SZ=DATA.hex_size_deg;
  for(const p of pts){
    const gy=Math.round(p.lat/SZ), gx=Math.round(p.lon/SZ);
    const cx=(gy%2===0?gx:gx+0.5)*SZ, cy=gy*SZ;
    const k=cx.toFixed(4)+','+cy.toFixed(4);
    counts.set(k,(counts.get(k)||0)+1);
  }
  if(counts.size===0) return L.layerGroup();
  let maxN=0; for(const v of counts.values()) if(v>maxN) maxN=v;
  const layer=L.layerGroup();
  for(const [k,n] of counts){
    const [cx,cy]=k.split(',').map(Number);
    const t=Math.log(1+n)/Math.log(1+maxN);
    const fill=`rgba(122, 78, 32, ${0.20 + t*0.65})`;
    const r=SZ/2*1.05; const verts=[];
    for(let i=0;i<6;i++){
      const ang=Math.PI/3*i;
      verts.push([cy+r*Math.sin(ang), cx+r*Math.cos(ang)]);
    }
    L.polygon(verts,{color:'#5a3510',weight:0.4,fillColor:fill,fillOpacity:1})
      .bindTooltip(`${n} photo${n===1?'':'s'}`).addTo(layer);
  }
  return layer;
}
function buildClusters(pts){
  const c=L.markerClusterGroup({maxClusterRadius:50,disableClusteringAtZoom:16,
    spiderfyOnMaxZoom:true,chunkedLoading:true});
  for(const p of pts){
    const m=L.circleMarker([p.lat,p.lon],
      {radius:3,weight:0,fillOpacity:0.7,fillColor:'#3a1f08'});
    m.bindPopup(`<b>${p.title}</b><br>${tsToDateStr(p.ts)}<br>(${p.lat.toFixed(4)}, ${p.lon.toFixed(4)})`);
    c.addLayer(m);
  }
  return c;
}
function buildDots(pts){
  const layer=L.layerGroup();
  for(const p of pts){
    L.circleMarker([p.lat,p.lon],
      {radius:1.6,weight:0,fillOpacity:0.45,fillColor:'#3a1f08'}).addTo(layer);
  }
  return layer;
}
function buildStays(stays){
  const layer=L.layerGroup();
  for(const s of stays){
    const r=Math.max(5,Math.min(28,Math.sqrt(s.nights)*3));
    const c=colorForYear(s.year);
    L.circleMarker([s.lat,s.lon],
      {radius:r,color:c,weight:2,fillColor:c,fillOpacity:0.45})
      .bindPopup(
        (() => {
          const title = s.place ? s.place : `Stay #${s.id}`;
          let html = `<b>${title}</b><br>${s.start} &rarr; ${s.end}<br>` +
            `${s.nights} night${s.nights===1?'':'s'} &middot; ${s.photos.toLocaleString()} photo${s.photos===1?'':'s'}<br>` +
            `<small>(${s.lat.toFixed(3)}, ${s.lon.toFixed(3)})</small>`;
          if (s.thumbs && s.thumbs.length) {
            html += `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">` +
              s.thumbs.map(t => `<img src="${t.thumb}" alt="" style="width:80px;height:auto;border:1px solid #5a3510;">`).join('') +
              `</div>`;
          }
          return html;
        })())
      .bindTooltip(`#${s.id} ${s.start} (${s.nights}n)`).addTo(layer);
  }
  return layer;
}
function buildPath(stays){
  if(stays.length<2) return L.layerGroup();
  const sorted=[...stays].sort((a,b)=>a.start.localeCompare(b.start));
  return L.polyline(sorted.map(s=>[s.lat,s.lon]),
    {color:'#5a3510',weight:1.5,opacity:0.6,dashArray:'4,7'});
}
function buildChoropleth(){
  if(!DATA.states) return L.layerGroup();
  const filtered=filteredPoints();
  const fracKept=DATA.points.length===0?1:filtered.length/DATA.points.length;
  let maxC=0;
  for(const f of DATA.states.features){
    const c=(f.properties.photo_count||0)*fracKept; if(c>maxC) maxC=c;
  }
  return L.geoJSON(DATA.states,{
    style:f=>{
      const c=(f.properties.photo_count||0)*fracKept;
      const t=maxC>0?Math.log(1+c)/Math.log(1+maxC):0;
      return {fillColor:c>0?`rgba(122,78,32,${0.18+t*0.62})`:'rgba(245,234,208,0.4)',
              color:'#5a3510',weight:0.6,fillOpacity:1};
    },
    onEachFeature:(f,lyr)=>{
      const c=Math.round((f.properties.photo_count||0)*fracKept);
      const name=f.properties.name||f.properties.NAME||'?';
      lyr.bindTooltip(`<b>${name}</b><br>${c.toLocaleString()} photos (approx)`);
    }
  });
}

// ---------- registry ----------
const LAYERS = {
  'Heatmap':            { builder:()=>buildHeat(filteredPoints()),     defaultOn:true,  layer:null },
  'Hex grid':           { builder:()=>buildHex(filteredPoints()),      defaultOn:false, layer:null },
  'Clustered markers':  { builder:()=>buildClusters(filteredPoints()), defaultOn:false, layer:null },
  'Raw dots':           { builder:()=>buildDots(filteredPoints()),     defaultOn:false, layer:null },
  'Stays':              { builder:()=>buildStays(filteredStays()),     defaultOn:true,  layer:null },
  'Chronological path': { builder:()=>buildPath(filteredStays()),      defaultOn:true,  layer:null },
  'US state choropleth':{ builder:()=>buildChoropleth(),               defaultOn:false, layer:null },
};
const visibility = new Set();
for(const [name,e] of Object.entries(LAYERS)){
  e.layer = e.builder();
  if(e.defaultOn){ e.layer.addTo(map); visibility.add(name); }
}

// ---------- custom layer toggles (parchment-styled) ----------
const toggles = document.getElementById('layerToggles');
for(const [name,e] of Object.entries(LAYERS)){
  const id='tgl_'+name.replace(/[^a-z]/gi,'');
  const lbl=document.createElement('label');
  lbl.innerHTML = `<input type="checkbox" id="${id}" ${e.defaultOn?'checked':''} /> ${name}`;
  toggles.appendChild(lbl);
  document.getElementById(id).addEventListener('change',ev=>{
    if(ev.target.checked){ e.layer.addTo(map); visibility.add(name); }
    else { map.removeLayer(e.layer); visibility.delete(name); }
  });
}

// ---------- legend (year gradient) ----------
const legend = L.control({position:'bottomright'});
legend.onAdd = () => {
  const div = L.DomUtil.create('div','legend-grad');
  let body='<b>Stays · year</b><br>';
  for(let i=0;i<PALETTE.length;i++){
    const t=i/(PALETTE.length-1);
    const yr=Math.round(DATA.year_min + t*(DATA.year_max-DATA.year_min));
    body += `<i style="background:${PALETTE[i]}"></i>${yr}<br>`;
  }
  div.innerHTML =
    `<div class="legend-toggle">🗓 Years <span class="legend-caret">▾</span></div>` +
    `<div class="legend-body">${body}</div>`;
  // Don't let taps on the legend pan/zoom the map
  L.DomEvent.disableClickPropagation(div);
  L.DomEvent.disableScrollPropagation(div);
  // Toggle open/closed when the legend is tapped on mobile
  div.addEventListener('click', () => {
    if (window.matchMedia('(max-width: 600px)').matches) {
      div.classList.toggle('open');
      const caret = div.querySelector('.legend-caret');
      if (caret) caret.textContent = div.classList.contains('open') ? '▴' : '▾';
    }
  });
  return div;
};
legend.addTo(map);

// ---------- year slider ----------
const yMin=document.getElementById('yMin'), yMax=document.getElementById('yMax');
const yMinLbl=document.getElementById('yMinLbl'), yMaxLbl=document.getElementById('yMaxLbl');
const liveStats=document.getElementById('liveStats');
const resetBtn=document.getElementById('resetBtn');

yMin.min=yMax.min=DATA.year_min; yMin.max=yMax.max=DATA.year_max;
yMin.value=DATA.year_min; yMax.value=DATA.year_max;

function refreshLabels(){
  yMinLbl.textContent=curMin; yMaxLbl.textContent=curMax;
  const pts=filteredPoints(), stays=filteredStays();
  liveStats.innerHTML = `<b>${pts.length.toLocaleString()}</b> photos &middot; ` +
                        `<b>${stays.length.toLocaleString()}</b> stays &middot; ` +
                        `${curMin}&ndash;${curMax}`;
}
function rebuildVisible(){
  for(const [name,e] of Object.entries(LAYERS)){
    if(visibility.has(name)) map.removeLayer(e.layer);
    e.layer = e.builder();
    if(visibility.has(name)) e.layer.addTo(map);
  }
}
let rebuildTimer=null;
function onSlide(){
  let lo=parseInt(yMin.value,10), hi=parseInt(yMax.value,10);
  if(lo>hi){ const t=lo; lo=hi; hi=t; }
  curMin=lo; curMax=hi; refreshLabels();
  if(rebuildTimer) clearTimeout(rebuildTimer);
  rebuildTimer=setTimeout(rebuildVisible,140);
}
yMin.addEventListener('input',onSlide);
yMax.addEventListener('input',onSlide);
resetBtn.addEventListener('click',()=>{ yMin.value=DATA.year_min; yMax.value=DATA.year_max; onSlide(); });

// ---------- header stats ----------
document.getElementById('statPhotos').textContent = DATA.stats.total_photos.toLocaleString();
document.getElementById('statStays').textContent  = DATA.stats.total_stays.toLocaleString();
document.getElementById('statYears').textContent  = (DATA.stats.year_max - DATA.stats.year_min + 1);

refreshLabels();

// ---------- nav drawer ----------
function toggleNav(){ document.getElementById('navDrawer').classList.toggle('open'); }
window.toggleNav = toggleNav;
document.querySelectorAll('#navDrawer a').forEach(a=>{
  a.addEventListener('click',()=>document.getElementById('navDrawer').classList.remove('open'));
});
function toggleDropdown(e, btn){
  e.stopPropagation();
  var dd=btn.closest('.nav-dropdown');
  document.querySelectorAll('.nav-dropdown.open').forEach(function(o){
    if(o!==dd){ o.classList.remove('open'); o.querySelector('.nav-dropdown-trigger').setAttribute('aria-expanded','false'); }
  });
  var open=dd.classList.toggle('open');
  dd.querySelector('.nav-dropdown-trigger').setAttribute('aria-expanded',open?'true':'false');
}
window.toggleDropdown = toggleDropdown;
document.addEventListener('click',function(e){
  document.querySelectorAll('.nav-dropdown.open').forEach(function(dd){
    if(!dd.contains(e.target)){ dd.classList.remove('open'); dd.querySelector('.nav-dropdown-trigger').setAttribute('aria-expanded','false'); }
  });
});
document.querySelectorAll('.nav-dropdown-menu a').forEach(function(a){
  a.addEventListener('click',function(){
    var dd=a.closest('.nav-dropdown');
    dd.classList.remove('open');
    dd.querySelector('.nav-dropdown-trigger').setAttribute('aria-expanded','false');
  });
});
</script>

<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
