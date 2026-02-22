/**
 * Instant loading overlay for IRIS-D.
 *
 * Two mechanisms:
 *   1. Tab clicks (mousedown): instant highlight + show overlay
 *   2. Fetch interceptor: shows overlay when Dash sends a callback
 *      that targets tab-content-container, hides when response arrives
 */
(function () {
    var ACTIVE = "px-3 py-1.5 rounded bg-ink-900 text-white";
    var INACTIVE = "px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700";
    var MIN_SHOW_MS = 300;
    var loadingStartedAt = 0;
    var hideTimer = null;

    function showOverlay() {
        var wrapper = document.getElementById("tab-content-wrapper");
        if (!wrapper || wrapper.classList.contains("is-loading")) return;
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        wrapper.classList.add("is-loading");
        loadingStartedAt = Date.now();
    }

    function hideOverlay() {
        var w = document.getElementById("tab-content-wrapper");
        if (w) w.classList.remove("is-loading");
    }

    function scheduleHide() {
        var elapsed = Date.now() - loadingStartedAt;
        var remaining = Math.max(0, MIN_SHOW_MS - elapsed);
        if (hideTimer) clearTimeout(hideTimer);
        hideTimer = setTimeout(hideOverlay, remaining);
    }

    // --- 1. Tab clicks: instant highlight + overlay ---
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
        }
        btn.className = ACTIVE;
        showOverlay();
    }, true);

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

        return originalFetch.apply(this, arguments).then(function (response) {
            // Check if this response is for a content update
            if (typeof url === "string" && url.indexOf("_dash-update-component") !== -1) {
                // Clone to read body without consuming it
                var clone = response.clone();
                clone.text().then(function (text) {
                    if (text.indexOf("tab-content-container") !== -1) {
                        // Content response arrived — schedule hide
                        // Use requestAnimationFrame to wait for React to paint
                        requestAnimationFrame(function () {
                            requestAnimationFrame(function () {
                                scheduleHide();
                            });
                        });
                    }
                });
            }
            return response;
        });
    };
})();
