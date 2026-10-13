// The steward form (F23-T8; R7, R8, R15; D-32 and D-36 v3.33). The page is static: it carries an
// empty slot with the problem's id and the commitment sentence as data (from opn_gate.steward,
// its one home). Only once session.js has the service's answer does this draw anything:
// signed out, one link that signs in with GitHub and comes back here; signed in, the form —
// display name, an optional identity link, the commitment with a tick box, Become steward — or,
// for a login already a steward of this problem, the same fields starting from the name and link
// the page shows now (data-stewards), Update name, and Step down. Updating the name commits again,
// which the service writes as a restatement (F24-T7, F24-Q15). The form posts to the service's
// POST /stewards, which opens the record's pull request; every answer is set as text.
(function () {
  "use strict";
  var me = document.currentScript;
  var slot = document.querySelector(".steward-form[data-target]");
  if (!me || !slot || !window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var target = slot.dataset.target;
  var back = slot.dataset.return || window.location.pathname;
  var commitment = slot.dataset.commitment || "";
  var held = {};
  try { held = JSON.parse(slot.dataset.stewards || "{}") || {}; } catch (e) { held = {}; }

  function clear() { while (slot.firstChild) { slot.removeChild(slot.firstChild); } }

  function receipt(text, data) {
    var p = el("p", { "class": "receipt", role: "status" }, text);
    if (data && typeof data.pr_url === "string" && /^https:\/\//.test(data.pr_url)) {
      p.appendChild(document.createTextNode(" "));
      p.appendChild(el("a", { href: data.pr_url }, "Pull request #" + String(data.pr_number)));
    }
    return p;
  }

  function signedOut() {
    clear();
    slot.appendChild(el("p", {}, "Signing in with GitHub is all the form needs."));
    slot.appendChild(el("a", { "class": "btn btn-primary", href: O.signInHref(back) },
      "Sign in with GitHub to continue"));
  }

  function stepDown(s) {
    var out = el("p", { "class": "form-error", role: "alert" });
    var button = el("button", { type: "button", "class": "btn btn-secondary" }, "Step down");
    button.addEventListener("click", function () {
      button.disabled = true;
      O.call("POST", "/stewards", {
        target: target, action: "step-down", name: s.login, link: null, accept: true
      }).then(function (r) {
        if (r.status === 201) {
          clear();
          slot.appendChild(receipt("You've stepped down as steward of " + target +
            "; the problem page shows it in a few minutes.", r.data));
          return;
        }
        out.textContent = r.status === 409 ? "You're not an active steward of " + target + "." :
          O.errorText(r);
        button.disabled = false;
      }, function () { out.textContent = O.errorText(null); button.disabled = false; });
    });
    slot.appendChild(button);
    slot.appendChild(out);
  }

  // The fields, the commitment tick box and one button that commits. ``now`` is the name and
  // link the steward holds (a restatement), or null for someone becoming a steward.
  function form(s, now) {
    clear();
    var f = el("div", { "class": "steward-fields" });
    var nameLabel = el("label", { "for": "steward-name" }, "Your name, as the problem page shows it");
    var name = el("input", { id: "steward-name", "class": "input", type: "text", maxlength: "200" });
    name.value = now && typeof now.name === "string" ? now.name : s.login;
    var linkLabel = el("label", { "for": "steward-link" },
      "An identity link (optional): an institutional page or ORCID record");
    var link = el("input", { id: "steward-link", "class": "input", type: "url",
      placeholder: "https://", maxlength: "500" });
    if (now && typeof now.link === "string") { link.value = now.link; }
    var tickRow = el("label", { "class": "tick" });
    var tick = el("input", { type: "checkbox", id: "steward-accept" });
    tickRow.appendChild(tick);
    tickRow.appendChild(el("span", { "class": "commitment" }, commitment));
    var submit = el("button", { type: "button", "class": "btn btn-primary" },
      now ? "Update name" : "Become steward");
    var out = el("p", { "class": "form-error", role: "alert" });
    submit.disabled = true;
    tick.addEventListener("change", function () { submit.disabled = !tick.checked; });
    submit.addEventListener("click", function () {
      var url = link.value.trim();
      if (!name.value.trim()) { out.textContent = "Give the name the problem page should show."; return; }
      if (url && !/^https:\/\//.test(url)) { out.textContent = "The identity link starts https://."; return; }
      submit.disabled = true;
      out.textContent = "";
      O.call("POST", "/stewards", {
        target: target, action: "commit", name: name.value.trim(),
        link: url || null, accept: tick.checked
      }).then(function (r) {
        if (r.status === 201) {
          clear();
          slot.appendChild(receipt(now ?
            "Your name on " + target + " is updated; the problem page shows it in a few minutes." :
            "You're the steward of " + target + "; it shows on the problem page in a few minutes.",
            r.data));
          return;
        }
        out.textContent = O.errorText(r);
        submit.disabled = !tick.checked;
      }, function () { out.textContent = O.errorText(null); submit.disabled = !tick.checked; });
    });
    [nameLabel, name, linkLabel, link, tickRow, submit, out].forEach(function (n) { f.appendChild(n); });
    if (now) { slot.appendChild(el("p", { "class": "receipt" }, "You're a steward of " + target + ".")); }
    slot.appendChild(el("p", { "class": "kicker" }, "Signed in as " + s.login));
    slot.appendChild(f);
  }

  O.session.then(function (s) {
    if (!s.signed_in) { signedOut(); return; }
    if (s.stewards.indexOf(target) >= 0) {
      var now = Object.prototype.hasOwnProperty.call(held, s.login) ? held[s.login] : {};
      form(s, now || {});
      stepDown(s);
      return;
    }
    // F04-T44: a problem with a panel takes a new steward by invitation (D-32 v3.34); the page
    // says how, and a self-commitment would be refused at the gate, so no form is drawn.
    if (slot.dataset.invitation === "required") { return; }
    form(s, null);
  }).catch(function () { /* no form: the read-only page */ });
})();
