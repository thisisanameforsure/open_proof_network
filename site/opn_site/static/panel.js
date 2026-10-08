// The panel and write-up controls (F24-T6; R8, R9; D-32 v3.34, D-36). The problem page is static:
// it carries two empty slots, .panel-ctl (the members and the open motions, as data) and
// .writeup-ctl (each write-up's number, title, stage, authors and signers, as data). Only once
// session.js has the service's answer does this draw anything, and only what the signed-in login
// may do: a member or curator invites and votes; an invited login accepts; anyone signed in
// records a write-up; a listed author signs it, adds its arXiv id, records a submission, an
// acceptance or a rejection, or withdraws it; a member asks the panel to verify it. Every call
// goes to the service (POST /motions, /votes, /writeups, /stewards), which opens the record's
// pull request; every answer, a refusal included, is set as text. No service, no controls (C7).
(function () {
  "use strict";
  if (!window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var panelSlot = document.querySelector(".panel-ctl[data-target]");
  var writeSlot = document.querySelector(".writeup-ctl[data-target]");
  if (!panelSlot && !writeSlot) { return; }

  function parse(raw, fallback) {
    try { var v = JSON.parse(raw || "null"); return v === null ? fallback : v; } catch (e) { return fallback; }
  }

  var target = (panelSlot || writeSlot).dataset.target;
  var panel = parse(panelSlot && panelSlot.dataset.panel, { members: [], open: [] });
  var writeups = parse(writeSlot && writeSlot.dataset.writeups, []);
  // A write-up at or above panel-verified has been verified; no second motion is offered.
  var VERIFIED = ["panel-verified", "released", "on-arxiv", "submitted", "accepted"];
  var commitment = (panelSlot && panelSlot.dataset.commitment) || "";

  function receipt(text, data) {
    var p = el("p", { "class": "receipt", role: "status" }, text);
    if (data && typeof data.pr_url === "string" && /^https:\/\//.test(data.pr_url)) {
      p.appendChild(document.createTextNode(" "));
      p.appendChild(el("a", { href: data.pr_url }, "Pull request #" + String(data.pr_number)));
    }
    return p;
  }

  // One call: disable the button, post, then the receipt in place of `box` or the refusal in `out`.
  function post(button, out, path, body, done, box) {
    button.disabled = true;
    out.textContent = "";
    O.call("POST", path, body).then(function (r) {
      if (r.ok) {
        var p = receipt(done, r.data);
        if (box && box.parentNode) { box.parentNode.replaceChild(p, box); } else { out.parentNode.insertBefore(p, out); }
        return;
      }
      out.textContent = O.errorText(r);
      button.disabled = false;
    }, function () { out.textContent = O.errorText(null); button.disabled = false; });
  }

  function field(id, label, attrs) {
    var wrap = el("div", { "class": "ctl-field" });
    wrap.appendChild(el("label", { "for": id }, label));
    var a = { id: id, "class": "input", type: "text" };
    Object.keys(attrs || {}).forEach(function (k) { a[k] = attrs[k]; });
    var input = el("input", a);
    wrap.appendChild(input);
    return { wrap: wrap, input: input };
  }

  function errorLine() { return el("p", { "class": "form-error", role: "alert" }); }

  // -- the panel -------------------------------------------------------------------------------

  function voteButtons(n) {
    var li = document.querySelector('.motions.open li[data-motion="' + String(n) + '"]');
    if (!li) { return; }
    var box = el("span", { "class": "vote-ctl" });
    var out = errorLine();
    ["yes", "no"].forEach(function (v) {
      var b = el("button", { type: "button", "class": "btn btn-secondary btn-small" }, v === "yes" ? "Yes" : "No");
      b.addEventListener("click", function () {
        post(b, out, "/votes", { target: target, motion: n, vote: v },
          "Your " + v + " vote on motion #" + String(n) + " is filed.", box);
      });
      box.appendChild(b);
    });
    li.appendChild(box);
    li.appendChild(out);
  }

  function inviteForm() {
    var box = el("div", { "class": "ctl-box invite-ctl" });
    box.appendChild(el("h3", {}, "Invite someone"));
    var login = field("invite-login", "Their GitHub login", { maxlength: "39" });
    var note = field("invite-note", "What part of the work you ask them for (optional)", { maxlength: "300" });
    var b = el("button", { type: "button", "class": "btn btn-primary" }, "Invite");
    var out = errorLine();
    b.addEventListener("click", function () {
      var who = login.input.value.trim();
      if (!who) { out.textContent = "Give the login to invite."; return; }
      var subject = { login: who };
      if (note.input.value.trim()) { subject.note = note.input.value.trim(); }
      post(b, out, "/motions", { target: target, kind: "invite", subject: subject },
        "The invitation of " + who + " is put to the panel.", box);
    });
    [login.wrap, note.wrap, b, out].forEach(function (n) { box.appendChild(n); });
    panelSlot.appendChild(box);
  }

  function acceptForm(s, inv) {
    var box = el("div", { "class": "ctl-box accept-ctl" });
    box.appendChild(el("h3", {}, "You are invited to this problem's panel"));
    if (inv.note) { box.appendChild(el("p", { "class": "invite-note" }, "Asked for: " + String(inv.note))); }
    var name = field("accept-name", "Your name, as the problem page shows it", { maxlength: "200" });
    name.input.value = s.login;
    var link = field("accept-link", "An identity link (optional): an institutional page or ORCID record",
      { type: "url", placeholder: "https://", maxlength: "500" });
    var tickRow = el("label", { "class": "tick" });
    var tick = el("input", { type: "checkbox", id: "accept-commitment" });
    tickRow.appendChild(tick);
    tickRow.appendChild(el("span", { "class": "commitment" }, commitment));
    var b = el("button", { type: "button", "class": "btn btn-primary" }, "Accept the invitation");
    b.disabled = true;
    tick.addEventListener("change", function () { b.disabled = !tick.checked; });
    var out = errorLine();
    b.addEventListener("click", function () {
      var url = link.input.value.trim();
      if (!name.input.value.trim()) { out.textContent = "Give the name the problem page should show."; return; }
      if (url && !/^https:\/\//.test(url)) { out.textContent = "The identity link starts https://."; return; }
      post(b, out, "/stewards", {
        target: target, action: "commit", name: name.input.value.trim(), link: url || null,
        accept: tick.checked, motion: inv.motion
      }, "You've accepted; you're a steward of " + target + " once the record merges.", box);
    });
    [name.wrap, link.wrap, tickRow, b, out].forEach(function (n) { box.appendChild(n); });
    panelSlot.appendChild(box);
  }

  function drawPanel(s) {
    var awaiting = s.awaiting || {};
    var member = (panel.members || []).indexOf(s.login) >= 0;
    var votes = (Array.isArray(awaiting.votes) ? awaiting.votes : []).filter(function (v) {
      return v && v.target === target;
    }).map(function (v) { return v.motion; });
    (panel.open || []).forEach(function (m) {
      if (member || votes.indexOf(m.n) >= 0) { voteButtons(m.n); }
    });
    if (member || s.curator) { inviteForm(); }
    (Array.isArray(awaiting.invitations) ? awaiting.invitations : []).forEach(function (inv) {
      if (inv && inv.target === target) { acceptForm(s, inv); }
    });
  }

  // -- the write-ups ---------------------------------------------------------------------------

  function recordForm(s) {
    var box = el("details", { "class": "ctl-box record-ctl" });
    box.appendChild(el("summary", {}, "Record a write-up"));
    var kindWrap = el("div", { "class": "ctl-field" });
    kindWrap.appendChild(el("label", { "for": "wr-kind" }, "Kind"));
    var kind = el("select", { id: "wr-kind", "class": "input" });
    kind.appendChild(el("option", { value: "paper" }, "paper"));
    kind.appendChild(el("option", { value: "note" }, "note"));
    kindWrap.appendChild(kind);
    var title = field("wr-title", "Title", { maxlength: "300" });
    var url = field("wr-url", "Where it lives (https://)", { type: "url", placeholder: "https://", maxlength: "500" });
    var authors = field("wr-authors", "Authors' GitHub logins, in order, comma-separated");
    authors.input.value = s.login;
    var model = field("wr-model", "The model that drafted it, if one did (optional)", { maxlength: "200" });
    var b = el("button", { type: "button", "class": "btn btn-primary" }, "Record it");
    var out = errorLine();
    b.addEventListener("click", function () {
      var list = authors.input.value.split(",").map(function (a) { return a.trim(); }).filter(Boolean);
      if (!title.input.value.trim()) { out.textContent = "Give the write-up's title."; return; }
      if (!/^https:\/\//.test(url.input.value.trim())) { out.textContent = "The link starts https://."; return; }
      if (!list.length) { out.textContent = "Name at least one author."; return; }
      var body = { target: target, action: "record", kind: kind.value, title: title.input.value.trim(),
        url: url.input.value.trim(), authors: list };
      if (model.input.value.trim()) { body.model = model.input.value.trim(); }
      post(b, out, "/writeups", body, "The write-up is recorded.", box);
    });
    [kindWrap, title.wrap, url.wrap, authors.wrap, model.wrap, b, out].forEach(function (n) { box.appendChild(n); });
    return box;
  }

  // One act on write-up n with an optional text field; `key` names the field in the body.
  function act(w, label, action, input) {
    var row = el("div", { "class": "ctl-act" });
    var f = null;
    if (input) {
      f = field("wr-" + action + "-" + String(w.n), input.label, { maxlength: "300" });
      row.appendChild(f.wrap);
    }
    var doi = null;
    if (action === "accepted") {
      doi = field("wr-doi-" + String(w.n), "DOI (optional)", { maxlength: "300" });
      row.appendChild(doi.wrap);
    }
    var b = el("button", { type: "button", "class": "btn btn-secondary" }, label);
    var out = errorLine();
    b.addEventListener("click", function () {
      var body = { target: target, action: action, writeup: w.n };
      if (f) {
        var v = f.input.value.trim();
        if (!v) { out.textContent = input.missing; return; }
        body[input.key] = v;
      }
      if (doi && doi.input.value.trim()) { body.doi = doi.input.value.trim(); }
      post(b, out, "/writeups", body, label + ": filed.", row);
    });
    row.appendChild(b);
    row.appendChild(out);
    return row;
  }

  function writeupControls(s, member) {
    writeups.forEach(function (w) {
      if (!w || w.stage === "withdrawn") { return; }
      var author = (w.authors || []).indexOf(s.login) >= 0;
      if (!author && !member) { return; }
      // Folded: an author of several write-ups would otherwise face every form at once.
      var box = el("details", { "class": "ctl-box writeup-acts", "data-writeup": String(w.n) });
      box.appendChild(el("summary", {}, "Act on write-up #" + String(w.n) + ": " + String(w.title)));
      if (author) {
        if ((w.signed || []).indexOf(s.login) < 0) { box.appendChild(act(w, "Sign", "author-sign")); }
        box.appendChild(act(w, "Add arXiv id", "arxiv",
          { key: "arxiv", label: "arXiv identifier, e.g. 2610.01234", missing: "Give the arXiv identifier." }));
        [["Submitted", "submitted"], ["Accepted", "accepted"], ["Rejected", "rejected"]].forEach(function (p) {
          box.appendChild(act(w, p[0], p[1], { key: "journal", label: "Journal (" + p[1] + ")",
            missing: "Give the journal's name." }));
        });
        box.appendChild(act(w, "Withdraw", "withdrawn"));
      }
      if (member && VERIFIED.indexOf(w.stage) < 0) {
        var row = el("div", { "class": "ctl-act" });
        var b = el("button", { type: "button", "class": "btn btn-secondary" }, "Ask the panel to verify this write-up");
        var out = errorLine();
        b.addEventListener("click", function () {
          post(b, out, "/motions", { target: target, kind: "verify-writeup", subject: { writeup: w.n } },
            "The verification of write-up #" + String(w.n) + " is put to the panel.", row);
        });
        row.appendChild(b);
        row.appendChild(out);
        box.appendChild(row);
      }
      writeSlot.appendChild(box);
    });
  }

  O.session.then(function (s) {
    if (!s.signed_in) {
      if (writeSlot) {
        writeSlot.appendChild(el("a", { "class": "btn btn-secondary", href: O.signInHref() },
          "Sign in with GitHub to record a write-up or take part"));
      }
      return;
    }
    var member = (panel.members || []).indexOf(s.login) >= 0;
    if (panelSlot) { drawPanel(s); }
    if (writeSlot) {
      writeupControls(s, member);
      writeSlot.appendChild(recordForm(s));
    }
  }).catch(function () { /* no controls: the read-only page */ });
})();
