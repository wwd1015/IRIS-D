/**
 * Portfolio Intelligence Copilot — client-side behaviour for IRIS-D.
 *
 * The copilot markup (#copilot-root → rail + panel) is rendered once in the
 * app shell; this script drives it. The backend is a PLACEHOLDER: answers are
 * deterministic, keyword-matched, and reference the portfolio / tab currently
 * in view. Open/collapse state and the suggested prompts track the active tab.
 *
 *   - #copilot-rail            → expand into the panel
 *   - #copilot-collapse-btn    → collapse back to the rail
 *   - #copilot-suggestions     → context-aware prompt pills (per tab)
 *   - ask() → user bubble + thinking dots, then a canned answer
 *   - answer action buttons    → click the matching nav tab (tab-<id>)
 */
(function () {
  // Suggested prompts per context key.
  var SUGGEST = {
    overview: [
      "Summarize today's portfolio risk posture",
      "What changed most since last month?",
      "Which segments are driving exposure growth?",
    ],
    trend: [
      "Explain the period-over-period waterfall",
      "Where is run-off concentrated?",
      "Which segment grew fastest this window?",
    ],
    financial: [
      "Any covenant breaches I should review?",
      "How is leverage trending vs the threshold?",
      "Summarize DSCR coverage quality",
    ],
    market: [
      "What's driving the composite risk score?",
      "Which indicators flipped red recently?",
      "How stretched are valuations right now?",
    ],
  };

  // Map a tab id → suggestion context key.
  function ctxKey(tabId) {
    tabId = tabId || "";
    if (tabId.indexOf("market") !== -1) return "market";
    if (tabId.indexOf("financial") !== -1) return "financial";
    if (tabId.indexOf("trend") !== -1 || tabId.indexOf("summary") !== -1) return "trend";
    return "overview";
  }

  function activeTab() {
    var b = document.querySelector(".navtab.active");
    if (b && b.id && b.id.indexOf("tab-") === 0) return b.id.slice(4);
    return "overview";
  }
  function activeTabLabel() {
    var c = document.getElementById("crumb-label");
    return c ? c.textContent.trim() : "Overview";
  }
  function portfolioName() {
    var el = document.getElementById("portfolio-selector-btn");
    if (!el) return "your portfolio";
    var txt = el.textContent.replace(/[▾●]/g, "").trim();
    return txt || "your portfolio";
  }

  // ── DOM builders (mirror the seeded greeting markup) ──────────────────────
  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  }
  function userMsg(text) {
    var wrap = el("div", "copilot-msg user");
    wrap.appendChild(el("div", "copilot-bubble", text));
    return wrap;
  }
  function aiHead() {
    var h = el("div", "copilot-msg-head");
    h.appendChild(el("span", "copilot-badge sm", "IQ"));
    h.appendChild(el("span", "copilot-msg-role", "Copilot"));
    return h;
  }
  function thinkingMsg() {
    var wrap = el("div", "copilot-msg ai");
    wrap.appendChild(aiHead());
    var dots = el("div", "copilot-dots");
    for (var i = 0; i < 3; i++) {
      var d = el("span");
      d.style.animationDelay = (i * 0.18) + "s";
      dots.appendChild(d);
    }
    wrap.appendChild(dots);
    return wrap;
  }
  function answerMsg(ans) {
    var wrap = el("div", "copilot-msg ai");
    wrap.appendChild(aiHead());
    var body = el("div", "copilot-msg-body");
    body.appendChild(el("div", "copilot-msg-text", ans.text));
    if (ans.cites && ans.cites.length) {
      var c = el("div", "copilot-cites");
      ans.cites.forEach(function (t) {
        var row = el("div", "copilot-cite");
        row.appendChild(el("span", "copilot-cite-dot", "·"));
        row.appendChild(el("span", null, t));
        c.appendChild(row);
      });
      body.appendChild(c);
    }
    if (ans.action) {
      var btn = el("button", "copilot-action", ans.action.label + " →");
      btn.addEventListener("click", function () {
        var t = document.getElementById("tab-" + ans.action.tab);
        if (t) t.click();
      });
      body.appendChild(btn);
    }
    wrap.appendChild(body);
    return wrap;
  }

  // ── Answer builder (placeholder, deterministic) ───────────────────────────
  function A(text, cites, action) { return { text: text, cites: cites || [], action: action || null }; }
  function answer(q) {
    var lower = q.toLowerCase();
    var pf = portfolioName();
    var win = "the current window";

    if (/composite|risk score|driving the/.test(lower))
      return A("The composite market-risk score is in an elevated regime — a weighted blend of the live indicators, with stretched valuation and leverage signals the largest contributors.",
        ["Composite risk · elevated", "Top driver · valuations"], { label: "Open Market monitor", tab: "market-insight" });
    if (/\bred\b|flipped|indicator/.test(lower))
      return A("Several market indicators are currently red. The most material for portfolio risk are the valuation and credit-spread signals.",
        ["Valuation · red", "Credit spreads · red", "Liquidity · amber"], { label: "Open Market monitor", tab: "market-insight" });
    if (/valuation|stretched/.test(lower))
      return A("Valuations look historically stretched — broad equity multiples sit well above long-run norms, leaving little buffer if earnings disappoint.",
        ["Shiller CAPE · elevated", "Buffett indicator · elevated"], { label: "Open Market monitor", tab: "market-insight" });
    if (/covenant|breach/.test(lower))
      return A("No covenant breaches flagged for " + pf + " in " + win + " — headline credit metrics are within their thresholds. (Placeholder — wire to live covenant checks.)",
        ["Leverage · within limit", "DSCR · within floor"], { label: "Open Financial", tab: "financial-trend" });
    if (/leverage/.test(lower))
      return A("Leverage for " + pf + " is trending broadly flat against its covenant ceiling over " + win + ". (Placeholder figure — connect the financial dataset for live values.)",
        ["Leverage · stable", "Covenant · within limit"], { label: "Open Financial", tab: "financial-trend" });
    if (/dscr|coverage/.test(lower))
      return A("DSCR coverage for " + pf + " looks comfortable against its floor over " + win + ". (Placeholder — grounded figures pending backend.)",
        ["DSCR · comfortable"], { label: "Open Financial", tab: "financial-trend" });
    if (/waterfall|run-?off|concentrat/.test(lower))
      return A("Over " + win + ", the period-over-period bridge nets run-off against repricing / changes and new originations. Run-off is heaviest in maturing CRE facilities.",
        ["Bridge · run-off vs new", "Run-off · maturing CRE"], { label: "Open Trend", tab: "portfolio-trend" });
    if (/fastest|growth|growing|driving exposure|segment/.test(lower))
      return A("Segment growth in " + pf + " is led by the larger industry concentrations this window, while the overall book is broadly stable. (Placeholder — exact figures pending backend.)",
        ["Top segment · growing", "Total book · stable"], { label: "Open Trend", tab: "portfolio-trend" });
    if (/changed|since last|posture|summar|today/.test(lower))
      return A("Snapshot for " + pf + ": exposure broadly stable over " + win + ", the market regime is elevated, and a handful of facilities sit on the watchlist. (Placeholder summary — connect the copilot backend for live numbers.)",
        ["Exposure · stable", "Market regime · elevated", "Watchlist · active"], { label: "Open Overview", tab: "overview" });
    return A("Here's the current read on " + pf + ": exposure broadly stable over " + win + ", market regime elevated, a few facilities on watch. Ask about valuations, covenants, run-off, or a specific segment. (Placeholder backend.)",
      [], null);
  }

  // ── Plumbing ──────────────────────────────────────────────────────────────
  function root() { return document.getElementById("copilot-root"); }
  function messages() { return document.getElementById("copilot-messages"); }
  function scrollBottom() { var m = messages(); if (m) m.scrollTop = m.scrollHeight; }
  function enabled() { var r = root(); return r && r.style.display !== "none"; }

  // Content reflows when the panel docks/undocks; nudge Plotly (and anything
  // else bound to window resize) to refit after the CSS transition settles.
  function reflow() {
    setTimeout(function () { window.dispatchEvent(new Event("resize")); }, 260);
  }

  function openPanel() {
    var r = root(); if (!r) return;
    r.classList.add("copilot-open");
    localStorage.setItem("copilot_open", "true");
    renderSuggestions();
    setTimeout(function () { var i = document.getElementById("copilot-input"); if (i) i.focus(); }, 40);
    scrollBottom();
    reflow();
  }
  function collapsePanel() {
    var r = root(); if (!r) return;
    r.classList.remove("copilot-open");
    localStorage.setItem("copilot_open", "false");
    reflow();
  }

  var busy = false;
  function ask(q) {
    q = (q || "").trim();
    if (!q || busy) return;
    var m = messages(); if (!m) return;
    var inp = document.getElementById("copilot-input");
    if (inp) inp.value = "";
    m.appendChild(userMsg(q));
    var think = thinkingMsg();
    m.appendChild(think);
    scrollBottom();
    busy = true;
    setTimeout(function () {
      if (think.parentNode === m) m.removeChild(think);
      m.appendChild(answerMsg(answer(q)));
      scrollBottom();
      busy = false;
    }, 650);
  }

  function renderSuggestions() {
    var box = document.getElementById("copilot-suggestions");
    if (box) {
      var list = SUGGEST[ctxKey(activeTab())] || SUGGEST.overview;
      box.innerHTML = "";
      list.forEach(function (s) {
        var b = el("button", "copilot-sugg-pill", s);
        b.addEventListener("click", function () { ask(s); });
        box.appendChild(b);
      });
    }
    var sub = document.getElementById("copilot-subtitle");
    if (sub) sub.textContent = activeTabLabel();
  }

  // ── Events ──────────────────────────────────────────────────────────────
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    if (t.closest("#copilot-rail")) { e.preventDefault(); openPanel(); return; }
    if (t.closest("#copilot-collapse-btn")) { e.preventDefault(); collapsePanel(); return; }
    if (t.closest("#copilot-send")) {
      e.preventDefault();
      var i = document.getElementById("copilot-input");
      ask(i ? i.value : "");
      return;
    }
    // Re-sync suggestions shortly after any tab switch (nav, palette, action btn).
    if (t.closest(".navtab")) { setTimeout(renderSuggestions, 90); }
  });

  document.addEventListener("keydown", function (e) {
    if (e.target && e.target.id === "copilot-input" && e.key === "Enter") {
      e.preventDefault();
      ask(e.target.value);
    }
  });

  function init() {
    renderSuggestions();
    // Restore the open state, but only if the feature is enabled.
    if (enabled() && localStorage.getItem("copilot_open") === "true") {
      var r = root();
      if (r) r.classList.add("copilot-open");
    }
    // Keep the subtitle / prompts in sync if the breadcrumb mutates in place.
    var crumb = document.getElementById("crumb-label");
    if (crumb) {
      new MutationObserver(renderSuggestions)
        .observe(crumb, { childList: true, characterData: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { setTimeout(init, 300); });
  } else {
    setTimeout(init, 300);
  }
})();
