/* Journeys with Jersey Mark: visitor analytics, with a "don't count me" switch.
 *
 * Loads Vercel Web Analytics on every page, and Google Analytics where the
 * tag asks for it (data-ga="G-..."), unless this browser has opted out.
 *
 * Mark's own visits shouldn't count. Neither service can filter him out by
 * IP (the RV's internet address keeps changing), so the opt-out is per
 * browser:
 *   visit any page with ?notrack=on   -> this browser is never counted again
 *   visit any page with ?notrack=off  -> counted again
 * Once per browser, per device. A small note confirms the change.
 *
 * Include:  <script src="/analytics.js" data-ga="G-G9H0YG26NY" defer></script>
 *      or:  <script src="/analytics.js" defer></script>   (Vercel only)
 */
(function () {
  var KEY = "jwjm-notrack";
  var tag = document.currentScript;
  var ga = tag && tag.getAttribute("data-ga");
  var off = false;
  var changed = null;
  try {
    var q = new URLSearchParams(location.search).get("notrack");
    if (q === "on") { localStorage.setItem(KEY, "1"); changed = "on"; }
    if (q === "off") { localStorage.removeItem(KEY); changed = "off"; }
    off = localStorage.getItem(KEY) === "1";
  } catch (e) { /* storage blocked: count as a normal visitor */ }

  if (changed) {
    var note = document.createElement("div");
    note.textContent = changed === "on"
      ? "This browser is no longer counted in analytics."
      : "This browser is counted in analytics again.";
    note.setAttribute("role", "status");
    note.style.cssText = "position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:99999;background:#2c1d0e;color:#f3e6c8;font:14px/1.4 Georgia,serif;padding:10px 16px;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.3)";
    var show = function () { document.body.appendChild(note); setTimeout(function () { note.remove(); }, 6000); };
    if (document.body) show(); else document.addEventListener("DOMContentLoaded", show);
  }
  if (off) {
    // Belt and braces: Google's documented per-property kill switch.
    if (ga) window["ga-disable-" + ga] = true;
    return;
  }

  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  var v = document.createElement("script");
  v.defer = true;
  v.src = "/_vercel/insights/script.js";
  document.head.appendChild(v);

  if (ga) {
    var g = document.createElement("script");
    g.async = true;
    g.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(ga);
    document.head.appendChild(g);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", ga);
  }
})();
