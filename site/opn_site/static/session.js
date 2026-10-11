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

  // The service's refusal, as text: {"error", "message"} (ApiError), never markup.
  function errorText(result) {
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
    api: api, call: call, session: session, errorText: errorText,
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
})();
