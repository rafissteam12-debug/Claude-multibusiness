/* Seller profile form: builds the profile object from data-path inputs, PUTs it, shows German field errors. */
(function () {
  "use strict";
  var start = document.getElementById("delete-start"), box = document.getElementById("delete-confirm");
  if (start && box) {
    var sure = document.getElementById("delete-sure"), go = document.getElementById("delete-go"), st = document.getElementById("account-status");
    start.addEventListener("click", function () { box.hidden = false; start.hidden = true; sure.focus(); });
    document.getElementById("delete-cancel").addEventListener("click", function () { box.hidden = true; start.hidden = false; sure.checked = false; go.disabled = true; start.focus(); });
    sure.addEventListener("change", function () { go.disabled = !sure.checked; });
    go.addEventListener("click", function () {
      if (!sure.checked) return;
      go.disabled = true;
      BB.say(st, "Konto wird gelöscht …");
      BB.api("DELETE", "/api/v1/account").then(function () { window.location.href = "/login?geloescht=1"; })
        .catch(function (e) { BB.say(st, e.message, "error"); go.disabled = false; });
    });
  }
})();
(function () {
  "use strict";
  var form = document.getElementById("profile-form");
  if (!form) return;
  var status = document.getElementById("profile-status");
  function setPath(obj, path, value) {
    var parts = path.split("/").filter(Boolean), o = obj;
    for (var i = 0; i < parts.length - 1; i++) { o[parts[i]] = o[parts[i]] || {}; o = o[parts[i]]; }
    o[parts[parts.length - 1]] = value;
  }
  function collect() {
    var p = { seller: {}, payment_defaults: {}, defaults: {} }, exText = "";
    Array.prototype.forEach.call(form.querySelectorAll("[data-path]"), function (inp) {
      var path = inp.getAttribute("data-path"), v = inp.value.trim();
      if (path === "/defaults/vat_exemption_text") { exText = v; return; }
      if (!v) return;
      if (path === "/payment_defaults/payment_days") { var n = Number(v); v = Number.isInteger(n) ? n : v; }
      setPath(p, path, v);
    });
    var cat = p.defaults.vat_category;
    if (exText && cat && ["E", "AE", "K", "G", "O"].indexOf(cat) !== -1) { p.defaults.vat_exemptions = {}; p.defaults.vat_exemptions[cat] = { text: exText }; }
    return p;
  }
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    Array.prototype.forEach.call(form.querySelectorAll(".field-error"), function (e) { e.textContent = ""; });
    Array.prototype.forEach.call(form.querySelectorAll("[aria-invalid]"), function (e) { e.removeAttribute("aria-invalid"); });
    var hints = document.getElementById("profile-hints"); hints.textContent = "";
    BB.say(status, "Wird gespeichert …");
    BB.api("PUT", "/api/v1/seller-profile", collect()).then(function (d) {
      BB.say(status, "Profil gespeichert.", "ok");
      (d.hints_de || []).forEach(function (h) { hints.appendChild(BB.el("li", { text: h })); });
    }).catch(function (e) {
      BB.say(status, e.message, "error");
      var fields = e.data && e.data.error && e.data.error.fields || [];
      var first = null;
      fields.forEach(function (f) {
        var path = f.field.indexOf("/defaults/vat_exemptions") === 0 ? "/defaults/vat_exemption_text" : f.field;
        var target = form.querySelector('[data-err-for="' + path + '"]');
        if (!target) { BB.say(status, e.message + " " + f.message_de, "error"); return; }
        target.textContent = (target.textContent ? target.textContent + " " : "") + f.message_de;
        var inp = form.querySelector('[data-path="' + path + '"]');
        if (inp) { inp.setAttribute("aria-invalid", "true"); if (!first) first = inp; }
      });
      if (first) first.focus();
    });
  });
})();
