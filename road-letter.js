/* The Road Letter signup (2026-09-29).
 *
 * Put <div data-road-letter data-source="jwjm-home"></div> where the form
 * should appear and load this script. Signups go to the MilePost signup
 * endpoint, which adds them to Kit; Kit sends a confirmation email before
 * anything else. `data-source` tags where they signed up, so the Growth
 * page can show which form works.
 */
(function () {
  var ENDPOINT = "https://www.milepostlabs.com/api/subscribe";
  var CSS =
    ".rl-form{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:0.8rem 0 0.4rem}" +
    ".rl-form input{font-family:'Crimson Text',Georgia,serif;font-size:1.05rem;color:#0f0800;background:#f5ead0;border:1.5px solid #7a4e20;border-radius:3px;padding:8px 10px;min-width:0}" +
    ".rl-form input[type=email]{flex:1 1 220px;max-width:320px}" +
    ".rl-form input[name=firstName]{flex:0 1 150px}" +
    ".rl-form input:focus{outline:2px solid #5a3510;outline-offset:1px}" +
    ".rl-form button{font-family:'Cinzel',Georgia,serif;font-size:0.82rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f5ead0;background:#5a3510;border:1.5px solid #3a1f08;border-radius:3px;padding:9px 16px;cursor:pointer}" +
    ".rl-form button:hover{background:#3a1f08}" +
    ".rl-form button:disabled{opacity:.6;cursor:wait}" +
    ".rl-hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}" +
    ".rl-msg{font-family:'IM Fell English',Georgia,serif;font-style:italic;font-size:1.02rem;color:#5a3510;text-align:center;min-height:1.3em}" +
    ".rl-msg.err{color:#8b1a1a}";

  function mount(el) {
    if (el.dataset.mounted) return;
    el.dataset.mounted = "1";
    var source = el.getAttribute("data-source") || "jwjm";
    el.innerHTML =
      '<form class="rl-form" novalidate>' +
      '<label class="rl-hp" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>' +
      '<input name="firstName" type="text" placeholder="First name" autocomplete="given-name" aria-label="First name (optional)">' +
      '<input name="email" type="email" placeholder="you@example.com" autocomplete="email" required aria-label="Email address">' +
      '<button type="submit">Send me the Road Letter</button>' +
      "</form>" +
      '<p class="rl-msg" role="status" aria-live="polite"></p>';
    var form = el.querySelector("form");
    var msg = el.querySelector(".rl-msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = form.querySelector("button");
      var email = form.email.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        msg.className = "rl-msg err";
        msg.textContent = "That email address doesn't look right.";
        form.email.focus();
        return;
      }
      btn.disabled = true;
      msg.className = "rl-msg";
      msg.textContent = "Sending…";
      fetch(ENDPOINT, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: email, firstName: form.firstName.value.trim(), source: source, website: form.website.value }),
      })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (!res.ok) throw new Error(res.d.error || "The signup didn't go through. Please try again.");
          form.hidden = true;
          msg.textContent = "Almost there: check your inbox and confirm, and the next Road Letter will find you.";
        })
        .catch(function (err) {
          msg.className = "rl-msg err";
          msg.textContent = err.message || "The signup didn't go through. Please try again.";
          btn.disabled = false;
        });
    });
  }

  function init() {
    if (!document.getElementById("rl-css")) {
      var st = document.createElement("style");
      st.id = "rl-css";
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    document.querySelectorAll("[data-road-letter]").forEach(mount);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
