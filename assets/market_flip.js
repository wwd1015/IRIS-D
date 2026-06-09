/* Market Insight — indicator cards flip to a full-history chart.
 *
 * The server emits each card's history as a `data-hist` JSON payload on the
 * `.mkt-back` face. This script (event-delegated, survives Dash re-renders):
 *   • flips a card on front-click (ignoring source links), unflips on back-click
 *   • lazily renders the banded SVG history chart into `.mkt-hist-wrap`
 *   • exports the series as CSV from the download button
 *
 * The SVG uses CSS custom properties (var(--primary-500) etc.) so it tracks the
 * day/night theme live, exactly like the design prototype. */
(function () {
  "use strict";
  if (window.__mktFlipInit) return;
  window.__mktFlipInit = true;

  var BAND_FILL = { red: "var(--red-500)", yellow: "var(--amber-500)", green: "var(--green-500)" };

  function fmt(v, h) {
    var a = Math.abs(v);
    var dp = a >= 100 ? 0 : a >= 10 ? 1 : 2;
    return (h.prefix || "") + v.toFixed(dp) + (h.suffix || "");
  }

  // Banded time-series plot for one indicator's full history (port of MktHistoryChart).
  function buildSvg(h) {
    var W = 320, H = 132, padL = 40, padR = 12, padT = 10, padB = 20;
    var pts = h.points;
    var n = pts.length;
    var vals = pts.map(function (p) { return p.v; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var bands = (h.bands || []).map(function (b) {
      return { max: (b.max === null || b.max === undefined) ? Infinity : b.max, status: b.status };
    });
    bands.forEach(function (b) {
      if (b.max !== Infinity && b.max >= lo - (hi - lo) && b.max <= hi + (hi - lo)) {
        lo = Math.min(lo, b.max); hi = Math.max(hi, b.max);
      }
    });
    var span = (hi - lo) || 1;
    lo -= span * 0.12; hi += span * 0.12;
    var x = function (i) { return padL + (i / (n - 1)) * (W - padL - padR); };
    var y = function (v) { return padT + (1 - (v - lo) / (hi - lo)) * (H - padT - padB); };
    var line = pts.map(function (p, i) { return (i ? "L" : "M") + x(i).toFixed(1) + "," + y(p.v).toFixed(1); }).join(" ");
    var area = line + " L" + x(n - 1).toFixed(1) + "," + y(lo).toFixed(1) + " L" + x(0).toFixed(1) + "," + y(lo).toFixed(1) + " Z";

    var zones = [];
    var prev = -Infinity;
    bands.forEach(function (b) {
      var zLo = Math.max(prev, lo), zHi = Math.min(b.max, hi);
      if (zHi > zLo) zones.push({ yTop: y(zHi), yBot: y(zLo), c: BAND_FILL[b.status] });
      prev = b.max;
    });

    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="mkt-hist-svg" preserveAspectRatio="xMidYMid meet">';
    zones.forEach(function (z) {
      svg += '<rect x="' + padL + '" y="' + z.yTop.toFixed(1) + '" width="' + (W - padL - padR) +
             '" height="' + Math.max(0, z.yBot - z.yTop).toFixed(1) + '" fill="' + z.c + '" opacity="0.12"/>';
    });
    bands.filter(function (b) { return b.max !== Infinity && b.max > lo && b.max < hi; }).forEach(function (b) {
      svg += '<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + y(b.max).toFixed(1) +
             '" y2="' + y(b.max).toFixed(1) + '" stroke="' + BAND_FILL[b.status] +
             '" stroke-width="1" stroke-dasharray="2 4" opacity="0.5"/>';
    });
    svg += '<text x="' + (padL - 6) + '" y="' + (y(hi) + 8).toFixed(1) + '" text-anchor="end" class="mkt-hist-axis">' + fmt(hi, h) + '</text>';
    svg += '<text x="' + (padL - 6) + '" y="' + y(lo).toFixed(1) + '" text-anchor="end" class="mkt-hist-axis">' + fmt(lo, h) + '</text>';
    svg += '<path d="' + area + '" fill="var(--primary-500)" opacity="0.08"/>';
    svg += '<path d="' + line + '" fill="none" stroke="var(--primary-500)" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"/>';
    svg += '<circle cx="' + x(n - 1).toFixed(1) + '" cy="' + y(pts[n - 1].v).toFixed(1) +
           '" r="3" fill="var(--primary-500)" stroke="var(--bg-base)" stroke-width="1.5"/>';
    svg += '<text x="' + padL + '" y="' + (H - 5) + '" text-anchor="start" class="mkt-hist-axis">' + pts[0].label + '</text>';
    svg += '<text x="' + (W - padR) + '" y="' + (H - 5) + '" text-anchor="end" class="mkt-hist-axis">' + pts[n - 1].label + '</text>';
    svg += '</svg>';
    return svg;
  }

  function parseHist(back) {
    try { return JSON.parse(back.getAttribute("data-hist")); } catch (e) { return null; }
  }

  function renderChart(back) {
    var wrap = back.querySelector(".mkt-hist-wrap");
    if (!wrap || wrap.getAttribute("data-rendered")) return;
    var h = parseHist(back);
    if (!h) return;
    wrap.innerHTML = buildSvg(h);
    wrap.setAttribute("data-rendered", "1");
  }

  function downloadCsv(card) {
    var back = card.querySelector(".mkt-back");
    if (!back) return;
    var h = parseHist(back);
    if (!h) return;
    var sufTrim = (h.suffix || "").trim();
    var head = ["period", "value" + (sufTrim ? " (" + sufTrim + ")" : "")];
    var meta = [
      ["# indicator", h.name],
      ["# id", h.id],
      ["# current", fmt(h.current, h)],
      ["# status", h.status],
      ['# thresholds', '"' + (h.threshold || "").replace(/"/g, "'") + '"'],
      ["# source", '"' + (h.source || "") + '"'],
    ];
    var lines = meta.map(function (r) { return r.join(","); });
    lines.push(head.join(","));
    h.points.forEach(function (p) { lines.push(p.label + "," + p.v); });
    var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = h.id + "_history.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  }

  function flip(card, on) {
    if (!card) return;
    if (on) {
      var back = card.querySelector(".mkt-back");
      if (back) renderChart(back);
    }
    card.classList.toggle("flipped", on);
  }

  document.addEventListener("click", function (e) {
    // Download button (don't flip)
    var dl = e.target.closest(".mkt-dl");
    if (dl) { e.preventDefault(); e.stopPropagation(); downloadCsv(dl.closest(".mkt-ind")); return; }

    // Front face → flip to history (links / buttons inside don't flip)
    var front = e.target.closest(".mkt-front.clickable");
    if (front) {
      if (e.target.closest("a") || e.target.closest("button")) return;
      flip(front.closest(".mkt-ind"), true);
      return;
    }

    // Back face → flip back
    var back = e.target.closest(".mkt-back");
    if (back) { flip(back.closest(".mkt-ind"), false); }
  });

  // Keyboard: Enter/Space toggles the focused face.
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " ") return;
    var front = e.target.closest && e.target.closest(".mkt-front.clickable");
    if (front) { e.preventDefault(); flip(front.closest(".mkt-ind"), true); return; }
    var back = e.target.closest && e.target.closest(".mkt-back");
    if (back && !e.target.closest(".mkt-dl")) { e.preventDefault(); flip(back.closest(".mkt-ind"), false); }
  });
})();
