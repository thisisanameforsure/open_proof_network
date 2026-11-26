// Contributors (F34-T9, R10-R12): "Show test runs" reveals the cards of the identities the
// site's config calls test runs, and the search box filters the full ledger's rows. Without the
// script, test runs stay out of the cards and the whole ledger is listed. Same-origin, plain.
(function () {
  "use strict";
  var tools = document.querySelector("[data-tools]");
  var toggle = document.querySelector("[data-show-tests]");
  if (tools && toggle) {
    tools.hidden = false;
    toggle.addEventListener("change", function () {
      Array.prototype.forEach.call(document.querySelectorAll('[data-test="1"]'), function (card) {
        card.hidden = !toggle.checked;
      });
    });
  }
  var q = document.querySelector('[name="ledger-q"]');
  if (q) {
    var rows = Array.prototype.slice.call(document.querySelectorAll("table.ledger tbody tr"));
    q.addEventListener("input", function () {
      var needle = q.value.trim().toLowerCase();
      rows.forEach(function (row) {
        row.hidden = Boolean(needle) && row.textContent.toLowerCase().indexOf(needle) === -1;
      });
    });
  }
})();
