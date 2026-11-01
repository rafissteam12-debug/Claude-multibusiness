/* Shared helpers: CSRF header on every state-changing request, German error extraction. */
(function () {
  "use strict";
  var meta = document.querySelector('meta[name="csrf-token"]');
  function csrf() { return meta ? meta.getAttribute("content") : ""; }
  function api(method, url, body, isForm) {
    var opts = { method: method, credentials: "same-origin", headers: { "X-CSRF-Token": csrf() } };
    if (body !== undefined) {
      if (isForm) { opts.body = body; } else { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    }
    return fetch(url, opts).then(function (res) {
      return res.text().then(function (t) {
        var data = null;
        try { data = t ? JSON.parse(t) : null; } catch (e) { data = null; }
        if (!res.ok) {
          var msg = data && data.error && data.error.message_de ? data.error.message_de : "Es ist ein Fehler aufgetreten (" + res.status + ").";
          var err = new Error(msg); err.status = res.status; err.data = data; throw err;
        }
        return data;
      });
    });
  }
  function say(el, text, kind) { if (!el) return; el.textContent = text; el.className = "status" + (kind ? " " + kind : ""); }
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") n.textContent = attrs[k]; else if (k === "class") n.className = attrs[k]; else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }
  window.BB = { api: api, say: say, el: el, csrf: csrf };
})();
