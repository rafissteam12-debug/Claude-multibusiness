/* Mapping review: builds the Mapping JSON from the table, PUTs it, then starts the conversion. */
(function () {
  "use strict";
  var dataEl = document.getElementById("mapping-data");
  if (!dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var form = document.getElementById("mapping-form");
  var status = document.getElementById("mapping-status");
  var rows = Array.prototype.slice.call(form.querySelectorAll("tr[data-target]"));
  var hint = document.getElementById("bt10-hint");
  var ORDER = ["strip", "upper", "de_decimal", "en_decimal", "date_dmy", "date_iso", "abs", "gross_to_net", "rate_to_category", "unit_map"];

  function colName(v) { return v && v.indexOf("c:") === 0 ? D.columns[parseInt(v.slice(2), 10)] : null; }
  function refresh(tr) {
    var sel = tr.querySelector("select.src"), cst = tr.querySelector("input.const"), sample = tr.querySelector(".sample");
    cst.hidden = sel.value !== "const";
    var c = colName(sel.value);
    sample.textContent = c && D.samples[c] ? D.samples[c] : "";
    var checked = Array.prototype.slice.call(tr.querySelectorAll("input.tr:checked")).map(function (i) { return i.parentNode.textContent.trim(); });
    tr.querySelector(".tr-text").textContent = checked.length ? checked.join(", dann ") : "keine";
  }
  function bt10() {
    var tr = document.getElementById("row-bt10");
    var prof = form.querySelector("input[name=profile]:checked");
    if (!tr || !hint) return;
    var sel = tr.querySelector("select.src"), cst = tr.querySelector("input.const");
    var missing = sel.value === "" || (sel.value === "const" && !cst.value.trim());
    hint.hidden = !(missing && prof && prof.value === "xrechnung");
  }
  rows.forEach(function (tr) {
    tr.addEventListener("change", function () { refresh(tr); bt10(); });
    tr.querySelector("input.const").addEventListener("input", bt10);
    refresh(tr);
  });
  Array.prototype.forEach.call(form.querySelectorAll("input[name=profile]"), function (r) { r.addEventListener("change", bt10); });
  bt10();

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
        var v = tr.querySelector("input.const").value.trim();
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
    var formats = Array.prototype.slice.call(form.querySelectorAll("input[name=format]:checked")).map(function (i) { return i.value; });
    if (!formats.length) { BB.say(status, "Bitte wählen Sie mindestens ein Format.", "error"); return; }
    var prof = form.querySelector("input[name=profile]:checked");
    var btn = document.getElementById("convert-btn"); btn.disabled = true;
    BB.say(status, "Wird gespeichert und umgewandelt …");
    save().then(function () {
      return BB.api("POST", "/api/v1/conversions", { upload_id: D.upload_id, mapping_id: D.mapping_id, formats: formats, profile: prof ? prof.value : "xrechnung" });
    }).then(function (j) { window.location.href = "/app/jobs/" + encodeURIComponent(j.job_id); })
      .catch(function (e) { BB.say(status, e.message, "error"); btn.disabled = false; });
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
