(function () {
  "use strict";
  var form = document.getElementById("upload-form");
  if (!form) return;
  var status = document.getElementById("upload-status");
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var file = form.file.files[0];
    if (!file) { BB.say(status, "Bitte wählen Sie eine Datei aus.", "error"); return; }
    if (!/\.(csv|xlsx)$/i.test(file.name)) { BB.say(status, "Bitte laden Sie eine CSV- oder XLSX-Datei hoch.", "error"); return; }
    if (file.size > 10 * 1024 * 1024) { BB.say(status, "Die Datei ist zu groß (höchstens 10 MB).", "error"); return; }
    var fd = new FormData(); fd.append("file", file);
    var btn = form.querySelector("button"); btn.disabled = true;
    BB.say(status, "Datei wird gelesen …");
    BB.api("POST", "/api/v1/uploads", fd, true).then(function (u) {
      BB.say(status, u.row_count + " Zeilen gelesen. Zuordnung wird vorgeschlagen …");
      return BB.api("POST", "/api/v1/mappings/propose", { upload_id: u.upload_id, send_real_values: form.send_real_values.checked });
    }).then(function (m) { window.location.href = "/app/mapping/" + encodeURIComponent(m.mapping_id); })
      .catch(function (e) { BB.say(status, e.message, "error"); btn.disabled = false; });
  });
})();
