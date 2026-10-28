// The web session (F23-T8; R1, R15; D-36 v3.33). Every page is static and takes no input; this
// script asks the network service, whose address the page was rendered with (the site's config,
// never a template), who is signed in, and only then draws the header's Sign in link or the
// login with My problems and Sign out. The answer is shared with the page's own scripts as
// window.OPN.session, a promise, so a page costs one GET /session. A failed fetch, an answer it
// cannot read, or no script at all leaves the header empty and the page read-only (C7). The
// session is an HttpOnly cookie on the service's host: no script here can read it, and every
// call carries the X-OPN-Web header the service requires of a web request (R3).
(function () {
  "use strict";
  var me = document.currentScript;
  if (!me || !me.dataset || !me.dataset.api || typeof fetch !== "function") { return; }
  var api = me.dataset.api.replace(/\/+$/, "");

  function call(method, path, body) {
    var init = {
      method: method,
      credentials: "include",
      headers: { "X-OPN-Web": "1", "Content-Type": "application/json" }
    };
    if (body !== undefined) { init.body = JSON.stringify(body); }
    return fetch(api + path, init).then(function (resp) {
      return resp.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        return { status: resp.status, ok: resp.ok, data: data };
      });
    });
  }

  // The service's refusal, as text: {"error", "message"} (ApiError), never markup. A 401 on a
  // web call means the session behind the cookie has ended (eight hours, F23-R3) while the page
  // still shows what the session allowed; the service's own words are written for a bearer
  // client, so the page says what happened instead (F04-T59).
  var ENDED = "Your sign-in has ended.";
  function errorText(result) {
    if (result && result.status === 401) { return ENDED + " Reload the page and sign in again."; }
    var d = result && result.data;
    if (d && typeof d.message === "string" && d.message) { return d.message; }
    if (result && result.status) { return "The service answered " + String(result.status) + "."; }
    return "The service did not answer. Nothing was sent.";
  }

  function here() { return window.location.pathname + window.location.search; }

  function signInHref(path) {
    return api + "/auth/github/start?return=" + encodeURIComponent(path || here());
  }

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  // A refusal set into `out`: the text, and for an ended session a link that signs in again and
  // comes back to this page (F04-T59).
  function refusal(out, result) {
    out.textContent = "";
    if (result && result.status === 401) {
      out.appendChild(document.createTextNode(ENDED + " "));
      out.appendChild(el("a", { href: signInHref() }, "Sign in again"));
      out.appendChild(document.createTextNode(", then send it once more."));
      return;
    }
    out.textContent = errorText(result);
  }

  var session = call("GET", "/session").then(function (r) {
    if (!r.ok || !r.data || typeof r.data.signed_in !== "boolean") { throw new Error("session"); }
    var s = r.data;
    if (s.signed_in) {
      s.stewards = Array.isArray(s.stewards) ? s.stewards.map(String) : [];
      s.curator = s.curator === true;
      s.login = String(s.login || "");
    }
    return s;
  });

  window.OPN = {
    api: api, call: call, session: session, errorText: errorText, refusal: refusal,
    signInHref: signInHref, el: el
  };

  var slot = document.querySelector(".session-slot[data-session]");
  session.then(function (s) {
    if (!slot) { return; }
    if (!s.signed_in) {
      slot.appendChild(el("a", { "class": "session-in", href: signInHref() }, "Sign in"));
    } else {
      slot.appendChild(el("span", { "class": "session-login" }, s.login));
      slot.appendChild(el("a", { href: "/me/" }, "My problems"));
      var out = el("a", { href: "#", "class": "session-out" }, "Sign out");
      out.addEventListener("click", function (ev) {
        ev.preventDefault();
        call("POST", "/session/end").then(function () { window.location.reload(); },
          function () { window.location.reload(); });
      });
      slot.appendChild(out);
    }
    slot.hidden = false;
  }).catch(function () { /* the header stays empty: the read-only page */ });

  // F26-T12 (R16): the review page's answer form. The static page carries one empty slot,
  // .review-answer-ctl[data-review-answer], with the target and the questions waiting as data;
  // nothing in it posts. Once the session answers, a signed-in login gets one box per question
  // that posts to POST /reviews/<t>/answers (the service checks that the login is the intent
  // signer and opens the record's pull request; every refusal is set as text); a visitor sees
  // the sign-in link. No service, no session, no form (C7).
  var answerSlot = document.querySelector(".review-answer-ctl[data-review-answer]");
  if (answerSlot) {
    var questions = [];
    try { questions = JSON.parse(answerSlot.dataset.questions || "[]"); } catch (e) { questions = []; }
    var target = answerSlot.dataset.target || "";
    session.then(function (s) {
      if (!questions.length) { return; }
      if (!s.signed_in) {
        var p = el("p", { "class": "cue" }, "The intent signer answers here, signed in: ");
        p.appendChild(el("a", { href: signInHref() }, "Sign in"));
        answerSlot.appendChild(p);
        answerSlot.hidden = false;
        return;
      }
      questions.forEach(function (q) {
        // F26-T22 (Q24): under its own question, beside the variant it asks about; the slot
        // takes a box whose question is not in the list, and only there is the question repeated.
        var item = document.querySelector('li.question[data-question="' + String(q.id) + '"]');
        var box = el("div", { "class": "ctl-box review-answer", "data-question": String(q.id) });
        box.appendChild(el("h3", {}, "Answer " + String(q.id) + " as " + s.login));
        if (!item) { box.appendChild(el("p", { "class": "cue" }, String(q.question))); }
        var answer = el("textarea", { "class": "input", "aria-label": "Your answer, in mathematics" });
        var cites = el("input", { "class": "input", type: "text", placeholder: "Source cited (optional; an answer without one is flagged)" });
        var out = el("p", { "class": "form-error", role: "alert" });
        var button = el("button", { "class": "btn btn-secondary btn-small", type: "button" }, "Send the answer");
        button.addEventListener("click", function () {
          if (!answer.value.trim()) { out.textContent = "Write the answer first."; return; }
          button.disabled = true;
          out.textContent = "";
          call("POST", "/reviews/" + encodeURIComponent(target) + "/answers", {
            question: String(q.id), answer: answer.value, cites: cites.value.trim() || null
          }).then(function (r) {
            if (r.ok) {
              var done = el("p", { "class": "receipt", role: "status" }, "Answer sent as a record; it reaches the page once its pull request merges.");
              if (r.data && typeof r.data.pr_url === "string" && /^https:\/\//.test(r.data.pr_url)) {
                done.appendChild(document.createTextNode(" "));
                done.appendChild(el("a", { href: r.data.pr_url }, "Pull request #" + String(r.data.pr_number)));
              }
              box.parentNode.replaceChild(done, box);
              return;
            }
            out.textContent = errorText(r);
            button.disabled = false;
          }, function () { out.textContent = errorText(null); button.disabled = false; });
        });
        box.appendChild(answer);
        box.appendChild(cites);
        box.appendChild(button);
        box.appendChild(out);
        (item || answerSlot).appendChild(box);
      });
      answerSlot.hidden = false;
    }).catch(function () { /* no session: the form stays hidden */ });
  }

  // F26-T23 (R9, R14; Q24): the review page's sign form, drawn as the answer form is. The slot
  // carries the clusters (each named by its first member), the logins that hold the intent role,
  // the questions a send-back may name and how many still wait. A signed-in login signs one
  // decision for a role: the intent role when the login holds it, else the independent one, and
  // either may be chosen, since the service decides (F26-R9) and its refusal is set as text.
  // Accept and split name a cluster; a send-back names no cluster and may name a question.
  var signSlot = document.querySelector(".review-sign-ctl[data-review-sign]");
  if (signSlot) {
    var parse = function (name, fallback) {
      try { return JSON.parse(signSlot.dataset[name] || ""); } catch (e) { return fallback; }
    };
    var clusters = parse("clusters", []);
    var intentLogins = parse("intent", []).map(function (x) { return String(x).toLowerCase(); });
    var askable = parse("questions", []);
    var waitingCount = Number(parse("waiting", 0)) || 0;
    var signTarget = signSlot.dataset.target || "";
    session.then(function (s) {
      if (!s.signed_in) {
        var p = el("p", { "class": "cue" }, "The signers sign here, signed in: ");
        p.appendChild(el("a", { href: signInHref() }, "Sign in"));
        signSlot.appendChild(p);
        signSlot.hidden = false;
        return;
      }
      var box = el("div", { "class": "ctl-box review-sign" });
      box.appendChild(el("h3", {}, "Sign as " + s.login));
      if (waitingCount > 0) {
        box.appendChild(el("p", { "class": "cue" }, String(waitingCount) +
          (waitingCount === 1 ? " question is" : " questions are") +
          " still waiting for the intent signer's answer (section 3)."));
      }
      function radios(name, options, chosen) {
        var group = el("fieldset", { "class": "choice" });
        options.forEach(function (o) {
          var label = el("label", {});
          var input = el("input", { type: "radio", name: name, value: o[0] });
          if (o[0] === chosen) { input.checked = true; }
          if (o[2]) { input.disabled = true; }
          label.appendChild(input);
          label.appendChild(document.createTextNode(" " + o[1]));
          group.appendChild(label);
        });
        return group;
      }
      function picked(name) {
        var on = box.querySelector("input[name=" + name + "]:checked");
        return on ? on.value : null;
      }
      var holdsIntent = intentLogins.indexOf(s.login.toLowerCase()) >= 0;
      box.appendChild(el("p", { "class": "kicker" }, "Role"));
      box.appendChild(radios("role", [
        ["intent", "Intent signer: the surviving cluster says what the conjecture says"],
        ["independent", "Independent signer: the evidence supports it"]
      ], holdsIntent ? "intent" : "independent"));
      var none = clusters.length === 0;
      box.appendChild(el("p", { "class": "kicker" }, "Decision"));
      box.appendChild(radios("decision", [
        ["accept", "Accept the cluster", none],
        ["split", "Split: the clusters are different readings", none],
        ["send-back", "Send back"]
      ], none ? "send-back" : "accept"));
      var cluster = el("select", { "class": "input cluster", "aria-label": "The cluster" });
      clusters.forEach(function (members) {
        var rep = String(members[0]);
        var o = el("option", { value: rep }, members.length > 1
          ? rep + " (with " + members.slice(1).map(String).join(", ") + ")" : rep);
        cluster.appendChild(o);
      });
      var question = el("select", { "class": "input question", "aria-label": "The question it is sent back with" });
      question.appendChild(el("option", { value: "" }, "No question named"));
      askable.forEach(function (qid) { question.appendChild(el("option", { value: String(qid) }, String(qid))); });
      function sync() {
        var back = picked("decision") === "send-back";
        cluster.hidden = back;
        question.hidden = !back;
      }
      box.addEventListener("change", sync);
      box.appendChild(cluster);
      box.appendChild(question);
      sync();
      var out = el("p", { "class": "form-error", role: "alert" });
      var button = el("button", { "class": "btn btn-secondary btn-small", type: "button" }, "Sign");
      button.addEventListener("click", function () {
        var decision = picked("decision");
        var back = decision === "send-back";
        button.disabled = true;
        out.textContent = "";
        call("POST", "/reviews/" + encodeURIComponent(signTarget) + "/signatures", {
          role: picked("role"),
          decision: decision,
          cluster: back ? null : cluster.value,
          question: back ? (question.value || null) : null
        }).then(function (r) {
          if (r.ok) {
            var done = el("p", { "class": "receipt", role: "status" }, "Signature sent as a record; it reaches the page once its pull request merges.");
            if (r.data && typeof r.data.pr_url === "string" && /^https:\/\//.test(r.data.pr_url)) {
              done.appendChild(document.createTextNode(" "));
              done.appendChild(el("a", { href: r.data.pr_url }, "Pull request #" + String(r.data.pr_number)));
            }
            box.parentNode.replaceChild(done, box);
            return;
          }
          refusal(out, r);
          button.disabled = false;
        }, function () { refusal(out, null); button.disabled = false; });
      });
      box.appendChild(button);
      box.appendChild(out);
      signSlot.appendChild(box);
      signSlot.hidden = false;
    }).catch(function () { /* no session: the form stays hidden */ });
  }
})();
