/**
 * Command palette (⌘K) for IRIS-D — fully client-side.
 *
 * Toggles the #cmd-palette overlay, filters items as you type, supports
 * keyboard navigation, and activates items via their data-action:
 *   - "tab:<tab-id>"     → clicks the matching nav button
 *   - "click:<selector>" → clicks the target element (opens a modal, etc.)
 */
(function () {
  function palette() { return document.getElementById("cmd-palette"); }
  function isOpen() { var p = palette(); return p && p.classList.contains("open"); }
  function visibleItems() {
    return Array.prototype.slice
      .call(document.querySelectorAll("#cmd-palette .cmd-item"))
      .filter(function (el) { return el.style.display !== "none"; });
  }

  var sel = 0;

  function highlight() {
    var its = visibleItems();
    its.forEach(function (el, i) { el.classList.toggle("sel", i === sel); });
    if (its[sel]) its[sel].scrollIntoView({ block: "nearest" });
  }

  function filter(q) {
    q = (q || "").toLowerCase().trim();
    document.querySelectorAll("#cmd-palette .cmd-item").forEach(function (el) {
      var hay = el.getAttribute("data-search") || "";
      el.style.display = (!q || hay.indexOf(q) !== -1) ? "" : "none";
    });
    document.querySelectorAll("#cmd-palette .cmd-group").forEach(function (g) {
      var any = Array.prototype.slice.call(g.querySelectorAll(".cmd-item"))
        .some(function (i) { return i.style.display !== "none"; });
      g.style.display = any ? "" : "none";
    });
    sel = 0;
    highlight();
  }

  function open() {
    var p = palette();
    if (!p) return;
    p.classList.add("open");
    var inp = document.getElementById("cmd-palette-input");
    if (inp) inp.value = "";
    filter("");
    setTimeout(function () { if (inp) inp.focus(); }, 30);
  }

  function close() {
    var p = palette();
    if (p) p.classList.remove("open");
  }

  function activate(el) {
    if (!el) return;
    var action = el.getAttribute("data-action") || "";
    close();
    setTimeout(function () {
      if (action.indexOf("tab:") === 0) {
        var b = document.getElementById("tab-" + action.slice(4));
        if (b) b.click();
      } else if (action.indexOf("click:") === 0) {
        var t = document.querySelector(action.slice(6));
        if (t) t.click();
      }
    }, 20);
  }

  document.addEventListener("keydown", function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key && e.key.toLowerCase() === "k") {
      e.preventDefault();
      isOpen() ? close() : open();
      return;
    }
    if (!isOpen()) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(visibleItems().length - 1, sel + 1); highlight(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); highlight(); }
    else if (e.key === "Enter") { e.preventDefault(); activate(visibleItems()[sel]); }
  });

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.closest && t.closest("#command-palette-trigger")) { e.preventDefault(); open(); return; }
    var item = t.closest && t.closest("#cmd-palette .cmd-item");
    if (item) { activate(item); return; }
    if (t.id === "cmd-palette") { close(); }
  });

  document.addEventListener("input", function (e) {
    if (e.target && e.target.id === "cmd-palette-input") filter(e.target.value);
  });
})();
