// Edit, approve and withdraw words (F23-T9; R12; D-3 and D-36 v3.33). A node or proof page is
// static: every gloss and explainer carries an empty, hidden slot with what a control would need
// as data (the problem, the node, the kind, the version and the words), and each section that is
// not final carries one more. Only once session.js has the service's answer does this draw
// anything, and only for a signed-in reader: Edit for anyone (a text box holding the current
// words, a live preview through POST /glosses with dry_run, then submit), Approve for a steward of
// the problem or a curator on each section that is not final (POST /approvals), Withdraw for a
// curator (POST /glosses/withdrawals). Signed out, or with the service down, nothing is drawn and
// the page is the read-only page (C7). Every answer is set as text; the preview is the service's
// own rendering of the words (opn_site.prose, the renderer this page was built with), which
// escapes everything a contributor wrote.
(function () {
  "use strict";
  var me = document.currentScript;
  if (!me || !window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var LICENCES = (me.dataset.licences || "").split(",").filter(Boolean);

  function parse(raw) { try { return JSON.parse(raw || "null"); } catch (e) { return null; } }

  function receipt(where, text, data) {
    var p = el("p", { "class": "receipt", role: "status" }, text);
    if (data && typeof data.pr_url === "string" && /^https:\/\//.test(data.pr_url)) {
      p.appendChild(document.createTextNode(" "));
      p.appendChild(el("a", { href: data.pr_url }, "Pull request #" + String(data.pr_number)));
      p.appendChild(document.createTextNode(
        ". The gate checks it; it merges on its own when green, and the page shows it then."));
    }
    where.appendChild(p);
  }

  function approveButton(slot, ctx, s) {
    var out = el("span", { "class": "form-error", role: "alert" });
    var b = el("button", { type: "button", "class": "btn btn-ghost words-btn" }, "Approve");
    b.addEventListener("click", function () {
      b.disabled = true;
      var section = slot.dataset.section;
      O.call("POST", "/approvals", {
        target: ctx.target, node: ctx.node || null, kind: ctx.kind,
        version: slot.dataset.version, sections: section ? [section] : null
      }).then(function (r) {
        if (r.status === 201) {
          slot.removeChild(b);
          receipt(slot, "Approved.", r.data);
          return;
        }
        out.textContent = O.errorText(r);
        b.disabled = false;
      }, function () { out.textContent = O.errorText(null); b.disabled = false; });
    });
    slot.appendChild(b);
    slot.appendChild(out);
    slot.hidden = false;
  }

  function editor(ctl, ctx) {
    var box = el("div", { "class": "words-editor" });
    var text = el("textarea", { "class": "input words-text", rows: "10",
      "aria-label": "The words, in Markdown" });
    text.value = ctl.dataset.text || "";
    var licence = el("select", { "class": "input", "aria-label": "Licence" });
    licence.appendChild(el("option", { value: "" }, "Choose the licence you give these words"));
    LICENCES.forEach(function (l) { licence.appendChild(el("option", { value: l }, l)); });
    var model = el("input", { "class": "input", type: "text", maxlength: "200",
      placeholder: "The model that helped, if any (D-23)", "aria-label": "Drafted with" });
    var previewHead = el("p", { "class": "kicker" }, "Preview");
    var preview = el("div", { "class": "prose words-preview" });
    var out = el("p", { "class": "form-error", role: "alert" });
    var submit = el("button", { type: "button", "class": "btn btn-primary" }, "Submit");
    var cancel = el("button", { type: "button", "class": "btn btn-ghost" }, "Cancel");

    function body(dry) {
      var b = { subject: ctx.subject, text: text.value, supersedes: ctl.dataset.head || null,
        licence: licence.value || null, dry_run: dry };
      if (model.value.trim()) { b.drafted_with = model.value.trim(); }
      return b;
    }
    var timer = null;
    var asked = 0;
    function refresh() {
      if (!licence.value) { out.textContent = "Choose a licence to see the preview."; return; }
      var n = ++asked;
      O.call("POST", "/glosses", body(true)).then(function (r) {
        if (n !== asked) { return; }
        if (r.ok && r.data && typeof r.data.preview_html === "string") {
          // The service renders the words with the site's own escaping renderer.
          preview.innerHTML = r.data.preview_html;
          out.textContent = "";
        } else { out.textContent = O.errorText(r); }
      }, function () { out.textContent = O.errorText(null); });
    }
    function later() { clearTimeout(timer); timer = setTimeout(refresh, 600); }
    text.addEventListener("input", later);
    licence.addEventListener("change", refresh);
    submit.addEventListener("click", function () {
      if (!licence.value) { out.textContent = "Choose the licence you give these words."; return; }
      submit.disabled = true;
      O.call("POST", "/glosses", body(false)).then(function (r) {
        if (r.status === 201) {
          ctl.removeChild(box);
          receipt(ctl, "Your words are filed.", r.data);
          return;
        }
        out.textContent = O.errorText(r);
        submit.disabled = false;
      }, function () { out.textContent = O.errorText(null); submit.disabled = false; });
    });
    cancel.addEventListener("click", function () { ctl.removeChild(box); });
    [text, licence, model, previewHead, preview, out, submit, cancel].forEach(function (n) {
      box.appendChild(n);
    });
    return box;
  }

  function withdrawer(ctl) {
    var box = el("div", { "class": "words-editor" });
    var reason = el("input", { "class": "input", type: "text", maxlength: "500",
      placeholder: "Why this version is withdrawn", "aria-label": "Reason" });
    var out = el("p", { "class": "form-error", role: "alert" });
    var go = el("button", { type: "button", "class": "btn btn-secondary" }, "Withdraw this version");
    go.addEventListener("click", function () {
      if (!reason.value.trim()) { out.textContent = "Give a reason."; return; }
      go.disabled = true;
      O.call("POST", "/glosses/withdrawals", { record: ctl.dataset.path, reason: reason.value.trim() })
        .then(function (r) {
          if (r.status === 201) { ctl.removeChild(box); receipt(ctl, "Withdrawal filed.", r.data); return; }
          out.textContent = O.errorText(r);
          go.disabled = false;
        }, function () { out.textContent = O.errorText(null); go.disabled = false; });
    });
    [reason, go, out].forEach(function (n) { box.appendChild(n); });
    return box;
  }

  function contextOf(node) {
    return {
      target: node.dataset.target, node: node.dataset.node || null, kind: node.dataset.kind,
      subject: parse(node.dataset.subject)
    };
  }

  O.session.then(function (s) {
    if (!s.signed_in) { return; }
    var ctls = document.querySelectorAll(".words-ctl[data-target]");
    Array.prototype.forEach.call(ctls, function (ctl) {
      var ctx = contextOf(ctl);
      if (!ctx.subject) { return; }
      var row = el("div", { "class": "words-actions" });
      var edit = el("button", { type: "button", "class": "btn btn-ghost words-btn" }, "Edit");
      edit.addEventListener("click", function () {
        if (ctl.querySelector(".words-editor")) { return; }
        ctl.appendChild(editor(ctl, ctx));
      });
      row.appendChild(edit);
      if (s.curator && ctl.dataset.path) {
        var wd = el("button", { type: "button", "class": "btn btn-ghost words-btn" }, "Withdraw");
        wd.addEventListener("click", function () {
          if (ctl.querySelector(".words-editor")) { return; }
          ctl.appendChild(withdrawer(ctl));
        });
        row.appendChild(wd);
      }
      ctl.insertBefore(row, ctl.firstChild);
      ctl.hidden = false;
    });
    var slots = document.querySelectorAll(".words-approve[data-target][data-version]");
    Array.prototype.forEach.call(slots, function (slot) {
      var ctx = contextOf(slot);
      if (slot.dataset.state === "verified") { return; }
      if (!(s.curator || s.stewards.indexOf(ctx.target) >= 0)) { return; }
      approveButton(slot, ctx, s);
    });
  }).catch(function () { /* the read-only page */ });
})();
