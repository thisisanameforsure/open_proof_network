// Confirm or dispute a literature proposal (F04-T54; D-25 v3.45, D-36 v3.33). A page is static:
// an awaiting proposal is a .lit-row carrying what a signed record needs as data (the node, the
// proposal's record relative to the node, its status, references and summary). On /me/ the rows
// sit in per-problem lists me.js shows to a steward or a curator; on a statement's page one row
// sits in a hidden .lit-act[data-target] slot. Only once session.js has the service's answer does
// this draw anything, and only for a signed-in steward of the target or a curator: Confirm posts
// the proposal's own fields to POST /literature/confirm (what /me/ has posted since F04-T38);
// Dispute opens a small form for the signer's own reading — a status, one reference, a summary —
// and posts {node_id, disputes, status, references, summary}. Signed out, or with the service
// down, nothing is drawn (C7). Every answer is set as text; nothing a contributor wrote is read
// back into markup.
(function () {
  "use strict";
  var me = document.currentScript;
  if (!window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var pulls = ((me && me.dataset.repo) || "").replace(/\/+$/, "") + "/pull/";
  var STATUSES = [
    ["open", "Open problem: no proof is known"],
    ["known", "Known: a proof is published and not formalised"],
    ["elementary", "Elementary: a routine formalisation of a known fact"]
  ];

  function parse(raw) { try { return JSON.parse(raw || "null"); } catch (e) { return null; } }

  function receipt(li, text, r) {
    var p = el("span", { "class": "receipt", role: "status" }, " " + text + " ");
    if (r.data && typeof r.data.pr_url === "string" && pulls !== "/pull/" && r.data.pr_url.indexOf(pulls) === 0) {
      p.appendChild(el("a", { href: r.data.pr_url }, "#" + String(r.data.pr_number)));
    }
    li.appendChild(p);
  }

  function post(li, body, done, controls, out) {
    controls.forEach(function (c) { c.disabled = true; });
    O.call("POST", "/literature/confirm", body).then(function (r) {
      if (r.status === 201) {
        controls.forEach(function (c) { if (c.parentNode) { c.parentNode.removeChild(c); } });
        var form = li.querySelector(".lit-dispute");
        if (form) { li.removeChild(form); }
        receipt(li, done, r);
        return;
      }
      out.textContent = O.errorText(r);
      controls.forEach(function (c) { c.disabled = false; });
    }, function () {
      out.textContent = O.errorText(null);
      controls.forEach(function (c) { c.disabled = false; });
    });
  }

  // Confirm: the proposal's own fields, as /me/ posts them (F04-T38).
  function confirmButton(li) {
    var out = el("span", { "class": "form-error", role: "alert" });
    var b = el("button", { type: "button", "class": "btn btn-ghost" }, "Confirm");
    b.addEventListener("click", function () {
      var refs = parse(li.dataset.references);
      post(li, {
        node_id: li.dataset.node,
        record: li.dataset.record,
        status: li.dataset.status,
        references: Array.isArray(refs) ? refs : [],
        summary: li.dataset.summary || ""
      }, "Confirmation filed:", li.querySelectorAll("button"), out);
    });
    li.appendChild(document.createTextNode(" "));
    li.appendChild(b);
    li.appendChild(out);
  }

  // Dispute: the signer's own reading, which the route requires (status, references, summary).
  function disputeButton(li) {
    var out = el("span", { "class": "form-error", role: "alert" });
    var b = el("button", { type: "button", "class": "btn btn-ghost" }, "Dispute");
    b.addEventListener("click", function () {
      if (li.querySelector(".lit-dispute")) { return; }
      var form = el("div", { "class": "lit-dispute ctl-box" });
      form.appendChild(el("p", { "class": "cue" },
        "Your own reading of the literature, signed as a record of yours; the proposal stays on the record as history."));
      var status = el("select", { "class": "input", "aria-label": "What the literature says of the statement" });
      STATUSES.forEach(function (s) { status.appendChild(el("option", { value: s[0] }, s[1])); });
      var summary = el("textarea", { "class": "input", name: "summary", "aria-label": "Summary: what is known, in your words" });
      summary.placeholder = "What is known, in your words";
      var title = el("input", { "class": "input", type: "text", name: "title", "aria-label": "Reference title" });
      title.placeholder = "One reference: its title (required)";
      var url = el("input", { "class": "input", type: "url", name: "url", "aria-label": "Reference URL" });
      url.placeholder = "Its https:// URL (optional)";
      var send = el("button", { type: "button", "class": "btn btn-secondary btn-small" }, "File the dispute");
      var cancel = el("button", { type: "button", "class": "btn btn-ghost btn-small" }, "Cancel");
      send.addEventListener("click", function () {
        if (!summary.value.trim()) { out.textContent = "Write the summary first."; return; }
        if (!title.value.trim()) { out.textContent = "Name one reference."; return; }
        if (url.value.trim() && url.value.trim().indexOf("https://") !== 0) {
          out.textContent = "A reference URL starts with https://.";
          return;
        }
        out.textContent = "";
        post(li, {
          node_id: li.dataset.node,
          disputes: li.dataset.record,
          status: status.value,
          references: [{ title: title.value.trim(), url: url.value.trim() || null, note: null }],
          summary: summary.value
        }, "Dispute filed:", li.querySelectorAll("button"), out);
      });
      cancel.addEventListener("click", function () { li.removeChild(form); out.textContent = ""; });
      form.appendChild(status);
      form.appendChild(summary);
      form.appendChild(title);
      form.appendChild(url);
      form.appendChild(send);
      form.appendChild(cancel);
      li.appendChild(form);
    });
    li.appendChild(document.createTextNode(" "));
    li.appendChild(b);
    li.appendChild(out);
  }

  O.literature = { confirmButton: confirmButton, disputeButton: disputeButton };

  // The statement's page: one slot, shown to a steward of the target or a curator.
  var act = document.querySelector(".lit-act[data-target]");
  if (!act) { return; }
  O.session.then(function (s) {
    if (!s.signed_in) { return; }
    if (!(s.curator || s.stewards.indexOf(act.dataset.target) >= 0)) { return; }
    Array.prototype.forEach.call(act.querySelectorAll(".lit-row"), function (li) {
      confirmButton(li);
      disputeButton(li);
    });
    act.hidden = false;
  }).catch(function () { /* no session: the page stays read-only */ });
})();
