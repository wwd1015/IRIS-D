/**
 * Playground tab — pure JS handlers for Add Column and Close buttons.
 */
(function () {
    var wiredElements = new WeakSet();

    // Expose updateGrid globally so Dash clientside callbacks can call it
    window.pgUpdateGrid = updateGrid;

    function updateGrid() {
        var grid = document.getElementById("pg-cards-grid");
        if (!grid) return;
        var visible = 0;
        for (var i = 0; i < 3; i++) {
            var card = document.getElementById("pg-card-" + i + "-wrapper");
            if (card && card.style.display !== "none") visible++;
        }
        grid.style.gridTemplateColumns = "repeat(" + visible + ", minmax(0, 1fr))";
        var btn = document.getElementById("pg-add-col");
        if (btn) {
            btn.disabled = visible >= 3;
            btn.classList.toggle("pg-add-col-btn--disabled", visible >= 3);
        }
        var saveBtn = document.getElementById("pg-save-portfolio");
        if (saveBtn) {
            saveBtn.disabled = visible < 2;
            saveBtn.classList.toggle("pg-save-btn--disabled", visible < 2);
        }
    }

    function wireButton(id, handler) {
        var el = document.getElementById(id);
        if (el && !wiredElements.has(el)) {
            wiredElements.add(el);
            el.addEventListener("click", function (e) {
                e.stopPropagation();
                e.preventDefault();
                handler();
            });
        }
    }

    function wireAll() {
        wireButton("pg-add-col", function () {
            for (var i = 0; i < 3; i++) {
                var card = document.getElementById("pg-card-" + i + "-wrapper");
                if (card && card.style.display === "none") {
                    card.style.display = "";
                    break;
                }
            }
            updateGrid();
        });

        for (var i = 0; i < 3; i++) {
            (function (idx) {
                wireButton("pg-card-" + idx + "-close", function () {
                    for (var j = idx; j < 3; j++) {
                        var c = document.getElementById("pg-card-" + j + "-wrapper");
                        if (c) c.style.display = "none";
                    }
                    updateGrid();
                });
            })(i);
        }
    }

    var wireTimer = null;
    var observer = new MutationObserver(function () {
        if (wireTimer) clearTimeout(wireTimer);
        wireTimer = setTimeout(wireAll, 100);
    });
    var grid = document.getElementById("pg-cards-grid");
    if (grid) {
        observer.observe(grid, { childList: true, subtree: true });
    } else {
        // Fallback: observe body until grid appears, then re-scope
        var bodyObs = new MutationObserver(function () {
            var g = document.getElementById("pg-cards-grid");
            if (g) {
                bodyObs.disconnect();
                observer.observe(g, { childList: true, subtree: true });
                wireAll();
            }
        });
        bodyObs.observe(document.body, { childList: true, subtree: true });
    }
    wireAll();
})();
