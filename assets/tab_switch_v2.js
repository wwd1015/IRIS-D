/**
 * Instant loading overlay for IRIS-D.
 *
 * Two mechanisms:
 *   1. Tab clicks (mousedown): instant highlight + show overlay
 *   2. Fetch interceptor: shows overlay when Dash sends a callback
 *      that targets tab-content-container, hides when response arrives
 */
(function () {
    var ACTIVE = "navtab active";
    var INACTIVE = "navtab";
    var MIN_SHOW_MS = 300;
    var SAFETY_MS = 12000;   // hard backstop — never spin longer than this
    var loadingStartedAt = 0;
    var hideTimer = null;
    var safetyTimer = null;

    function showOverlay() {
        var wrapper = document.getElementById("tab-content-wrapper");
        if (!wrapper || wrapper.classList.contains("is-loading")) return;
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        wrapper.classList.add("is-loading");
        loadingStartedAt = Date.now();
        // Safety backstop: if no hide signal arrives (failed/aborted fetch,
        // missed detection), force the overlay off so content is never trapped.
        if (safetyTimer) clearTimeout(safetyTimer);
        safetyTimer = setTimeout(hideOverlay, SAFETY_MS);
    }

    function hideOverlay() {
        var w = document.getElementById("tab-content-wrapper");
        if (w) w.classList.remove("is-loading");
        if (safetyTimer) { clearTimeout(safetyTimer); safetyTimer = null; }
    }

    function scheduleHide() {
        var elapsed = Date.now() - loadingStartedAt;
        var remaining = Math.max(0, MIN_SHOW_MS - elapsed);
        if (hideTimer) clearTimeout(hideTimer);
        hideTimer = setTimeout(hideOverlay, remaining);
    }

    // Primary hide signal: the moment tab-content-container actually re-renders,
    // drop the overlay. This is independent of fetch success/failure, so a
    // rejected or aborted request can never strand the spinner.
    function observeContent() {
        var c = document.getElementById("tab-content-container");
        if (!c) { setTimeout(observeContent, 200); return; }
        new MutationObserver(function () {
            var w = document.getElementById("tab-content-wrapper");
            if (w && w.classList.contains("is-loading")) scheduleHide();
        }).observe(c, { childList: true, subtree: false });
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", observeContent);
    } else {
        observeContent();
    }

    // --- 0. Index menu (Ledger nav): open/close ---
    function setIndexMenu(open) {
        var pop = document.getElementById("index-menu-pop");
        if (pop) pop.style.display = open ? "block" : "none";
    }
    document.addEventListener("click", function (e) {
        if (e.target.closest && e.target.closest("#index-menu-btn")) {
            var pop = document.getElementById("index-menu-pop");
            setIndexMenu(pop && pop.style.display === "none");
            return;
        }
        if (e.target.closest && e.target.closest("#index-menu-backdrop")) {
            setIndexMenu(false);
        }
        // In-page links that jump to a tab (e.g. Overview "Full monitor →")
        var jump = e.target.closest && e.target.closest("[data-target-tab]");
        if (jump) {
            var t = document.getElementById(jump.getAttribute("data-target-tab"));
            if (t) t.click();
        }
    }, true);

    // --- 1. Tab clicks: instant highlight + breadcrumb + overlay ---
    document.addEventListener("mousedown", function (e) {
        var btn = e.target;
        while (btn && btn !== document) {
            if (btn.tagName === "BUTTON" && btn.id && btn.id.indexOf("tab-") === 0) break;
            btn = btn.parentElement;
        }
        if (!btn || btn === document) return;

        var allTabs = document.querySelectorAll('button[id^="tab-"]');
        for (var i = 0; i < allTabs.length; i++) {
            allTabs[i].className = INACTIVE;
            allTabs[i].setAttribute("aria-selected", "false");
        }
        btn.className = ACTIVE;
        btn.setAttribute("aria-selected", "true");

        // Instant breadcrumb (server confirms via route_tabs)
        var g = document.getElementById("crumb-group");
        var l = document.getElementById("crumb-label");
        if (g && btn.getAttribute("data-group")) g.textContent = btn.getAttribute("data-group");
        if (l) {
            var lbl = btn.querySelector("span");
            if (lbl) l.textContent = lbl.textContent;
        }
        // NOTE: do NOT close the Index menu here — these tab buttons live inside
        // the menu, and hiding it on mousedown would remove the button before the
        // browser dispatches `click`, so Dash's onClick (→ route_tabs) never fires.
        // The menu is closed in a bubble-phase click listener below instead.
        showOverlay();
    }, true);

    // Close the Index menu AFTER the click has been delivered to the tab button
    // (bubble phase runs after Dash's React onClick), so navigation still fires.
    document.addEventListener("click", function (e) {
        var btn = e.target;
        while (btn && btn !== document) {
            if (btn.tagName === "BUTTON" && btn.id && btn.id.indexOf("tab-") === 0) break;
            btn = btn.parentElement;
        }
        if (btn && btn !== document) setIndexMenu(false);
    }, false);

    // --- 2. Fetch interceptor: catch all Dash callback requests ---
    var originalFetch = window.fetch;
    window.fetch = function () {
        var url = arguments[0];
        var opts = arguments[1];

        // Check if this is a Dash callback request
        if (typeof url === "string" && url.indexOf("_dash-update-component") !== -1) {
            // Check if it targets tab-content-container
            try {
                var body = opts && opts.body ? JSON.parse(opts.body) : {};
                var output = body.output || "";
                if (output.indexOf("tab-content-container") !== -1) {
                    showOverlay();
                }
            } catch (e) {}
        }

        // Track whether this request targets tab-content-container
        var isContentRequest = false;
        if (typeof url === "string" && url.indexOf("_dash-update-component") !== -1) {
            try {
                var reqBody = opts && opts.body ? JSON.parse(opts.body) : {};
                var reqOutput = reqBody.output || "";
                if (reqOutput.indexOf("tab-content-container") !== -1) {
                    isContentRequest = true;
                }
            } catch (e) {}
        }

        return originalFetch.apply(this, arguments).then(function (response) {
            // Only clone for content updates (avoid cloning large non-content responses)
            if (isContentRequest) {
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        scheduleHide();
                    });
                });
            }
            return response;
        }, function (err) {
            // Fetch rejected (network error / aborted by a fast re-navigation):
            // hide the overlay so content is never trapped, then re-throw.
            if (isContentRequest) hideOverlay();
            throw err;
        });
    };
})();
