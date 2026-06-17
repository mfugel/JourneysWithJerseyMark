// Vercel serverless function.
// GET /api/fetch-album-photos?url=https://photos.app.goo.gl/...
// Returns { title, photos: string[] } — 25-30 photo URLs ready to paste.
//
// Google Photos embeds photo data in AF_initDataCallback script blocks in the
// initial HTML. We extract all lh3.googleusercontent.com/pw/ token strings from
// that raw HTML, normalize the size suffix to =w1200-h900-no, deduplicate, and
// return an evenly-spaced selection of up to 30.

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS')
  if (req.method === 'OPTIONS') return res.status(200).end()
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET')
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { url } = req.query
  if (!url || typeof url !== 'string') {
    return res.status(400).json({ error: 'Missing url parameter' })
  }

  try {
    // Step 1 — resolve short links (photos.app.goo.gl → photos.google.com/...)
    const resolvedUrl = await resolveRedirect(url)

    // Step 2 — fetch the album page HTML
    const html = await fetchHtml(resolvedUrl)
    if (!html) return res.status(502).json({ error: 'Could not fetch album page' })

    // Step 3 — extract title from <title> tag
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i)
    const rawTitle = titleMatch ? titleMatch[1].trim() : ''
    const title = cleanTitle(rawTitle)

    // Step 4 — extract all lh3 photo tokens from the embedded JSON blobs
    const photos = extractPhotos(html)
    if (photos.length === 0) {
      return res.status(422).json({
        error: 'No photos found — the album may be private or the URL may have changed.',
      })
    }

    return res.status(200).json({ title, photos })
  } catch (err) {
    console.error('[fetch-album-photos]', err)
    return res.status(500).json({ error: err.message || 'Unknown error' })
  }
}

// Follow up to 5 redirects to resolve short URLs
async function resolveRedirect(url) {
  let current = url
  for (let i = 0; i < 5; i++) {
    const r = await fetch(current, {
      method: 'HEAD',
      redirect: 'manual',
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; JerseyMarkBot/1.0)' },
    })
    const loc = r.headers.get('location')
    if (!loc) break
    current = loc.startsWith('http') ? loc : new URL(loc, current).href
  }
  return current
}

async function fetchHtml(url) {
  const r = await fetch(url, {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.9',
    },
    signal: AbortSignal.timeout(10000),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status} fetching album page`)
  return r.text()
}

// Pull every lh3.googleusercontent.com/pw/ token out of the raw HTML.
// The page embeds them in JSON inside <script> blocks — they appear as
// escaped strings like "https:\/\/lh3.googleusercontent.com\/pw\/TOKEN"
// or unescaped. Grab both forms.
function extractPhotos(html) {
  const seen = new Set()
  const results = []

  // Match the token portion (everything after /pw/ up to a quote, whitespace, or =)
  const re = /lh3\.googleusercontent\.com\/pw\/([\w-]+)/g
  let m
  while ((m = re.exec(html)) !== null) {
    const token = m[1]
    if (seen.has(token)) continue
    // Skip very short tokens (likely thumbnails/avatars, not full photos)
    if (token.length < 20) continue
    seen.add(token)
    results.push(`https://lh3.googleusercontent.com/pw/${token}=w1200-h900-no`)
  }

  // Pick up to 30 evenly spaced photos so we don't spam a huge album
  return selectEvenly(results, 30)
}

function selectEvenly(arr, max) {
  if (arr.length <= max) return arr
  const step = arr.length / max
  return Array.from({ length: max }, (_, i) => arr[Math.round(i * step)])
}

// "Antelope Lake, CA - 2025 - Google Photos" → "Antelope Lake · CA · 2025"
function cleanTitle(raw) {
  return raw
    .replace(/\s*-\s*Google Photos\s*$/i, '')
    .trim()
    .replace(/\s*[,\-]\s*/g, ' · ')
}
