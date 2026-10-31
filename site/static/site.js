/* Site-wide script: first-touch campaign code + privacy-friendly events.
   No cookies, no Web Storage. The ?code= parameter is carried forward by
   rewriting links (internal pages and app links), nothing is stored. */
(function () {
  "use strict";

  var body = document.body;
  var API = body.getAttribute("data-api") || "";
  var APP_URL = body.getAttribute("data-app-url") || "";
  var ALLOWED = (body.getAttribute("data-events") || "").split(",");
  var CODE_RE = /^[a-z0-9][a-z0-9-]{0,31}$/;

  function readCode() {
    try {
      var c = new URLSearchParams(window.location.search).get("code");
      c = c ? c.toLowerCase() : "";
      return CODE_RE.test(c) ? c : "";
    } catch (e) {
      return "";
    }
  }

  var CODE = readCode();
  var MOCK = /(?:^|[?&])mock=1(?:&|$)/.test(window.location.search);

  function track(name) {
    if (MOCK || ALLOWED.indexOf(name) === -1 || !API || !navigator.sendBeacon) return;
    var payload = JSON.stringify({ name: name, path: window.location.pathname, code: CODE || null });
    try {
      navigator.sendBeacon(API + "/events", new Blob([payload], { type: "text/plain" }));
    } catch (e) { /* events are best effort */ }
  }

  function isAppLink(a) {
    return APP_URL && a.href.indexOf(APP_URL) === 0;
  }

  function withCode(a) {
    if (!CODE) return;
    var internal = a.origin === window.location.origin;
    if (!internal && !isAppLink(a)) return;
    try {
      var u = new URL(a.href);
      if (!u.searchParams.has("code")) {
        u.searchParams.set("code", CODE);
        a.href = u.toString();
      }
    } catch (e) { /* leave link as is */ }
  }

  var links = document.querySelectorAll("a[href]");
  for (var i = 0; i < links.length; i++) withCode(links[i]);

  document.addEventListener("click", function (ev) {
    var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
    if (a && (isAppLink(a) || a.hasAttribute("data-app-link"))) track("link_click");
  });

  /* E-mail sign-up: POST {email, consent, source} to /api/v1/subscribe (contracts/api.md). */
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  function initSubscribe(form) {
    var status = form.querySelector(".form-status");
    var email = form.querySelector("input[type=email]");
    var consent = form.querySelector("input[type=checkbox]");
    var button = form.querySelector("button[type=submit]");
    function say(text, kind) {
      status.textContent = text;
      status.className = "form-status" + (kind ? " is-" + kind : "");
    }
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var addr = (email.value || "").trim();
      if (!EMAIL_RE.test(addr)) { say("Bitte geben Sie eine gültige E-Mail-Adresse ein.", "error"); email.focus(); return; }
      if (!consent.checked) { say("Bitte bestätigen Sie die Einwilligung.", "error"); consent.focus(); return; }
      if (MOCK) { say("Testmodus: Es wurde keine Anmeldung gesendet.", ""); return; }
      button.disabled = true;
      say("Wird gesendet …", "");
      fetch(API + "/subscribe", {
        method: "POST", mode: "cors", credentials: "omit",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: addr, consent: true, source: form.getAttribute("data-source") || "check" })
      }).then(function (res) {
        if (res.status === 202 || res.ok) {
          say("Fast geschafft: Bitte bestätigen Sie die Anmeldung über den Link in der E-Mail, die wir Ihnen gerade geschickt haben.", "ok");
          form.reset();
          track("subscribe");
          return;
        }
        return res.json().catch(function () { return null; }).then(function (d) {
          say(d && d.error && d.error.message_de ? d.error.message_de : "Die Anmeldung hat nicht geklappt. Bitte versuchen Sie es später erneut.", "error");
        });
      }).catch(function () {
        say("Die Anmeldung ist gerade nicht möglich. Bitte versuchen Sie es später erneut.", "error");
      }).then(function () { button.disabled = false; });
    });
  }
  var forms = document.querySelectorAll("form.subscribe-form");
  for (var j = 0; j < forms.length; j++) initSubscribe(forms[j]);

  window.Belegbruecke = { track: track, code: CODE, api: API, mock: MOCK };
  track("page_view");
})();
