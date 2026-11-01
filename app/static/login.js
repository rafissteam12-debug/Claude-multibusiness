(function () {
  "use strict";
  var form = document.getElementById("login-form");
  if (!form) return;
  var status = document.getElementById("login-status");
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var email = form.email.value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { BB.say(status, "Bitte geben Sie eine gültige E-Mail-Adresse ein.", "error"); form.email.focus(); return; }
    BB.say(status, "Wird gesendet …");
    BB.api("POST", "/api/v1/auth/magic-link", { email: email }).then(function (d) {
      BB.say(status, d.message_de, "ok");
    }).catch(function (e) { BB.say(status, e.message, "error"); });
  });
})();
