// Vercel serverless function. POST { pin } and get 200 if it matches
// JERSEYMARK_PIN env var, 401 otherwise. No session/cookie — the hub uses
// sessionStorage to remember the unlocked state for the tab. Real SSO
// across tools comes in Phase 2.

export default function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const expected = process.env.JERSEYMARK_PIN;
  if (!expected) {
    return res.status(500).json({ error: "Server PIN not configured" });
  }

  const pin = (req.body && req.body.pin) || "";
  if (typeof pin !== "string" || pin.length === 0) {
    return res.status(400).json({ error: "Missing pin" });
  }

  // Constant-time-ish comparison via length-equal check + per-char OR.
  // For a 6-digit PIN over HTTPS this is fine.
  if (pin.length !== expected.length) {
    return res.status(401).json({ error: "Invalid pin" });
  }
  let mismatch = 0;
  for (let i = 0; i < pin.length; i++) {
    mismatch |= pin.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  if (mismatch !== 0) {
    return res.status(401).json({ error: "Invalid pin" });
  }
  return res.status(200).json({ ok: true });
}
