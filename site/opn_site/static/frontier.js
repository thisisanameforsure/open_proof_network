// Frontier filtering (F04-R7): one text filter per column, substring match, plain JavaScript,
// same-origin. Without JavaScript the full table is already on the page; this only hides rows.
// Beyond 500 rows the table is shown in pages of 500 (F04 §6).
(function () {
  "use strict";
  var table = document.querySelector("table.frontier");
  if (!table) { return; }
  var headers = table.querySelectorAll("thead th");
  var rows = Array.prototype.slice.call(table.querySelectorAll("tbody tr"));
  var PAGE = 500;
  var filters = [];
  var filterRow = document.createElement("tr");
  filterRow.className = "filters";
  Array.prototype.forEach.call(headers, function (th, i) {
    var cell = document.createElement("th");
    var input = document.createElement("input");
    input.type = "search";
    input.setAttribute("aria-label", "filter " + th.textContent);
    input.placeholder = "filter";
    input.addEventListener("input", apply);
    filters[i] = input;
    cell.appendChild(input);
    filterRow.appendChild(cell);
  });
  table.querySelector("thead").appendChild(filterRow);
  var note = document.createElement("p");
  note.className = "filter-note";
  table.parentNode.insertBefore(note, table.nextSibling);
  var more = document.createElement("button");
  more.type = "button";
  more.textContent = "Show more";
  more.hidden = true;
  more.addEventListener("click", function () { shown += PAGE; apply(); });
  note.parentNode.insertBefore(more, note.nextSibling);
  var shown = PAGE;

  function apply() {
    var wanted = filters.map(function (f) { return f.value.trim().toLowerCase(); });
    var matched = 0;
    rows.forEach(function (row) {
      var cells = row.cells;
      var ok = wanted.every(function (w, i) {
        return !w || (cells[i] && cells[i].textContent.toLowerCase().indexOf(w) !== -1);
      });
      if (ok) { matched += 1; }
      row.hidden = !ok || matched > shown;
    });
    note.textContent = matched === rows.length
      ? rows.length + " nodes on the frontier."
      : matched + " of " + rows.length + " nodes match.";
    more.hidden = matched <= shown;
  }
  apply();
})();
