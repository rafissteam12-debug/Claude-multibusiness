/* Job result: polls /api/v1/conversions/{id} and renders invoices, layers (incl. skipped), errors, downloads. */
(function () {
  "use strict";
  var dataEl = document.getElementById("job-data");
  if (!dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var root = document.getElementById("job-root");
  var el = BB.el;
  var FMT = { "xrechnung-cii": "XRechnung (XML)", "zugferd": "ZUGFeRD (PDF)" };

  function layerItem(l) {
    var badge, text;
    if (!l.ran) { badge = el("span", { "class": "badge skipped", text: "übersprungen" }); text = " – nicht geprüft: " + (l.skipped_reason || "ohne Angabe"); }
    else if (l.errors.length) { badge = el("span", { "class": "badge invalid", text: l.errors.length + " Fehler" }); text = ""; }
    else { badge = el("span", { "class": "badge valid", text: "bestanden" }); text = l.warnings.length ? " (" + l.warnings.length + " Hinweise)" : ""; }
    return el("li", null, [el("strong", { text: l.name + ": " }), badge, text]);
  }
  function issueList(items) {
    return el("ul", { "class": "errors" }, items.map(function (e) {
      return el("li", null, [el("code", { text: e.id }), " ", e.message_de || e.text_en || "", e.location ? el("span", { "class": "muted small", text: " (" + e.location + ")" }) : null]);
    }));
  }
  function invoice(inv) {
    var kids = [el("h3", null, [inv.number + " ", el("span", { "class": "badge " + (inv.valid ? "valid" : "invalid"), text: inv.valid ? "gültig" : "ungültig" })])];
    if (inv.layers && inv.layers.length) kids.push(el("ul", { "class": "layers" }, inv.layers.map(layerItem)));
    else if (inv.input_error) kids.push(el("p", { "class": "muted", text: "Nicht geprüft: Angaben fehlen oder sind ungültig, die Datei wurde nicht erzeugt." }));
    if (inv.errors.length) kids.push(issueList(inv.errors));
    if (inv.warnings && inv.warnings.length) { kids.push(el("p", { "class": "small", text: "Hinweise:" })); kids.push(issueList(inv.warnings)); }
    if (inv.totals_warning) kids.push(el("p", { "class": "notice warn", text: "Die berechneten Summen weichen von den Summen in Ihrer Datei ab. Bitte prüfen Sie die Rechnung." }));
    Object.keys(inv.formats || {}).forEach(function (k) {
      var f = inv.formats[k];
      if (f.status !== "valid") kids.push(el("p", { "class": "small", text: (FMT[k] || k) + ": " + f.message_de }));
    });
    var links = [];
    Object.keys(FMT).forEach(function (k) {
      if (inv.download_urls[k]) links.push(el("a", { href: inv.download_urls[k], "class": "btn primary", text: FMT[k] + " herunterladen" }));
    });
    if (inv.download_urls.pdf) links.push(el("a", { href: inv.download_urls.pdf, text: "Lesbare PDF – keine E-Rechnung" }));
    if (links.length) kids.push(el("p", { "class": "downloads" }, links));
    return el("section", { "class": "invoice" }, kids);
  }
  function render(j) {
    root.textContent = "";
    if (j.status === "queued" || j.status === "running") { root.appendChild(el("p", { "class": "status", text: "Die Umwandlung läuft … Diese Seite aktualisiert sich selbst." })); return false; }
    if (j.status === "expired") { root.appendChild(el("p", { "class": "notice info", text: j.message_de })); return true; }
    if (j.status === "failed") { root.appendChild(el("p", { "class": "notice error", text: j.error.message_de })); return true; }
    var s = j.summary;
    root.appendChild(el("p", { "class": "big" }, [el("span", { "class": "key", text: String(s.valid) }), " von " + j.invoices.length + " erzeugten Rechnungen sind gültig."]));
    if (s.limit_reached) root.appendChild(el("p", { "class": "notice warn", text: "Ihr Monatslimit ist erreicht. Weitere gültige Rechnungen werden in diesem Monat nicht als E-Rechnung angeboten." }));
    if (j.formats_unavailable.indexOf("zugferd") !== -1) root.appendChild(el("p", { "class": "notice info", text: "ZUGFeRD ist in dieser Installation noch nicht verfügbar." }));
    if (j.zip_url) root.appendChild(el("p", null, [el("a", { href: j.zip_url, "class": "btn", text: "Alle gültigen E-Rechnungen als ZIP" })]));
    if (j.row_errors.length) {
      root.appendChild(el("h2", { text: "Zeilen, die nicht umgewandelt wurden" }));
      root.appendChild(el("ul", { "class": "errors" }, j.row_errors.map(function (e) {
        return el("li", null, [el("code", { text: e.code }), " " + e.message_de]);
      })));
      root.appendChild(el("p", { "class": "small" }, ["Korrigieren Sie die Angaben in Ihrer Datei oder die Zuordnung und laden Sie die Datei erneut hoch. ",
        el("a", { href: "/app/upload", text: "Erneut hochladen" })]));
    }
    var card = el("div", { "class": "card" }, j.invoices.map(invoice));
    if (j.invoices.length) root.appendChild(card);
    return true;
  }
  function poll(delay) {
    BB.api("GET", "/api/v1/conversions/" + encodeURIComponent(D.job_id)).then(function (j) {
      if (!render(j)) setTimeout(function () { poll(Math.min(delay * 1.5, 5000)); }, delay);
    }).catch(function (e) { root.textContent = ""; root.appendChild(el("p", { "class": "notice error", text: e.message })); });
  }
  poll(700);
})();
