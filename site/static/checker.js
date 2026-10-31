/* E-Rechnung-Check: uploads one file to APP_PUBLIC_URL/api/v1/check and renders the Report.
   Report shape: contracts/mapping.md ("Report") and contracts/api.md (/api/v1/check).
   Rule: a skipped layer is shown as "übersprungen" with its reason, never as passed.
   All output uses textContent (no innerHTML): report texts are untrusted. */
(function (root) {
  "use strict";

  var FORMAT_LABELS = {
    "XRechnung-CII": "XRechnung (Syntax CII)",
    "XRechnung-UBL": "XRechnung (Syntax UBL)",
    "ZUGFeRD": "ZUGFeRD",
    "xrechnung": "XRechnung",
    "zugferd": "ZUGFeRD",
    "unknown": "nicht erkannt"
  };

  function asList(x) { return Array.isArray(x) ? x : []; }
  function asText(x) { return x === null || x === undefined ? "" : String(x); }

  function issue(e) {
    e = e || {};
    return {
      id: asText(e.id) || "ohne Kennung",
      message: asText(e.message_de) || asText(e.text_en) || "Keine Beschreibung vorhanden.",
      location: asText(e.location)
    };
  }

  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

  /* Pure: Report JSON -> view model. Exported for tests. */
  function normalizeReport(r) {
    r = r && typeof r === "object" ? r : {};
    var layers = asList(r.layers).map(function (l) {
      l = l || {};
      var errors = asList(l.errors).map(issue);
      var warnings = asList(l.warnings).map(issue);
      var ran = l.ran === true;
      var state, status;
      if (!ran) {
        state = "skip";
        status = "übersprungen – " + (asText(l.skipped_reason) || "kein Grund angegeben");
      } else if (errors.length > 0) {
        state = "fail";
        status = plural(errors.length, "Fehler", "Fehler");
      } else {
        state = "pass";
        status = "bestanden";
      }
      if (warnings.length > 0) status += ", " + plural(warnings.length, "Hinweis", "Hinweise");
      return { name: asText(l.name) || "Unbenannte Prüfstufe", state: state, status: status,
               errors: errors, warnings: warnings };
    });
    var failed = layers.filter(function (l) { return l.state === "fail"; }).length;
    var skipped = layers.filter(function (l) { return l.state === "skip"; }).length;
    // Defensive: only trust valid=true when no layer reports errors and at least one ran.
    var valid = r.valid === true && failed === 0 && layers.length > skipped;
    var fmt = asText(r.format || r.profile);
    var overall = valid
      ? "Ergebnis: gültig nach den gelaufenen Prüfstufen"
      : "Ergebnis: keine gültige E-Rechnung";
    return {
      valid: valid,
      overall: overall,
      skippedNote: skipped > 0
        ? plural(skipped, "Prüfstufe wurde", "Prüfstufen wurden") + " übersprungen und zählen nicht als bestanden."
        : "",
      format: fmt ? "Erkanntes Format: " + (FORMAT_LABELS[fmt] || fmt) : "",
      summary: asText(r.summary_de),
      totalsWarning: r.totals_warning ? "Die Summen in der Datei stimmen nicht mit den nachgerechneten Summen überein." : "",
      layers: layers,
      failedCount: failed,
      skippedCount: skipped
    };
  }

  function validateFile(file, maxBytes) {
    if (!file) return "Bitte wählen Sie eine Datei aus.";
    var name = (file.name || "").toLowerCase();
    if (!/\.(xml|pdf)$/.test(name)) return "Bitte wählen Sie eine XML- oder PDF-Datei.";
    if (file.size > maxBytes) return "Die Datei ist größer als " + Math.round(maxBytes / 1048576) + " MB.";
    if (file.size === 0) return "Die Datei ist leer.";
    return "";
  }

  var api = { normalizeReport: normalizeReport, validateFile: validateFile };
  if (typeof module !== "undefined" && module.exports) { module.exports = api; }
  root.BelegbrueckeChecker = api;

  if (typeof document === "undefined") return;

  /* ---------- DOM ---------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  function renderIssues(list, kind) {
    var ul = el("ul", "issues");
    list.forEach(function (i) {
      var li = el("li", "issue" + (kind === "warning" ? " issue-warning" : ""));
      li.appendChild(el("span", "issue-id", i.id));
      li.appendChild(document.createTextNode(": " + i.message));
      if (i.location) li.appendChild(el("span", "issue-loc", "Stelle: " + i.location));
      ul.appendChild(li);
    });
    return ul;
  }

  function render(report, notice) {
    var v = normalizeReport(report);
    var section = document.getElementById("report");
    var noticeEl = document.getElementById("report-notice");
    noticeEl.hidden = !notice;
    noticeEl.textContent = notice || "";
    var overall = document.getElementById("report-overall");
    overall.textContent = v.overall;
    overall.className = "overall " + (v.valid ? "overall-valid" : "overall-invalid");
    document.getElementById("report-format").textContent = [v.format, v.skippedNote].filter(Boolean).join(" ");
    document.getElementById("report-summary").textContent = v.summary;
    var totals = document.getElementById("report-totals");
    totals.hidden = !v.totalsWarning;
    totals.textContent = v.totalsWarning;
    var ol = document.getElementById("report-layers");
    while (ol.firstChild) ol.removeChild(ol.firstChild);
    v.layers.forEach(function (l) {
      var li = el("li", "layer layer-" + l.state);
      li.appendChild(el("span", "layer-name", l.name));
      li.appendChild(el("span", "layer-status", l.status));
      if (l.errors.length) li.appendChild(renderIssues(l.errors, "error"));
      if (l.warnings.length) li.appendChild(renderIssues(l.warnings, "warning"));
      ol.appendChild(li);
    });
    if (!v.layers.length) ol.appendChild(el("li", "layer layer-skip", "Keine Prüfstufe ist gelaufen."));
    section.hidden = false;
    var title = document.getElementById("report-title");
    if (title && title.focus) title.focus();
  }

  function loadMock(notice, status) {
    return fetch("/static/mock-report.json", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (rep) { render(rep, notice); setStatus(status, ""); })
      .catch(function () { setStatus("Der Beispielbericht konnte nicht geladen werden.", "error"); });
  }

  var statusEl;
  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = "form-status" + (kind ? " is-" + kind : "");
  }

  function errorMessage(res, data) {
    if (data && data.error && data.error.message_de) return data.error.message_de;
    if (res.status === 413) return "Die Datei ist zu groß.";
    if (res.status === 429) return "Zu viele Prüfungen in kurzer Zeit. Bitte versuchen Sie es später erneut.";
    return "Die Prüfung ist fehlgeschlagen (Status " + res.status + ").";
  }

  function init() {
    var form = document.getElementById("check-form");
    if (!form) return;
    statusEl = document.getElementById("check-status");
    var input = document.getElementById("check-file");
    var button = form.querySelector("button[type=submit]");
    var maxBytes = parseInt(form.getAttribute("data-max-bytes"), 10) || 5 * 1048576;
    var site = root.Belegbruecke || {};
    var API = document.body.getAttribute("data-api") || "";
    var mock = !!site.mock;

    if (mock) setStatus("Testmodus: Es wird ein Beispielbericht angezeigt, keine Datei wird gesendet.", "");

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var file = input.files && input.files[0];
      if (mock) {
        loadMock("Testmodus: Beispielbericht mit erfundenen Daten. Ihre Datei wurde nicht gesendet und nicht geprüft.",
                 "Beispielbericht angezeigt.");
        return;
      }
      var problem = validateFile(file, maxBytes);
      if (problem) { setStatus(problem, "error"); input.focus(); return; }

      var fd = new FormData();
      fd.append("file", file, file.name);
      button.disabled = true;
      setStatus("Datei wird geprüft …", "");
      if (site.track) site.track("check_run");

      var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
      var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 60000) : null;

      fetch(API + "/check", { method: "POST", body: fd, mode: "cors", credentials: "omit",
                              signal: ctrl ? ctrl.signal : undefined })
        .then(function (res) {
          return res.json().catch(function () { return null; }).then(function (data) {
            if (!res.ok) { setStatus(errorMessage(res, data), "error"); return; }
            if (!data || !Array.isArray(data.layers)) { setStatus("Die Antwort des Prüfdienstes war unvollständig.", "error"); return; }
            render(data, "");
            setStatus("Prüfung abgeschlossen.", "ok");
          });
        })
        .catch(function (err) {
          if (err && err.name === "AbortError") {
            setStatus("Die Prüfung hat zu lange gedauert. Bitte versuchen Sie es erneut.", "error");
            return;
          }
          return loadMock("Der Prüfdienst ist gerade nicht erreichbar. Angezeigt wird ein Beispielbericht mit erfundenen Daten. Ihre Datei wurde nicht geprüft.",
                          "Prüfdienst nicht erreichbar.");
        })
        .then(function () { button.disabled = false; if (timer) clearTimeout(timer); });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})(typeof window !== "undefined" ? window : globalThis);
