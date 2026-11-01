/* Mapping review: builds the Mapping JSON from the table, PUTs it, then starts the conversion.
   The convert button stays disabled while a required field is unmapped (review M4/M6). */
(function () {
  "use strict";
  var dataEl = document.getElementById("mapping-data");
  if (!dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var form = document.getElementById("mapping-form");
  var status = document.getElementById("mapping-status");
  var rows = Array.prototype.slice.call(form.querySelectorAll("tr[data-target]"));
  var byTarget = {};
  rows.forEach(function (tr) { byTarget[tr.getAttribute("data-target")] = tr; });
  var hint = document.getElementById("bt10-hint");
  var convertBtn = document.getElementById("convert-btn");
  var summary = document.getElementById("missing-summary");
  var deliveryBox = document.getElementById("delivery-eq-issue");
  var ORDER = D.order || ["strip", "upper", "de_decimal", "en_decimal", "date_dmy", "date_iso", "abs", "gross_to_net", "rate_to_category", "unit_map"];
  var MISSING = "nicht zugeordnet – bitte Spalte wählen oder festen Wert eingeben";

  function colName(v) { return v && v.indexOf("c:") === 0 ? D.columns[parseInt(v.slice(2), 10)] : null; }
  function label(tr) { var l = tr.querySelector(".field-label"); return l ? l.textContent.replace("*", "").trim() : tr.getAttribute("data-target"); }
  function isMapped(tr) {
    var sel = tr.querySelector("select.src"), cst = tr.querySelector(".const");
    if (sel.value === "") return false;
    if (sel.value === "const") return !!cst.value.trim();
    return true;
  }
  function profile() { var p = form.querySelector("input[name=profile]:checked"); return p ? p.value : "xrechnung"; }
  function requiredNow() {
    var req = (D.required || []).slice();
    if (profile() === "xrechnung") req = req.concat(D.required_xrechnung || []);
    return req;
  }
  function refresh(tr) {
    var sel = tr.querySelector("select.src"), cst = tr.querySelector(".const"), sample = tr.querySelector(".sample");
    cst.hidden = sel.value !== "const";
    var c = colName(sel.value);
    sample.textContent = c && D.samples[c] ? D.samples[c] : "";
    var checked = Array.prototype.slice.call(tr.querySelectorAll("input.tr:checked")).map(function (i) { return i.parentNode.textContent.trim(); });
    tr.querySelector(".tr-text").textContent = checked.length ? checked.join(", dann ") : "keine";
  }
  function check() {
    var req = requiredNow(), missing = [];
    rows.forEach(function (tr) {
      var t = tr.getAttribute("data-target"), msg = tr.querySelector(".missing");
      var miss = req.indexOf(t) !== -1 && !isMapped(tr);
      if (msg) msg.textContent = miss ? MISSING : "";
      tr.classList.toggle("unmapped", miss);
      if (miss) missing.push(label(tr));
    });
    var bt10 = byTarget["/buyer_reference"];
    if (hint && bt10) hint.hidden = !(profile() === "xrechnung" && !isMapped(bt10));
    if (summary) {
      summary.hidden = !missing.length;
      summary.textContent = missing.length ? "Umwandeln ist erst möglich, wenn alle Pflichtfelder zugeordnet sind. Noch offen: " + missing.join(", ") + "." : "";
    }
    if (convertBtn) convertBtn.disabled = !!convertBtn.getAttribute("data-blocked") || missing.length > 0;
    return missing;
  }
  rows.forEach(function (tr) {
    tr.addEventListener("change", function () { refresh(tr); check(); });
    tr.querySelector(".const").addEventListener("input", check);
    refresh(tr);
  });
  Array.prototype.forEach.call(form.querySelectorAll("input[name=profile]"), function (r) { r.addEventListener("change", check); });

  /* "Leistungsdatum = Rechnungsdatum": an explicit user choice that maps the delivery date to the issue-date column. */
  if (deliveryBox && byTarget["/delivery_date"] && byTarget["/issue_date"]) {
    deliveryBox.addEventListener("change", function () {
      var dTr = byTarget["/delivery_date"], iTr = byTarget["/issue_date"];
      var dSel = dTr.querySelector("select.src"), iSel = iTr.querySelector("select.src");
      if (deliveryBox.checked) {
        if (!iSel.value || iSel.value === "const") {
          deliveryBox.checked = false;
          BB.say(status, "Bitte ordnen Sie zuerst das Rechnungsdatum einer Spalte zu.", "error");
          return;
        }
        dSel.value = iSel.value;
        var on = Array.prototype.slice.call(iTr.querySelectorAll("input.tr:checked")).map(function (i) { return i.value; });
        Array.prototype.forEach.call(dTr.querySelectorAll("input.tr"), function (i) { i.checked = on.indexOf(i.value) !== -1; });
        dTr.setAttribute("data-transform", on.join(","));
        dTr.setAttribute("data-confidence", "1");
        dTr.setAttribute("data-reason", "Von Ihnen festgelegt: Leistungsdatum = Rechnungsdatum");
      } else {
        dSel.value = "";
        Array.prototype.forEach.call(dTr.querySelectorAll("input.tr"), function (i) { i.checked = false; });
      }
      refresh(dTr); check();
    });
  }
  check();

  function collect() {
    var fields = [];
    rows.forEach(function (tr) {
      var sel = tr.querySelector("select.src");
      if (!sel.value) return;
      var orig = (tr.getAttribute("data-transform") || "").split(",").filter(Boolean);
      var chosen = Array.prototype.slice.call(tr.querySelectorAll("input.tr:checked")).map(function (i) { return i.value; });
      var same = orig.length === chosen.length && orig.every(function (x) { return chosen.indexOf(x) !== -1; });
      var transform = same ? orig : ORDER.filter(function (x) { return chosen.indexOf(x) !== -1; });
      var f = { target: tr.getAttribute("data-target"), transform: transform };
      var conf = tr.getAttribute("data-confidence");
      f.confidence = conf === "" ? 1 : parseFloat(conf);
      f.reason_de = tr.getAttribute("data-reason") || "Von Ihnen festgelegt";
      if (sel.value === "const") {
        var v = tr.querySelector(".const").value.trim();
        if (!v) return;
        f.constant = v; f.transform = [];
      } else {
        f.source_column = colName(sel.value);
      }
      fields.push(f);
    });
    var gcol = document.getElementById("grouping-col").value;
    return {
      grouping: { mode: document.getElementById("grouping-mode").value, invoice_number_column: gcol === "" ? null : D.columns[parseInt(gcol, 10)] },
      fields: fields,
      save_for_reuse: document.getElementById("save-reuse").checked
    };
  }
  function save() { return BB.api("PUT", "/api/v1/mappings/" + encodeURIComponent(D.mapping_id), collect()); }

  document.getElementById("save-btn").addEventListener("click", function () {
    BB.say(status, "Wird gespeichert …");
    save().then(function () { BB.say(status, "Zuordnung gespeichert.", "ok"); }).catch(function (e) { BB.say(status, e.message, "error"); });
  });
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (check().length) { BB.say(status, "Bitte ordnen Sie zuerst alle Pflichtfelder zu.", "error"); return; }
    var formats = Array.prototype.slice.call(form.querySelectorAll("input[name=format]:checked")).map(function (i) { return i.value; });
    if (!formats.length) { BB.say(status, "Bitte wählen Sie mindestens ein Format.", "error"); return; }
    convertBtn.disabled = true;
    BB.say(status, "Wird gespeichert und umgewandelt …");
    save().then(function () {
      return BB.api("POST", "/api/v1/conversions", { upload_id: D.upload_id, mapping_id: D.mapping_id, formats: formats, profile: profile() });
    }).then(function (j) { window.location.href = "/app/jobs/" + encodeURIComponent(j.job_id); })
      .catch(function (e) { BB.say(status, e.message, "error"); check(); });
  });
  var re = document.getElementById("repropose-form");
  if (re) re.addEventListener("submit", function (ev) {
    ev.preventDefault();
    BB.say(status, "Neuer Vorschlag wird erstellt …");
    BB.api("POST", "/api/v1/mappings/propose", { upload_id: D.upload_id, send_real_values: document.getElementById("real-values").checked, ignore_saved: true })
      .then(function (m) { window.location.href = "/app/mapping/" + encodeURIComponent(m.mapping_id); })
      .catch(function (e) { BB.say(status, e.message, "error"); });
  });
})();
