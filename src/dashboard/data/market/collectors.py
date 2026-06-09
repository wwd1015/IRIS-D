"""Automated collectors for indicators we can compute from free data sources.

Each collector returns a `RefreshResult` and is registered by name in
`COLLECTORS`. The service calls the appropriate collector when an
indicator definition's `auto_collector` field matches a key here.

Sources used:
  - FRED CSV endpoint (no key required): fredgraph.csv?id=<SERIES>
  - Yahoo Finance via httpx (used for SPY/RSP/^VIX/DX-Y.NYB EOD closes)
  - multpl.com HTML scrape (Shiller CAPE)

Failure semantics: collectors never raise. On any error they return
`RefreshResult(ok=False, error=…)` so the service can fall back to the
research agent or keep the prior reading.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta

import httpx

from .models import RefreshResult

log = logging.getLogger(__name__)

_FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart"
_TIMEOUT = 15.0


async def _http_get(url: str, params: dict[str, str] | None = None) -> str:
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": "kestrel/1.0"}) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.text


async def _http_get_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers={"User-Agent": "kestrel/1.0"}, follow_redirects=True
    ) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


async def _fred_latest(series_id: str) -> tuple[date, float] | None:
    """Return the (date, value) of the most recent non-missing FRED observation."""
    try:
        body = await _http_get(_FRED_CSV, params={"id": series_id})
    except Exception as e:  # noqa: BLE001
        log.warning("fred fetch %s failed: %s", series_id, e)
        return None
    reader = csv.reader(io.StringIO(body))
    header = next(reader, None)
    if not header or len(header) < 2:
        return None
    latest: tuple[date, float] | None = None
    for row in reader:
        if len(row) < 2:
            continue
        try:
            d = datetime.strptime(row[0], "%Y-%m-%d").date()
            v = float(row[1])
        except (ValueError, TypeError):
            continue
        if latest is None or d > latest[0]:
            latest = (d, v)
    return latest


async def _fred_series(series_id: str) -> list[tuple[date, float]]:
    """Return the full FRED series as (date, value) pairs, sorted oldest-first."""
    try:
        body = await _http_get(_FRED_CSV, params={"id": series_id})
    except Exception as e:  # noqa: BLE001
        log.warning("fred series fetch %s failed: %s", series_id, e)
        return []
    reader = csv.reader(io.StringIO(body))
    header = next(reader, None)
    if not header or len(header) < 2:
        return []
    out: list[tuple[date, float]] = []
    for row in reader:
        if len(row) < 2:
            continue
        try:
            d = datetime.strptime(row[0], "%Y-%m-%d").date()
            v = float(row[1])
        except (ValueError, TypeError):
            continue
        out.append((d, v))
    out.sort(key=lambda x: x[0])
    return out


async def _yahoo_closes(symbol: str, range_str: str = "1y") -> list[float]:
    """Return the daily close series for a Yahoo symbol."""
    try:
        body = await _http_get(
            f"{_YAHOO_CHART}/{symbol}",
            params={"range": range_str, "interval": "1d"},
        )
    except Exception as e:  # noqa: BLE001
        log.warning("yahoo fetch %s failed: %s", symbol, e)
        return []
    import json as _json

    try:
        data = _json.loads(body)
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        return [c for c in closes if c is not None]
    except (KeyError, IndexError, TypeError, ValueError):
        return []


# ── Individual collectors ───────────────────────────────────────────


async def collect_hy_oas() -> RefreshResult:
    latest = await _fred_latest("BAMLH0A0HYM2")
    if latest is None:
        return RefreshResult(indicator_id="hy_oas", ok=False, error="FRED fetch failed")
    d, v = latest
    # FRED quotes BAMLH0A0HYM2 in percent (e.g. 2.79 = 279bps).
    bps = v * 100.0
    if bps > 500:
        status = "red"
    elif bps >= 350:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="hy_oas",
        ok=True,
        status=status,
        value_display=f"{bps:.0f} bps",
        note=f"Latest FRED observation {d.isoformat()}.",
        source_used="FRED BAMLH0A0HYM2",
    )


async def collect_ig_spread() -> RefreshResult:
    latest = await _fred_latest("BAMLC0A0CM")
    if latest is None:
        return RefreshResult(indicator_id="ig_spread", ok=False, error="FRED fetch failed")
    d, v = latest
    bps = v * 100.0
    if bps > 180:
        status = "red"
    elif bps >= 120:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="ig_spread",
        ok=True,
        status=status,
        value_display=f"{bps:.0f} bps",
        note=f"Latest FRED observation {d.isoformat()}.",
        source_used="FRED BAMLC0A0CM",
    )


async def collect_yield_curve_10_2() -> RefreshResult:
    latest = await _fred_latest("T10Y2Y")
    if latest is None:
        return RefreshResult(indicator_id="yield_curve_10_2", ok=False, error="FRED fetch failed")
    d, v = latest
    bps = v * 100.0
    if bps < 0:
        status = "red"
        regime = "inverted"
    elif bps <= 50:
        status = "yellow"
        regime = "flat"
    else:
        status = "green"
        regime = "normal"
    return RefreshResult(
        indicator_id="yield_curve_10_2",
        ok=True,
        status=status,
        value_display=f"{bps:+.0f} bps ({regime})",
        note=f"Latest FRED observation {d.isoformat()}.",
        source_used="FRED T10Y2Y",
    )


async def collect_vix_regime() -> RefreshResult:
    closes = await _yahoo_closes("^VIX", range_str="1mo")
    if not closes:
        return RefreshResult(indicator_id="vix_regime", ok=False, error="Yahoo fetch failed")
    vix = closes[-1]
    if vix < 13:
        status = "red"
        label = "complacency"
    elif vix > 30:
        status = "red"
        label = "stress"
    elif vix > 25:
        status = "yellow"
        label = "elevated"
    elif vix > 20:
        status = "yellow"
        label = "normal-elevated"
    else:
        status = "green"
        label = "normal"
    return RefreshResult(
        indicator_id="vix_regime",
        ok=True,
        status=status,
        value_display=f"{vix:.1f} ({label})",
        note="Yahoo Finance ^VIX latest daily close.",
        source_used="Yahoo ^VIX",
    )


async def collect_spy_vs_rsp() -> RefreshResult:
    spy = await _yahoo_closes("SPY", range_str="1y")
    rsp = await _yahoo_closes("RSP", range_str="1y")
    if len(spy) < 130 or len(rsp) < 130:
        return RefreshResult(
            indicator_id="spy_vs_rsp",
            ok=False,
            error="Yahoo returned insufficient history for SPY/RSP",
        )
    # 6 months ≈ 126 trading days back.
    lookback = 126
    spy_ret = spy[-1] / spy[-lookback - 1] - 1.0
    rsp_ret = rsp[-1] / rsp[-lookback - 1] - 1.0
    spread = (spy_ret - rsp_ret) * 100.0
    if spread > 10:
        status = "red"
    elif spread > 5:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="spy_vs_rsp",
        ok=True,
        status=status,
        value_display=f"{spread:+.1f}%",
        note=(
            f"6m return: SPY {spy_ret * 100:+.1f}%, RSP {rsp_ret * 100:+.1f}%. "
            "Positive spread = cap-weighted leading equal-weight (concentration)."
        ),
        source_used="Yahoo Finance",
    )


async def collect_dxy_trend() -> RefreshResult:
    closes = await _yahoo_closes("DX-Y.NYB", range_str="6mo")
    if len(closes) < 63:
        return RefreshResult(
            indicator_id="dxy_trend",
            ok=False,
            error="Yahoo DXY history insufficient",
        )
    pct = (closes[-1] / closes[-63] - 1.0) * 100.0
    if pct > 5:
        status = "red"
        label = "USD spike (tighter global liquidity)"
    elif pct < -5:
        status = "yellow"
        label = "USD weakness"
    else:
        status = "green"
        label = "stable"
    return RefreshResult(
        indicator_id="dxy_trend",
        ok=True,
        status=status,
        value_display=f"{pct:+.1f}% ({label})",
        note=f"DXY 3-month change. Latest close {closes[-1]:.2f}.",
        source_used="ICE / Yahoo DX-Y.NYB",
    )


async def collect_move_index() -> RefreshResult:
    closes = await _yahoo_closes("^MOVE", range_str="1mo")
    if not closes:
        return RefreshResult(indicator_id="move_index", ok=False, error="Yahoo ^MOVE fetch failed")
    move = closes[-1]
    if move > 120:
        status = "red"
        label = "rate-vol stress"
    elif move >= 80:
        status = "yellow"
        label = "elevated"
    else:
        status = "green"
        label = "calm"
    return RefreshResult(
        indicator_id="move_index",
        ok=True,
        status=status,
        value_display=f"{move:.1f} ({label})",
        note="Yahoo Finance ^MOVE latest daily close.",
        source_used="Yahoo ^MOVE",
    )


async def collect_vix_term_structure() -> RefreshResult:
    vix = await _yahoo_closes("^VIX", range_str="1mo")
    vix3m = await _yahoo_closes("^VIX3M", range_str="1mo")
    if not vix or not vix3m:
        return RefreshResult(
            indicator_id="vix_term_structure",
            ok=False,
            error="Yahoo VIX/VIX3M fetch failed",
        )
    ratio = vix[-1] / vix3m[-1] if vix3m[-1] > 0 else 0.0
    if ratio > 1.0:
        status = "red"
        label = "backwardation / stress"
    elif ratio < 0.85:
        status = "red"
        label = "complacent contango"
    elif ratio < 0.95:
        status = "yellow"
        label = "steep contango"
    else:
        status = "green"
        label = "normal"
    return RefreshResult(
        indicator_id="vix_term_structure",
        ok=True,
        status=status,
        value_display=f"{ratio:.2f} ({label})",
        note=f"VIX {vix[-1]:.1f} / VIX3M {vix3m[-1]:.1f}.",
        source_used="Yahoo ^VIX, ^VIX3M",
    )


async def collect_bank_lending_standards() -> RefreshResult:
    # FRED DRTSCILM = net % of banks tightening standards on C&I loans to large/mid firms.
    latest = await _fred_latest("DRTSCILM")
    if latest is None:
        return RefreshResult(
            indicator_id="bank_lending_standards",
            ok=False,
            error="FRED DRTSCILM fetch failed",
        )
    d, v = latest  # already a percentage, e.g. 14.3 means +14.3% net tightening
    if v > 30:
        status = "red"
        label = "broad tightening"
    elif v >= 0:
        status = "yellow"
        label = "mild tightening"
    else:
        status = "green"
        label = "easing"
    return RefreshResult(
        indicator_id="bank_lending_standards",
        ok=True,
        status=status,
        value_display=f"{v:+.1f}% ({label})",
        note=f"FRED DRTSCILM (SLOOS, quarterly). Latest {d.isoformat()}.",
        source_used="FRED DRTSCILM",
    )


_SHILLER_PE_PATTERNS = (
    # multpl.com renders the current value in #current div followed by a number.
    re.compile(
        r'id=["\']current["\'][^>]*>\s*<[^>]+>\s*Current\s+Shiller'
        r"[^<]*</[^>]+>\s*([0-9]+\.[0-9]+)",
        re.IGNORECASE,
    ),
    re.compile(r"Current Shiller PE Ratio[^0-9]{0,200}?([0-9]+\.[0-9]+)", re.IGNORECASE),
    # Generic fallback: any "X.YY" near the words "Shiller" at top of page.
    re.compile(r"Shiller[^0-9<]{1,40}?([0-9]{2}\.[0-9]+)", re.IGNORECASE),
)


def _parse_shiller_cape(html: str) -> float | None:
    for pat in _SHILLER_PE_PATTERNS:
        m = pat.search(html)
        if m:
            try:
                return float(m.group(1))
            except (ValueError, IndexError):
                continue
    return None


async def collect_shiller_cape() -> RefreshResult:
    try:
        body = await _http_get("https://www.multpl.com/shiller-pe")
    except Exception as e:  # noqa: BLE001
        return RefreshResult(indicator_id="shiller_cape", ok=False, error=f"multpl.com fetch: {e}")
    value = _parse_shiller_cape(body)
    if value is None:
        return RefreshResult(
            indicator_id="shiller_cape",
            ok=False,
            error="Could not locate Shiller CAPE number in multpl.com response",
        )
    if value > 35:
        status = "red"
    elif value >= 25:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="shiller_cape",
        ok=True,
        status=status,
        value_display=f"{value:.1f}",
        note="multpl.com Shiller PE (10-year CAPE) latest reading.",
        source_used="multpl.com",
    )


# multpl publishes the current reading in the page's meta description,
# e.g. "Current S&P 500 PE Ratio is 31.99, a change of ...".
_MULTPL_CURRENT = re.compile(
    r"Current\s+S&(?:amp;)?P\s+500[^0-9]*?is\s+([0-9,]+\.?[0-9]*)",
    re.IGNORECASE,
)


async def _multpl_current_value(slug: str) -> float | None:
    """Fetch multpl.com/<slug> and return the 'Current ... is N' value."""
    try:
        body = await _http_get(f"https://www.multpl.com/{slug}")
    except Exception as e:  # noqa: BLE001
        log.warning("multpl fetch %s failed: %s", slug, e)
        return None
    m = _MULTPL_CURRENT.search(body)
    if m is None:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


async def collect_profit_margins() -> RefreshResult:
    """S&P 500 net margin = (Price/Sales) / (Price/Earnings).

    Both ratios share the same price, so PS/PE = (P/S)·(E/P) = E/S = net
    margin. multpl publishes both for free. Status is keyed to the
    absolute level — for an overheat monitor, a historically-high margin
    is itself a mean-reversion risk.
    """
    pe = await _multpl_current_value("s-p-500-pe-ratio")
    ps = await _multpl_current_value("s-p-500-price-to-sales")
    if pe is None or ps is None or pe <= 0:
        return RefreshResult(
            indicator_id="profit_margins",
            ok=False,
            error="Need S&P 500 P/E and P/S from multpl.com; one or both missing",
        )
    margin_pct = (ps / pe) * 100.0
    if margin_pct > 13.0:
        status = "red"
    elif margin_pct >= 11.0:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="profit_margins",
        ok=True,
        status=status,
        value_display=f"{margin_pct:.1f}%",
        note=(
            f"S&P 500 net margin = P/S {ps:.2f} ÷ P/E {pe:.2f}. "
            "Historically-high margins carry mean-reversion risk."
        ),
        source_used="multpl.com (P/S ÷ P/E)",
    )


async def collect_buffett_indicator() -> RefreshResult:
    """Wilshire 5000 (Yahoo ^W5000, points ≈ $B mkt cap) / GDP (FRED, $B).

    ^W5000 quotes a level where 1 point ≈ $1 billion of total US market cap
    (Wilshire's design). FRED GDP is in $ billions, annualized SAAR. So the
    ratio is dimensionless; multiply by 100 for percent.
    """
    closes = await _yahoo_closes("^W5000", range_str="1mo")
    gdp = await _fred_latest("GDP")
    if not closes or gdp is None:
        return RefreshResult(
            indicator_id="buffett_indicator",
            ok=False,
            error="Need ^W5000 (Yahoo) and GDP (FRED); one or both missing",
        )
    w5000 = closes[-1]
    _, gdp_value = gdp
    pct = (w5000 / gdp_value) * 100.0
    if pct > 180:
        status = "red"
    elif pct >= 130:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="buffett_indicator",
        ok=True,
        status=status,
        value_display=f"{pct:.0f}%",
        note=(
            f"Wilshire 5000 {w5000:,.0f} pts / GDP ${gdp_value:,.0f}B. "
            "1 W5000 pt ≈ $1B market cap (Wilshire indexing convention)."
        ),
        source_used="Yahoo ^W5000 + FRED GDP",
    )


# Mapping consumed by the service: definition.auto_collector → function.
# ── FINRA margin statistics ─────────────────────────────────────────
#
# FINRA publishes customer margin balances monthly (~3-4 week lag) as an
# Excel file with full history back to Jan 1997. One download feeds two
# indicators — margin debt YoY and the debt/free-credit leverage ratio —
# so we cache the parsed series module-side for 6h to avoid re-fetching.

_FINRA_MARGIN_XLSX = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"
_FINRA_CACHE: dict[str, object] = {}
_FINRA_TTL_SEC = 6 * 3600.0


async def _fetch_finra_margin() -> list[tuple[str, float, float, float]]:
    """Return FINRA margin rows newest-first: (year_month, debit, fc_cash, fc_margin).

    Values are in $millions. Raises on download/parse failure so the
    calling collector can surface RefreshResult(ok=False).
    """
    import time as _time

    cached = _FINRA_CACHE.get("rows")
    fetched_at = _FINRA_CACHE.get("at")
    if cached is not None and isinstance(fetched_at, float):
        if _time.monotonic() - fetched_at < _FINRA_TTL_SEC:
            return cached  # type: ignore[return-value]

    import openpyxl  # local import — only needed for this collector

    raw = await _http_get_bytes(_FINRA_MARGIN_XLSX)
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    rows: list[tuple[str, float, float, float]] = []
    for r in ws.iter_rows(values_only=True):
        if not r or r[0] is None:
            continue
        ym = str(r[0]).strip()
        # Skip the header row ("Year-Month").
        if not re.fullmatch(r"\d{4}-\d{2}", ym):
            continue
        try:
            debit = float(r[1]) if r[1] is not None else 0.0
            fc_cash = float(r[2]) if r[2] is not None else 0.0
            fc_margin = float(r[3]) if len(r) > 3 and r[3] is not None else 0.0
        except (TypeError, ValueError):
            continue
        rows.append((ym, debit, fc_cash, fc_margin))
    wb.close()
    # The file is newest-first already; sort defensively to be sure.
    rows.sort(key=lambda x: x[0], reverse=True)
    _FINRA_CACHE["rows"] = rows
    _FINRA_CACHE["at"] = _time.monotonic()
    return rows


async def collect_margin_debt_yoy() -> RefreshResult:
    try:
        rows = await _fetch_finra_margin()
    except Exception as e:  # noqa: BLE001
        log.warning("finra margin fetch failed: %s", e)
        return RefreshResult(
            indicator_id="margin_debt_yoy", ok=False, error=f"FINRA fetch failed: {e}"
        )
    if len(rows) < 13:
        return RefreshResult(
            indicator_id="margin_debt_yoy", ok=False, error="insufficient FINRA history"
        )
    latest_ym, latest_debit, _, _ = rows[0]
    year_ago_ym, year_ago_debit, _, _ = rows[12]
    if year_ago_debit <= 0:
        return RefreshResult(
            indicator_id="margin_debt_yoy", ok=False, error="bad year-ago FINRA value"
        )
    yoy = (latest_debit / year_ago_debit - 1.0) * 100.0
    if yoy > 40:
        status = "red"
    elif yoy >= 20:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="margin_debt_yoy",
        ok=True,
        status=status,
        value_display=f"{yoy:+.1f}%",
        note=(
            f"Debit balances ${latest_debit / 1000:,.1f}B ({latest_ym}) vs "
            f"${year_ago_debit / 1000:,.1f}B ({year_ago_ym})."
        ),
        source_used="FINRA Margin Statistics",
    )


async def collect_margin_leverage_ratio() -> RefreshResult:
    try:
        rows = await _fetch_finra_margin()
    except Exception as e:  # noqa: BLE001
        log.warning("finra margin fetch failed: %s", e)
        return RefreshResult(
            indicator_id="margin_leverage_ratio", ok=False, error=f"FINRA fetch failed: {e}"
        )
    if not rows:
        return RefreshResult(indicator_id="margin_leverage_ratio", ok=False, error="no FINRA rows")
    latest_ym, debit, fc_cash, fc_margin = rows[0]
    free_credit = fc_cash + fc_margin
    if free_credit <= 0:
        return RefreshResult(
            indicator_id="margin_leverage_ratio", ok=False, error="bad FINRA free-credit value"
        )
    ratio = debit / free_credit
    if ratio > 5.0:
        status = "red"
    elif ratio >= 3.0:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="margin_leverage_ratio",
        ok=True,
        status=status,
        value_display=f"{ratio:.2f}x",
        note=(
            f"Debit ${debit / 1000:,.1f}B / free credit ${free_credit / 1000:,.1f}B ({latest_ym})."
        ),
        source_used="FINRA Margin Statistics",
    )


# ── AAII investor sentiment survey ──────────────────────────────────
#
# AAII publishes the weekly sentiment survey (bullish / neutral / bearish).
# The historical .xls download is bot-blocked (403), but the results page
# itself serves the full HTML table when fetched with a browser UA. We
# scrape the most recent row. Bull-bear spread = bullish% − bearish%.

_AAII_RESULTS_URL = "https://www.aaii.com/sentimentsurvey/sent_results"
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


async def _fetch_aaii_latest() -> tuple[str, float, float, float] | None:
    """Return the latest AAII row: (reported_date, bullish%, neutral%, bearish%)."""
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers={"User-Agent": _BROWSER_UA}, follow_redirects=True
    ) as c:
        r = await c.get(_AAII_RESULTS_URL)
        r.raise_for_status()
        html = r.text

    # Data rows look like:
    #   <tr align="center" bgcolor="ffffff"> ... <td ... class="tableTxt">May 13</td>
    #   <td align="right" class="tableTxt">39.3%</td> ...(neutral)... ...(bearish)...
    row_match = re.search(
        r'<tr[^>]*bgcolor="ffffff"[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE
    )
    if row_match is None:
        return None
    row = row_match.group(1)
    date_match = re.search(r'<td[^>]*align="left"[^>]*>([^<]+)</td>', row, re.IGNORECASE)
    nums = re.findall(
        r'<td[^>]*align="right"[^>]*>\s*([0-9]+\.?[0-9]*)%?\s*</td>', row, re.IGNORECASE
    )
    if date_match is None or len(nums) < 3:
        return None
    reported = date_match.group(1).strip()
    bullish, neutral, bearish = (float(nums[0]), float(nums[1]), float(nums[2]))
    return reported, bullish, neutral, bearish


async def collect_aaii_bull_bear() -> RefreshResult:
    try:
        latest = await _fetch_aaii_latest()
    except Exception as e:  # noqa: BLE001
        log.warning("aaii fetch failed: %s", e)
        return RefreshResult(
            indicator_id="aaii_bull_bear", ok=False, error=f"AAII fetch failed: {e}"
        )
    if latest is None:
        return RefreshResult(
            indicator_id="aaii_bull_bear", ok=False, error="could not parse AAII results table"
        )
    reported, bullish, neutral, bearish = latest
    spread = bullish - bearish
    # Contrarian: both euphoric and capitulation extremes are red.
    if spread > 30 or spread < -30:
        status = "red"
    elif spread > 10 or spread < -10:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="aaii_bull_bear",
        ok=True,
        status=status,
        value_display=f"{spread:+.1f}pp",
        note=(
            f"Bullish {bullish:.1f}% − bearish {bearish:.1f}% "
            f"(neutral {neutral:.1f}%), week of {reported}."
        ),
        source_used="AAII Sentiment Survey",
    )


# ── Fed policy direction ────────────────────────────────────────────
#
# A meeting calendar gives dates, not direction. The Fed funds target
# range tells you directly whether policy has been tightening, holding,
# or easing. We compare the latest DFEDTARU (target range upper limit)
# against the value ~6 months prior.

_FED_LOOKBACK_DAYS = 183


async def collect_fed_policy() -> RefreshResult:
    series = await _fred_series("DFEDTARU")
    if len(series) < 2:
        return RefreshResult(
            indicator_id="fed_policy", ok=False, error="FRED DFEDTARU fetch failed"
        )
    latest_date, latest_rate = series[-1]
    # Find the observation closest to _FED_LOOKBACK_DAYS ago.
    cutoff = latest_date - timedelta(days=_FED_LOOKBACK_DAYS)
    prior = series[0]
    for d, v in series:
        if d <= cutoff:
            prior = (d, v)
        else:
            break
    prior_date, prior_rate = prior
    delta = latest_rate - prior_rate

    if delta > 0.01:
        status = "red"
        direction = "Hiking"
    elif delta < -0.01:
        status = "green"
        direction = "Cutting"
    else:
        status = "yellow"
        direction = "Hold / data-dependent"

    moves = f"{delta:+.2f}pp" if abs(delta) > 0.01 else "unchanged"
    return RefreshResult(
        indicator_id="fed_policy",
        ok=True,
        status=status,
        value_display=direction,
        note=(
            f"Fed funds target upper {latest_rate:.2f}% ({latest_date.isoformat()}); "
            f"{moves} vs {prior_rate:.2f}% ~6 months prior ({prior_date.isoformat()})."
        ),
        source_used="FRED DFEDTARU",
    )


# ── S&P 500 trailing P/E (multpl) ───────────────────────────────────
#
# Forward P/E needs paywalled analyst estimates. We retarget the
# indicator to TRAILING P/E, which multpl publishes free.


async def collect_sp500_pe() -> RefreshResult:
    pe = await _multpl_current_value("s-p-500-pe-ratio")
    if pe is None:
        return RefreshResult(
            indicator_id="sp500_forward_pe",
            ok=False,
            error="Could not read S&P 500 P/E from multpl.com",
        )
    if pe > 25:
        status = "red"
    elif pe >= 20:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="sp500_forward_pe",
        ok=True,
        status=status,
        value_display=f"{pe:.2f}",
        note="S&P 500 trailing twelve-month P/E (multpl.com).",
        source_used="multpl.com",
    )


# ── Revenue vs EPS growth (multpl by-year tables) ───────────────────
#
# multpl publishes by-year history tables for S&P 500 earnings (TTM EPS)
# and sales (TTM sales per share). Each table is newest-first with rows
# of (date, value). We compute YoY growth for both and take the gap.

_MULTPL_TABLE_ROW = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>\s*([A-Za-z]{3}\s+\d{1,2},\s*\d{4})\s*</td>\s*"
    r"<td[^>]*>(.*?)</td>",
    re.DOTALL | re.IGNORECASE,
)


async def _multpl_table(slug: str) -> list[tuple[date, float]]:
    """Fetch multpl.com/<slug>/table/by-year, parse rows newest-first.

    Returns [(date, value), ...]. `$` and `,` are stripped from values.
    """
    try:
        body = await _http_get(f"https://www.multpl.com/{slug}/table/by-year")
    except Exception as e:  # noqa: BLE001
        log.warning("multpl table fetch %s failed: %s", slug, e)
        return []
    out: list[tuple[date, float]] = []
    for m in _MULTPL_TABLE_ROW.finditer(body):
        date_str = m.group(1).strip()
        raw_val = re.sub(r"<[^>]+>", "", m.group(2))
        # multpl pads values with HTML entities (e.g. &#x2002; EN SPACE).
        # Strip all entities first so a stray "2002" from "&#x2002;"
        # cannot be mistaken for the cell value.
        raw_val = re.sub(r"&#?\w+;", " ", raw_val)
        raw_val = raw_val.replace("$", "").replace(",", "").strip()
        num = re.search(r"-?[0-9]+\.?[0-9]*", raw_val)
        if num is None:
            continue
        try:
            d = datetime.strptime(date_str, "%b %d, %Y").date()
            v = float(num.group(0))
        except (ValueError, TypeError):
            continue
        out.append((d, v))
    return out


def _value_one_year_prior(rows: list[tuple[date, float]]) -> tuple[date, float] | None:
    """Given rows newest-first, return the row ~12 months before the latest."""
    if not rows:
        return None
    latest_date = rows[0][0]
    target = latest_date - timedelta(days=365)
    best: tuple[date, float] | None = None
    best_gap = None
    for d, v in rows[1:]:
        gap = abs((d - target).days)
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best = (d, v)
    # Reject if the nearest row is more than ~6 months off target.
    if best is None or best_gap is None or best_gap > 200:
        return None
    return best


async def collect_rev_vs_eps_growth() -> RefreshResult:
    eps_rows = await _multpl_table("s-p-500-earnings")
    sales_rows = await _multpl_table("s-p-500-sales")
    if len(eps_rows) < 2 or len(sales_rows) < 2:
        return RefreshResult(
            indicator_id="rev_vs_eps_growth",
            ok=False,
            error="Could not parse multpl earnings/sales by-year tables",
        )
    eps_now = eps_rows[0]
    sales_now = sales_rows[0]
    eps_prior = _value_one_year_prior(eps_rows)
    sales_prior = _value_one_year_prior(sales_rows)
    if eps_prior is None or sales_prior is None:
        return RefreshResult(
            indicator_id="rev_vs_eps_growth",
            ok=False,
            error="Could not locate a ~1-year-prior row in multpl tables",
        )
    if eps_prior[1] <= 0 or sales_prior[1] <= 0:
        return RefreshResult(
            indicator_id="rev_vs_eps_growth",
            ok=False,
            error="Non-positive prior-year EPS/sales value",
        )
    eps_growth = eps_now[1] / eps_prior[1] - 1.0
    sales_growth = sales_now[1] / sales_prior[1] - 1.0
    gap = (eps_growth - sales_growth) * 100.0
    if gap > 5:
        status = "red"
    elif gap >= 2:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="rev_vs_eps_growth",
        ok=True,
        status=status,
        value_display=f"{gap:+.1f}pp",
        note=(
            f"TTM EPS growth {eps_growth * 100:+.1f}% vs sales/share growth "
            f"{sales_growth * 100:+.1f}% ({eps_prior[0].isoformat()} → "
            f"{eps_now[0].isoformat()}). A wide gap means growth is driven by "
            "margin expansion / buybacks, not revenue."
        ),
        source_used="multpl.com (earnings ÷ sales by-year)",
    )


# ── % of S&P 500 above 50-day MA (computed from a sample) ───────────
#
# No free single-number breadth source survives. We compute it from a
# representative ~80-ticker sample spanning all 11 GICS sectors.

_SP500_BREADTH_SAMPLE: tuple[str, ...] = (
    # Technology
    "AAPL",
    "MSFT",
    "NVDA",
    "AVGO",
    "ORCL",
    "CRM",
    "AMD",
    # Communication Services
    "GOOGL",
    "META",
    "NFLX",
    "DIS",
    "TMUS",
    "CMCSA",
    "VZ",
    # Consumer Discretionary
    "AMZN",
    "TSLA",
    "HD",
    "MCD",
    "NKE",
    "LOW",
    "SBUX",
    # Consumer Staples
    "WMT",
    "PG",
    "KO",
    "PEP",
    "COST",
    "PM",
    "MDLZ",
    # Financials
    "BRK-B",
    "JPM",
    "V",
    "MA",
    "BAC",
    "WFC",
    "GS",
    # Healthcare
    "UNH",
    "JNJ",
    "LLY",
    "ABBV",
    "MRK",
    "PFE",
    "TMO",
    # Industrials
    "CAT",
    "HON",
    "UPS",
    "BA",
    "GE",
    "RTX",
    "LMT",
    # Energy
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "EOG",
    "MPC",
    "PSX",
    # Utilities
    "NEE",
    "DUK",
    "SO",
    "D",
    "AEP",
    "EXC",
    "SRE",
    # Materials
    "LIN",
    "SHW",
    "APD",
    "ECL",
    "FCX",
    "NEM",
    "DOW",
    # Real Estate
    "PLD",
    "AMT",
    "EQIX",
    "CCI",
    "PSA",
    "O",
    "SPG",
)
_BREADTH_MIN_NAMES = 40


async def collect_pct_above_50dma() -> RefreshResult:
    import asyncio as _aio

    # Fetch the sample concurrently (bounded) — sequential 77 Yahoo calls
    # would dominate a full market refresh.
    sem = _aio.Semaphore(12)

    async def _one(ticker: str) -> bool | None:
        async with sem:
            closes = await _yahoo_closes(ticker, range_str="6mo")
        if len(closes) < 50:
            return None
        ma50 = sum(closes[-50:]) / 50.0
        return closes[-1] > ma50

    flags = await _aio.gather(*[_one(t) for t in _SP500_BREADTH_SAMPLE])
    evaluated = sum(1 for f in flags if f is not None)
    above = sum(1 for f in flags if f is True)
    if evaluated < _BREADTH_MIN_NAMES:
        return RefreshResult(
            indicator_id="pct_above_50dma",
            ok=False,
            error=f"Only {evaluated} of {len(_SP500_BREADTH_SAMPLE)} sample names returned data",
        )
    pct = above / evaluated * 100.0
    if pct < 30:
        status = "red"
        label = "oversold"
    elif pct <= 75:
        status = "green"
        label = "healthy participation"
    elif pct <= 85:
        status = "yellow"
        label = "extended"
    else:
        status = "red"
        label = "overbought"
    return RefreshResult(
        indicator_id="pct_above_50dma",
        ok=True,
        status=status,
        value_display=f"{pct:.0f}% ({label})",
        note=(
            f"{above} of {evaluated} sampled S&P 500 names (11-sector sample) "
            "trading above their 50-day simple moving average."
        ),
        source_used="Yahoo Finance (computed breadth sample)",
    )


# ── CBOE equity put/call ratio (daily stats scrape) ─────────────────
#
# The daily market statistics page embeds put/call ratios in a JSON
# blob. We pull the equity put/call ratio, falling back to total.

_CBOE_DAILY_URL = "https://www.cboe.com/us/options/market_statistics/daily/"
_CBOE_PC_ENTRY = re.compile(
    r'name\\?"\s*:\s*\\?"([A-Z + ]*PUT/CALL RATIO)\\?"\s*,\s*'
    r'\\?"value\\?"\s*:\s*\\?"([0-9]+\.?[0-9]*)\\?"',
    re.IGNORECASE,
)


async def _fetch_cboe_put_call() -> tuple[float, str] | None:
    """Return (ratio, which) where which is 'equity' or 'total'."""
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers={"User-Agent": _BROWSER_UA}, follow_redirects=True
    ) as c:
        r = await c.get(_CBOE_DAILY_URL)
        r.raise_for_status()
        html = r.text
    ratios: dict[str, float] = {}
    for m in _CBOE_PC_ENTRY.finditer(html):
        name = m.group(1).strip().upper()
        try:
            val = float(m.group(2))
        except ValueError:
            continue
        ratios[name] = val
    if "EQUITY PUT/CALL RATIO" in ratios:
        return ratios["EQUITY PUT/CALL RATIO"], "equity"
    if "TOTAL PUT/CALL RATIO" in ratios:
        return ratios["TOTAL PUT/CALL RATIO"], "total"
    return None


async def collect_put_call_ratio() -> RefreshResult:
    try:
        result = await _fetch_cboe_put_call()
    except Exception as e:  # noqa: BLE001
        log.warning("cboe put/call fetch failed: %s", e)
        return RefreshResult(
            indicator_id="put_call_ratio", ok=False, error=f"CBOE fetch failed: {e}"
        )
    if result is None:
        return RefreshResult(
            indicator_id="put_call_ratio",
            ok=False,
            error="Could not locate a put/call ratio in CBOE daily stats",
        )
    ratio, which = result
    if ratio < 0.55:
        status = "red"
        label = "complacency"
    elif ratio <= 0.85:
        status = "green"
        label = "normal"
    elif ratio <= 1.10:
        status = "yellow"
        label = "fear building"
    else:
        status = "red"
        label = "capitulation"
    src_label = "equity" if which == "equity" else "total (equity unavailable)"
    return RefreshResult(
        indicator_id="put_call_ratio",
        ok=True,
        status=status,
        value_display=f"{ratio:.2f} ({label})",
        note=f"CBOE {src_label} put/call ratio, latest daily reading.",
        source_used="CBOE Daily Market Statistics",
    )


# ── IPO pipeline (stockanalysis.com) ────────────────────────────────
#
# stockanalysis.com/ipos embeds IPO entries with priced dates as a JS
# object literal: {s:"TICKER",n:"Name",ipoDate:"YYYY-MM-DD",...}.

_STOCKANALYSIS_IPO_URL = "https://stockanalysis.com/ipos/"
_IPO_DATE = re.compile(r'ipoDate:\s*"(\d{4}-\d{2}-\d{2})"')


async def _fetch_ipo_dates() -> list[date]:
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers={"User-Agent": _BROWSER_UA}, follow_redirects=True
    ) as c:
        r = await c.get(_STOCKANALYSIS_IPO_URL)
        r.raise_for_status()
        html = r.text
    out: list[date] = []
    for m in _IPO_DATE.finditer(html):
        try:
            out.append(datetime.strptime(m.group(1), "%Y-%m-%d").date())
        except ValueError:
            continue
    return out


async def collect_ipo_pipeline() -> RefreshResult:
    try:
        dates = await _fetch_ipo_dates()
    except Exception as e:  # noqa: BLE001
        log.warning("stockanalysis ipo fetch failed: %s", e)
        return RefreshResult(
            indicator_id="ipo_pipeline", ok=False, error=f"stockanalysis.com fetch failed: {e}"
        )
    if not dates:
        return RefreshResult(
            indicator_id="ipo_pipeline",
            ok=False,
            error="Could not parse any IPO dates from stockanalysis.com",
        )
    # Anchor "today" to the most recent priced date on the page.
    anchor = max(dates)
    cutoff = anchor - timedelta(days=30)
    count = sum(1 for d in dates if cutoff <= d <= anchor)
    if count > 20:
        status = "red"
        label = "Flood"
    elif count >= 6:
        status = "yellow"
        label = "Active"
    else:
        status = "green"
        label = "Quiet"
    return RefreshResult(
        indicator_id="ipo_pipeline",
        ok=True,
        status=status,
        value_display=f"{label} ({count} IPOs/30d)",
        note=(
            f"{count} IPOs priced in the 30 days through {anchor.isoformat()}. "
            "Flood = retail-mania risk; Quiet = risk-off primary market."
        ),
        source_used="stockanalysis.com IPO list",
    )


# ── ICI weekly equity fund flows ────────────────────────────────────
#
# ICI publishes weekly long-term mutual fund flow estimates as a legacy
# BIFF .xls. Column "Total equity" (index 3) is net new cash flow in
# $millions. The file has a monthly section then an "Estimated Weekly
# Net New Cash Flow" section; we average the last 4 weekly rows.
#
# Caveat baked into the note: this is *mutual fund* flow only — it
# excludes ETFs (now the dominant vehicle), so the series runs
# structurally negative regardless of investor risk appetite.

_ICI_FLOWS_URL = "https://www.ici.org/flows_data_{year}.xls"


async def _fetch_ici_weekly_equity_flows() -> list[tuple[str, float]]:
    """Return ICI weekly equity MF flows oldest-first: (date_str, $millions)."""
    from datetime import date as _date

    year = _date.today().year
    raw: bytes | None = None
    for y in (year, year - 1):
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT, headers={"User-Agent": _BROWSER_UA}, follow_redirects=True
            ) as c:
                r = await c.get(_ICI_FLOWS_URL.format(year=y))
                r.raise_for_status()
                raw = r.content
            break
        except Exception:  # noqa: BLE001
            continue
    if raw is None:
        raise RuntimeError("ICI flows .xls unavailable")

    import xlrd  # local import — only this collector needs it

    wb = xlrd.open_workbook(file_contents=raw)
    sh = wb.sheet_by_index(0)
    weekly_start: int | None = None
    for i in range(sh.nrows):
        cell = str(sh.cell_value(i, 0)).strip().lower()
        if "weekly" in cell and "cash flow" in cell:
            weekly_start = i + 1
            break
    if weekly_start is None:
        raise RuntimeError("could not locate weekly section in ICI file")
    rows: list[tuple[str, float]] = []
    for i in range(weekly_start, sh.nrows):
        date_cell = str(sh.cell_value(i, 0)).strip()
        equity = sh.cell_value(i, 3)
        if not date_cell or not isinstance(equity, int | float):
            continue
        rows.append((date_cell, float(equity)))
    return rows


async def collect_equity_fund_flows() -> RefreshResult:
    try:
        rows = await _fetch_ici_weekly_equity_flows()
    except Exception as e:  # noqa: BLE001
        log.warning("ici flows fetch failed: %s", e)
        return RefreshResult(
            indicator_id="equity_fund_flows", ok=False, error=f"ICI fetch failed: {e}"
        )
    if len(rows) < 4:
        return RefreshResult(
            indicator_id="equity_fund_flows", ok=False, error="insufficient ICI weekly history"
        )
    last4 = rows[-4:]
    avg_billions = (sum(v for _, v in last4) / 4.0) / 1000.0
    if avg_billions > 30:
        status = "red"
    elif avg_billions >= 10:
        status = "yellow"
    else:
        status = "green"
    return RefreshResult(
        indicator_id="equity_fund_flows",
        ok=True,
        status=status,
        value_display=f"{avg_billions:+.1f}B/wk",
        note=(
            f"ICI 4-week avg equity flow through {last4[-1][0]}. Long-term "
            "MUTUAL FUND flows only — excludes ETFs (the dominant vehicle "
            "today), so this series runs structurally negative."
        ),
        source_used="ICI Weekly MF Flow Estimates",
    )


COLLECTORS: dict[str, Callable[[], Awaitable[RefreshResult]]] = {
    "collect_hy_oas": collect_hy_oas,
    "collect_ig_spread": collect_ig_spread,
    "collect_yield_curve_10_2": collect_yield_curve_10_2,
    "collect_vix_regime": collect_vix_regime,
    "collect_spy_vs_rsp": collect_spy_vs_rsp,
    "collect_dxy_trend": collect_dxy_trend,
    "collect_move_index": collect_move_index,
    "collect_vix_term_structure": collect_vix_term_structure,
    "collect_bank_lending_standards": collect_bank_lending_standards,
    "collect_shiller_cape": collect_shiller_cape,
    "collect_buffett_indicator": collect_buffett_indicator,
    "collect_margin_debt_yoy": collect_margin_debt_yoy,
    "collect_margin_leverage_ratio": collect_margin_leverage_ratio,
    "collect_aaii_bull_bear": collect_aaii_bull_bear,
    "collect_fed_policy": collect_fed_policy,
    "collect_profit_margins": collect_profit_margins,
    "collect_sp500_pe": collect_sp500_pe,
    "collect_rev_vs_eps_growth": collect_rev_vs_eps_growth,
    "collect_pct_above_50dma": collect_pct_above_50dma,
    "collect_put_call_ratio": collect_put_call_ratio,
    "collect_ipo_pipeline": collect_ipo_pipeline,
    "collect_equity_fund_flows": collect_equity_fund_flows,
}


def is_auto(indicator_id: str) -> bool:
    """Convenience for the service / UI: does this indicator have a collector?"""
    # Late binding: catalog isn't imported here to avoid cycles. The service
    # is the source of truth for auto-vs-research routing.
    from .definitions import get_definition

    d = get_definition(indicator_id)
    return bool(d and d.auto_collector and d.auto_collector in COLLECTORS)


# A small helper used in tests + the service when a fresh fetch fails: returns
# how old `last_updated` is in hours.
def hours_since(ts: datetime) -> float:
    return (datetime.now(UTC) - ts).total_seconds() / 3600.0


# `timedelta` is intentionally re-exported so tests can monkey-patch.
__all__ = [
    "COLLECTORS",
    "collect_aaii_bull_bear",
    "collect_bank_lending_standards",
    "collect_buffett_indicator",
    "collect_equity_fund_flows",
    "collect_dxy_trend",
    "collect_fed_policy",
    "collect_hy_oas",
    "collect_ig_spread",
    "collect_margin_debt_yoy",
    "collect_margin_leverage_ratio",
    "collect_move_index",
    "collect_pct_above_50dma",
    "collect_profit_margins",
    "collect_put_call_ratio",
    "collect_rev_vs_eps_growth",
    "collect_shiller_cape",
    "collect_sp500_pe",
    "collect_spy_vs_rsp",
    "collect_vix_regime",
    "collect_vix_term_structure",
    "collect_yield_curve_10_2",
    "hours_since",
    "is_auto",
    "timedelta",
]
