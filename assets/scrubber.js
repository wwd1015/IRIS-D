/**
 * Draggable timeline scrubber for the Portfolio Summary composition chart.
 *
 * Drag either handle (or click a preset) to set a sub-window over the available
 * reporting periods. On release it writes "<startISO>,<endISO>" into the hidden
 * #ps-scrubber-input (a dcc.Input), which the bar + waterfall callbacks read.
 */
(function () {
  function tw() { return document.getElementById("ps-scrubber-trackwrap"); }
  function dates() {
    var t = tw(); if (!t) return [];
    try { return JSON.parse(t.getAttribute("data-dates") || "[]"); } catch (e) { return []; }
  }
  function labels() {
    var t = tw(); if (!t) return [];
    try { return JSON.parse(t.getAttribute("data-labels") || "[]"); } catch (e) { return []; }
  }
  function cur() {
    var t = tw(); if (!t) return [0, 0];
    return [parseInt(t.getAttribute("data-start") || "0", 10),
            parseInt(t.getAttribute("data-end") || "0", 10)];
  }

  var dragging = null;

  function paint(s, e) {
    var t = tw(); if (!t) return;
    var arr = dates(); var n = arr.length; if (n < 2) return;
    var pct = function (i) { return (i / (n - 1)) * 100; };
    var rng = t.querySelector(".scrubber-range");
    var hs = t.querySelector('.scrubber-handle[data-handle="start"]');
    var he = t.querySelector('.scrubber-handle[data-handle="end"]');
    if (rng) { rng.style.left = pct(s) + "%"; rng.style.width = (pct(e) - pct(s)) + "%"; }
    if (hs) hs.style.left = pct(s) + "%";
    if (he) he.style.left = pct(e) + "%";
    t.setAttribute("data-start", s);
    t.setAttribute("data-end", e);
    var lab = labels();
    var head = document.querySelector("#ps-scrubber .range");
    if (head && lab.length) {
      head.innerHTML = "<b>" + lab[s] + "</b> → <b>" + lab[e] + "</b>";
    }
  }

  function commit(s, e) {
    var arr = dates(); if (!arr.length) return;
    var inp = document.getElementById("ps-scrubber-input");
    if (!inp) return;
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(inp, arr[s] + "," + arr[e]);
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    inp.dispatchEvent(new Event("change", { bubbles: true }));
  }

  document.addEventListener("mousedown", function (ev) {
    var h = ev.target.closest && ev.target.closest('#ps-scrubber .scrubber-handle');
    if (h) { ev.preventDefault(); dragging = h.getAttribute("data-handle"); }
  });

  document.addEventListener("mousemove", function (ev) {
    if (!dragging) return;
    var t = tw(); if (!t) return;
    var box = t.getBoundingClientRect();
    var arr = dates(); var n = arr.length; if (n < 2) return;
    var x = Math.max(0, Math.min(box.width, ev.clientX - box.left));
    var idx = Math.round((x / box.width) * (n - 1));
    var c = cur(); var s = c[0], e = c[1];
    if (dragging === "start") s = Math.max(0, Math.min(idx, e - 1));
    else e = Math.min(n - 1, Math.max(idx, s + 1));
    paint(s, e);
  });

  document.addEventListener("mouseup", function () {
    if (!dragging) return;
    dragging = null;
    var c = cur();
    commit(c[0], c[1]);
  });

  document.addEventListener("click", function (ev) {
    var chip = ev.target.closest && ev.target.closest('#ps-scrubber .preset-chip');
    if (!chip) return;
    var arr = dates(); var n = arr.length; if (n < 2) return;
    var p = chip.getAttribute("data-preset");
    var e = n - 1, s;
    if (p === "all") s = 0;
    else s = Math.max(0, n - 1 - parseInt(p, 10));
    document.querySelectorAll("#ps-scrubber .preset-chip").forEach(function (c) { c.classList.remove("active"); });
    chip.classList.add("active");
    paint(s, e);
    commit(s, e);
  });
})();
