"""Per-indicator history series for the Market Insight flip charts.

Each indicator card flips to reveal a time-series of that metric's full history,
shaded by its red/yellow/green threshold bands.  Live collectors only return a
*current* value, so — exactly as in the Claude Design prototype — the history is
a deterministic, seeded, mean-reverting series that lands on the current value.
Same id + config → identical series every render (no random churn).

The numeric anchors, drift volatility, seeds, and threshold bands are ported
verbatim from the design's ``MKT_HIST_CFG``.
"""

from __future__ import annotations

from datetime import date

# Number of monthly points in each history series.
N_POINTS = 24

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Per-indicator config: numeric anchor (current `n`), display prefix/suffix,
# drift volatility, RNG seed, and colored threshold bands ({max, status}
# ascending; max=None means +infinity). A few direction-based indicators
# (profit_margins, fed_policy) omit bands.
HIST_CFG: dict[str, dict] = {
    "shiller_cape":           {"n": 42.7,  "suf": "",     "vol": 1.4,  "seed": 11, "bands": [{"max": 25, "status": "green"}, {"max": 35, "status": "yellow"}, {"max": None, "status": "red"}]},
    "sp500_forward_pe":       {"n": 32.69, "suf": "",     "vol": 1.2,  "seed": 12, "bands": [{"max": 18, "status": "green"}, {"max": 22, "status": "yellow"}, {"max": None, "status": "red"}]},
    "buffett_indicator":      {"n": 237,   "suf": "%",    "vol": 8,    "seed": 13, "bands": [{"max": 130, "status": "green"}, {"max": 180, "status": "yellow"}, {"max": None, "status": "red"}]},
    "margin_debt_yoy":        {"n": 53.3,  "suf": "%", "pre": "+", "vol": 5, "seed": 14, "bands": [{"max": 20, "status": "green"}, {"max": 40, "status": "yellow"}, {"max": None, "status": "red"}]},
    "margin_leverage_ratio":  {"n": 3.01,  "suf": "x",    "vol": 0.18, "seed": 15, "bands": [{"max": 3, "status": "green"}, {"max": 5, "status": "yellow"}, {"max": None, "status": "red"}]},
    "equity_fund_flows":      {"n": -27,   "suf": "B",    "vol": 9,    "seed": 16, "bands": [{"max": 10, "status": "green"}, {"max": 30, "status": "yellow"}, {"max": None, "status": "red"}]},
    "ipo_pipeline":           {"n": 39,    "suf": "/30d", "vol": 6,    "seed": 17, "bands": [{"max": 15, "status": "green"}, {"max": 30, "status": "yellow"}, {"max": None, "status": "red"}]},
    "pct_above_50dma":        {"n": 52,    "suf": "%",    "vol": 9,    "seed": 18, "bands": [{"max": 30, "status": "red"}, {"max": 75, "status": "green"}, {"max": 85, "status": "yellow"}, {"max": None, "status": "red"}]},
    "spy_vs_rsp":             {"n": 0.1,   "suf": "%", "pre": "+", "vol": 2.2, "seed": 19, "bands": [{"max": 5, "status": "green"}, {"max": 10, "status": "yellow"}, {"max": None, "status": "red"}]},
    "vix_regime":             {"n": 15.4,  "suf": "",     "vol": 2.4,  "seed": 20, "bands": [{"max": 13, "status": "red"}, {"max": 25, "status": "green"}, {"max": 30, "status": "yellow"}, {"max": None, "status": "red"}]},
    "vix_term_structure":     {"n": 0.80,  "suf": "",     "vol": 0.05, "seed": 21, "bands": [{"max": 0.85, "status": "red"}, {"max": 1.0, "status": "green"}, {"max": None, "status": "red"}]},
    "zero_dte_share":         {"n": 63,    "suf": "%",    "vol": 3.5,  "seed": 22, "bands": [{"max": 35, "status": "green"}, {"max": 55, "status": "yellow"}, {"max": None, "status": "red"}]},
    "put_call_ratio":         {"n": 0.49,  "suf": "",     "vol": 0.06, "seed": 23, "bands": [{"max": 0.55, "status": "red"}, {"max": 0.85, "status": "green"}, {"max": 1.10, "status": "yellow"}, {"max": None, "status": "red"}]},
    "aaii_bull_bear":         {"n": -0.7,  "suf": "pp",   "vol": 7,    "seed": 24, "bands": [{"max": 10, "status": "green"}, {"max": 30, "status": "yellow"}, {"max": None, "status": "red"}]},
    "hy_oas":                 {"n": 275,   "suf": "bps",  "vol": 22,   "seed": 25, "bands": [{"max": 350, "status": "green"}, {"max": 500, "status": "yellow"}, {"max": None, "status": "red"}]},
    "ig_spread":              {"n": 74,    "suf": "bps",  "vol": 7,    "seed": 26, "bands": [{"max": 120, "status": "green"}, {"max": 180, "status": "yellow"}, {"max": None, "status": "red"}]},
    "move_index":             {"n": 71.2,  "suf": "",     "vol": 8,    "seed": 27, "bands": [{"max": 80, "status": "green"}, {"max": 120, "status": "yellow"}, {"max": None, "status": "red"}]},
    "bank_lending_standards": {"n": 8.1,   "suf": "%", "pre": "+", "vol": 6, "seed": 28, "bands": [{"max": 0, "status": "green"}, {"max": 30, "status": "yellow"}, {"max": None, "status": "red"}]},
    "earnings_revision_breadth": {"n": 2.0, "suf": "%", "pre": "+", "vol": 4, "seed": 29, "bands": [{"max": -10, "status": "red"}, {"max": 10, "status": "yellow"}, {"max": None, "status": "green"}]},
    "profit_margins":         {"n": 11.5,  "suf": "%",    "vol": 0.5,  "seed": 30},
    "rev_vs_eps_growth":      {"n": 4.6,   "suf": "pp", "pre": "+", "vol": 1.3, "seed": 31, "bands": [{"max": 2, "status": "green"}, {"max": 5, "status": "yellow"}, {"max": None, "status": "red"}]},
    "yield_curve_10_2":       {"n": 42,    "suf": "bps", "pre": "+", "vol": 14, "seed": 32, "bands": [{"max": 0, "status": "red"}, {"max": 50, "status": "yellow"}, {"max": None, "status": "green"}]},
    "fed_policy":             {"n": 3.75,  "suf": "%",    "vol": 0.18, "seed": 33},
    "dxy_trend":              {"n": 0.4,   "suf": "%", "pre": "+", "vol": 2.6, "seed": 34, "bands": [{"max": -5, "status": "yellow"}, {"max": 5, "status": "green"}, {"max": None, "status": "red"}]},
}


def _mulberry32(seed: int):
    """Port of the design's mulberry32 PRNG (32-bit, deterministic)."""
    a = seed & 0xFFFFFFFF

    def rng() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = (t ^ (t >> 15)) & 0xFFFFFFFF
        t = (t * (1 | a)) & 0xFFFFFFFF
        u = (t ^ (t >> 7)) & 0xFFFFFFFF
        u = (u * (61 | t)) & 0xFFFFFFFF
        t = (((t + u) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return rng


def _gen_series(end: float, vol: float, seed: int, n: int = N_POINTS) -> list[float]:
    """Seeded mean-reverting series with gentle drift, landing exactly on `end`."""
    rng = _mulberry32((seed * 2654435761) & 0xFFFFFFFF)
    drift = rng() * 2 - 1
    start = end - drift * vol * 5
    out: list[float] = []
    noise = 0.0
    for i in range(n):
        base = start + (end - start) * (i / (n - 1))
        noise = noise * 0.55 + (rng() - 0.5) * vol * 1.5
        out.append(round(base + noise, 4))
    out[n - 1] = end
    return out


def _period_labels(n: int, end: date) -> list[str]:
    """`n` monthly labels (e.g. "Jun '26") ending at `end`'s month."""
    seq: list[tuple[int, int]] = []
    yy, mm = end.year, end.month
    for _ in range(n):
        seq.append((yy, mm))
        mm -= 1
        if mm == 0:
            mm = 12
            yy -= 1
    seq.reverse()
    return [f"{_MONTHS[m - 1]} '{str(y)[2:]}" for (y, m) in seq]


def build_hist(indicator_id: str, end: date | None = None) -> dict | None:
    """Return the history payload for an indicator, or None if it has no config.

    Shape: ``{points: [{x, label, v}], current, prefix, suffix, bands}``.
    """
    cfg = HIST_CFG.get(indicator_id)
    if not cfg:
        return None
    end = end or date.today()
    series = _gen_series(cfg["n"], cfg["vol"], cfg["seed"])
    labels = _period_labels(N_POINTS, end)
    points = [{"x": i, "label": labels[i], "v": series[i]} for i in range(N_POINTS)]
    return {
        "points": points,
        "current": cfg["n"],
        "prefix": cfg.get("pre", ""),
        "suffix": cfg.get("suf", ""),
        "bands": cfg.get("bands"),
    }


def format_value(v: float, prefix: str = "", suffix: str = "") -> str:
    """Match the design's mktFmt: 0/1/2 decimals by magnitude."""
    a = abs(v)
    dp = 0 if a >= 100 else 1 if a >= 10 else 2
    return f"{prefix}{v:.{dp}f}{suffix}"
