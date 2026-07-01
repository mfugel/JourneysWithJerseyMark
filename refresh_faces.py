#!/usr/bin/env python3
"""Scrape Mark's 'Friends From The Road' Google Photos album and write people.json
for the People-of-the-Road slideshow. Run manually or weekly via GitHub Actions."""
import re, json, os, sys, urllib.request

ALBUM_URL = "https://photos.app.goo.gl/u5etbgE36JB5Yf9o9"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "people.json")

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "ignore")

def main():
    html = fetch(ALBUM_URL)
    # photo URLs live under /pw/ ; /a/ are profile avatars (skip)
    raw = re.findall(r'https://lh3\.googleusercontent\.com/pw/[A-Za-z0-9_\-]+', html)
    seen, urls = set(), []
    for u in raw:
        if u not in seen:
            seen.add(u); urls.append(u)
    if len(urls) < 1:
        print("No photos scraped — leaving people.json unchanged.", file=sys.stderr)
        sys.exit(1)
    people = [{"url": u} for u in urls]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(people, indent=2) + "\n")
    print(f"Wrote {len(people)} photos to people.json")

if __name__ == "__main__":
    main()
