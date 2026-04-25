"""
build_travel_heatmap.py
=======================
Walks E:\\MyPhotoArchive, reads every .json sidecar, extracts GPS coordinates
and timestamps, and writes:

  - travels.geojson          : raw points (one feature per geotagged photo)
  - travels_heatmap.html     : interactive Leaflet heatmap, opens in any browser
  - travels_summary.txt      : run summary (counts, date range, bounding box)

Usage:
    pip install folium
    python build_travel_heatmap.py

Notes:
- Filters out (0,0) "null island" entries (old/un-geotagged photos).
- Uses geoData first, falls back to geoDataExif if geoData is empty.
- Dedupes near-identical points (same ~11m square within 5 minutes) so a
  burst of photos at one spot doesn't artificially heat up the map.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ------------------------------------------------------------------ config
ROOT = Path(r"E:\MyPhotoArchive")
OUT_DIR = ROOT  # write outputs alongside the archive
GEOJSON_PATH = OUT_DIR / "travels.geojson"
HEATMAP_PATH = OUT_DIR / "travels_heatmap.html"
SUMMARY_PATH = OUT_DIR / "travels_summary.txt"

# Dedup grid: round coords to this many decimals (~11 m at 4 decimals)
COORD_ROUND = 4
# Dedup time bucket in seconds
TIME_BUCKET = 300  # 5 minutes

# Skip clearly bogus coords
def is_valid_coord(lat, lon):
    if lat is None or lon is None:
        return False
    if lat == 0.0 and lon == 0.0:
        return False
    if not (-90 <= lat <= 90):
        return False
    if not (-180 <= lon <= 180):
        return False
    return True


def extract_gps(sidecar_data):
    """Return (lat, lon, alt) or None."""
    for key in ("geoData", "geoDataExif"):
        geo = sidecar_data.get(key) or {}
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        alt = geo.get("altitude", 0.0)
        if is_valid_coord(lat, lon):
            return (lat, lon, alt)
    return None


def extract_timestamp(sidecar_data):
    """Return unix timestamp (int) or None."""
    pt = sidecar_data.get("photoTakenTime") or {}
    ts = pt.get("timestamp")
    if ts is None:
        return None
    try:
        return int(ts)
    except (TypeError, ValueError):
        return None


def main():
    if not ROOT.exists():
        print(f"ERROR: {ROOT} not found.")
        sys.exit(1)

    print(f"Scanning {ROOT} ...")
    json_count = 0
    parse_failures = 0
    no_gps = 0
    invalid_gps = 0
    points = []  # list of dicts: lat, lon, alt, ts, source

    for dirpath, _dirnames, filenames in os.walk(ROOT):
        for fname in filenames:
            if not fname.lower().endswith(".json"):
                continue
            json_count += 1
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                parse_failures += 1
                continue

            # Skip non-photo JSONs (album metadata, user info, etc.)
            if "photoTakenTime" not in data and "geoData" not in data:
                continue

            gps = extract_gps(data)
            if gps is None:
                # Distinguish "had a geo block but it was 0,0" vs "no geo block"
                if data.get("geoData") or data.get("geoDataExif"):
                    invalid_gps += 1
                else:
                    no_gps += 1
                continue

            lat, lon, alt = gps
            ts = extract_timestamp(data)

            points.append({
                "lat": lat,
                "lon": lon,
                "alt": alt,
                "ts": ts,
                "source": fpath,
            })

            if json_count % 5000 == 0:
                print(f"  scanned {json_count:,} sidecars, {len(points):,} geotagged so far ...")

    print(f"\nTotal sidecars scanned : {json_count:,}")
    print(f"Parse failures         : {parse_failures:,}")
    print(f"Photos w/o geo block   : {no_gps:,}")
    print(f"Photos w/ (0,0) coords : {invalid_gps:,}")
    print(f"Photos with valid GPS  : {len(points):,}")

    if not points:
        print("\nNo geotagged points found. Nothing to map.")
        sys.exit(0)

    # --------------------------------------------------------------- dedup
    seen = {}
    for p in points:
        key = (
            round(p["lat"], COORD_ROUND),
            round(p["lon"], COORD_ROUND),
            (p["ts"] // TIME_BUCKET) if p["ts"] else None,
        )
        # Keep first occurrence
        if key not in seen:
            seen[key] = p

    deduped = list(seen.values())
    print(f"After dedup            : {len(deduped):,} unique points")

    # --------------------------------------------------------------- stats
    lats = [p["lat"] for p in deduped]
    lons = [p["lon"] for p in deduped]
    timestamps = [p["ts"] for p in deduped if p["ts"]]

    bbox = {
        "min_lat": min(lats), "max_lat": max(lats),
        "min_lon": min(lons), "max_lon": max(lons),
    }
    center_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    center_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2

    if timestamps:
        date_min = datetime.fromtimestamp(min(timestamps), tz=timezone.utc)
        date_max = datetime.fromtimestamp(max(timestamps), tz=timezone.utc)
    else:
        date_min = date_max = None

    # Year breakdown
    year_counts = defaultdict(int)
    for p in deduped:
        if p["ts"]:
            y = datetime.fromtimestamp(p["ts"], tz=timezone.utc).year
            year_counts[y] += 1

    # ---------------------------------------------------------- write geojson
    features = []
    for p in deduped:
        props = {"altitude": p["alt"]}
        if p["ts"]:
            props["timestamp"] = p["ts"]
            props["date"] = datetime.fromtimestamp(p["ts"], tz=timezone.utc).isoformat()
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": props,
        })

    geojson = {"type": "FeatureCollection", "features": features}
    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f)
    print(f"\nWrote {GEOJSON_PATH}  ({GEOJSON_PATH.stat().st_size / 1024:,.0f} KB)")

    # ------------------------------------------------------------ write map
    try:
        import folium
        from folium.plugins import HeatMap, Fullscreen
    except ImportError:
        print("\nfolium not installed. Run: pip install folium")
        print("(GeoJSON was still written, you can map it however you like.)")
        sys.exit(0)

    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="CartoDB positron",
    )
    Fullscreen().add_to(fmap)

    heat_data = [[p["lat"], p["lon"]] for p in deduped]
    HeatMap(
        heat_data,
        radius=10,
        blur=15,
        min_opacity=0.4,
        max_zoom=12,
    ).add_to(fmap)

    # Fit map to data bounds
    fmap.fit_bounds([
        [bbox["min_lat"], bbox["min_lon"]],
        [bbox["max_lat"], bbox["max_lon"]],
    ])

    fmap.save(str(HEATMAP_PATH))
    print(f"Wrote {HEATMAP_PATH}  ({HEATMAP_PATH.stat().st_size / 1024:,.0f} KB)")

    # --------------------------------------------------------- write summary
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write("Travel Heatmap Build Summary\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Sidecars scanned       : {json_count:,}\n")
        f.write(f"Parse failures         : {parse_failures:,}\n")
        f.write(f"Photos w/o geo block   : {no_gps:,}\n")
        f.write(f"Photos w/ (0,0) coords : {invalid_gps:,}\n")
        f.write(f"Photos with valid GPS  : {len(points):,}\n")
        f.write(f"Unique points (deduped): {len(deduped):,}\n\n")
        if date_min:
            f.write(f"Date range : {date_min.date()}  ->  {date_max.date()}\n")
        f.write(f"Bounding box:\n")
        f.write(f"  Latitude  {bbox['min_lat']:.4f}  ..  {bbox['max_lat']:.4f}\n")
        f.write(f"  Longitude {bbox['min_lon']:.4f}  ..  {bbox['max_lon']:.4f}\n\n")
        f.write("Points per year:\n")
        for y in sorted(year_counts):
            bar = "#" * min(50, year_counts[y] // max(1, max(year_counts.values()) // 50))
            f.write(f"  {y}: {year_counts[y]:>6,}  {bar}\n")

    print(f"Wrote {SUMMARY_PATH}")
    print(f"\nDone. Open {HEATMAP_PATH} in your browser.")


if __name__ == "__main__":
    main()
