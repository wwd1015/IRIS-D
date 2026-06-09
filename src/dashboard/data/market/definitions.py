"""Static catalog of broad-market overheat / oversold indicators.

Each `IndicatorDefinition` ships with a `default_source` *name* and a
`default_source_url` so the user can click through and verify any
number the dashboard claims — same pattern as aibubble-cn's per-card
source annotations.

`research_prompt` is the load-bearing field for the LLM agent: it tells
the agent what number to look up and how to map the answer to
red / yellow / green. Keep the threshold mapping inside the prompt.

Adding a new indicator: append an `IndicatorDefinition` here, optionally
implement an `auto_collector` function in `automated_collectors.py`.
"""

from __future__ import annotations

from .models import IndicatorDefinition

CATALOG: list[IndicatorDefinition] = [
    # ── VALUATION ──────────────────────────────────────────────────
    IndicatorDefinition(
        id="shiller_cape",
        name="Shiller CAPE Ratio",
        name_zh="席勒市盈率 (CAPE)",
        category="valuation",
        threshold_text=">35 red / 25-35 yellow / <25 green",
        research_prompt=(
            "Find today's Shiller CAPE ratio for the S&P 500 (cyclically-adjusted "
            "P/E, 10-year smoothed earnings). Authoritative source is multpl.com/"
            "shiller-pe. Return the numeric value. Map: >35 → red, 25-35 → yellow, "
            "<25 → green."
        ),
        default_source="multpl.com",
        default_source_url="https://www.multpl.com/shiller-pe",
        refresh_cadence_hours=24 * 7,
        auto_collector="collect_shiller_cape",
    ),
    IndicatorDefinition(
        id="sp500_forward_pe",
        name="S&P 500 P/E (Trailing)",
        name_zh="标普500市盈率（滚动）",
        category="valuation",
        threshold_text=">25 red / 20-25 yellow / <20 green",
        research_prompt=(
            "Find today's S&P 500 trailing twelve-month P/E ratio. Authoritative "
            "free source is multpl.com/s-p-500-pe-ratio (forward P/E needs "
            "paywalled analyst estimates, so this indicator tracks trailing P/E). "
            "Read the current value. Map: >25 → red, 20-25 → yellow, <20 → green. "
            "Return the numeric value."
        ),
        default_source="multpl.com",
        default_source_url="https://www.multpl.com/s-p-500-pe-ratio",
        auto_collector="collect_sp500_pe",
    ),
    IndicatorDefinition(
        id="buffett_indicator",
        name="Buffett Indicator (Mkt Cap / GDP)",
        name_zh="巴菲特指标",
        category="valuation",
        threshold_text=">180% red / 130-180% yellow / <130% green",
        research_prompt=(
            "Find the current Wilshire 5000 / US GDP ratio (Buffett indicator). "
            "Sources: currentmarketvaluation.com, Longtermtrends, GuruFocus. "
            "Return as a percentage. Map: >180% → red, 130-180% → yellow, "
            "<130% → green."
        ),
        default_source="currentmarketvaluation.com",
        default_source_url="https://www.currentmarketvaluation.com/models/buffett-indicator.php",
        auto_collector="collect_buffett_indicator",
    ),
    # ── CAPITAL FLOWS ──────────────────────────────────────────────
    IndicatorDefinition(
        id="margin_debt_yoy",
        name="FINRA Margin Debt YoY",
        name_zh="融资余额同比",
        category="capital",
        threshold_text=">+40% red / +20-40% yellow / <+20% green",
        research_prompt=(
            "Open FINRA's monthly margin statistics page "
            "(finra.org/finra-data/browse-catalog/margin-statistics). "
            "Find the latest month's 'Debit Balances in Customers' Securities Margin "
            "Accounts' and compare to the same month one year prior. Compute the "
            "YoY % change. Map: >+40% → red, +20-40% → yellow, <+20% (including "
            "negative) → green. Return the YoY % change and the latest month."
        ),
        default_source="FINRA Margin Statistics",
        default_source_url="https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics",
        refresh_cadence_hours=24 * 30,
        auto_collector="collect_margin_debt_yoy",
    ),
    IndicatorDefinition(
        id="margin_leverage_ratio",
        name="Margin Debt / Free Credit Ratio",
        name_zh="融资余额/自由信贷比率",
        category="capital",
        threshold_text=">5.0x red / 3.0-5.0x yellow / <3.0x green",
        research_prompt=(
            "Open FINRA's monthly margin statistics page "
            "(finra.org/finra-data/browse-catalog/margin-statistics). "
            "Take the latest 'Debit Balances in Customers' Securities Margin Accounts' "
            "and divide by the sum of 'Free Credit Balances in Cash Accounts' + "
            "'Free Credit Balances in Securities Margin Accounts'. Map: >5.0x → red, "
            "3.0-5.0x → yellow, <3.0x → green. Return ratio plus the report month."
        ),
        default_source="FINRA Margin Statistics",
        default_source_url="https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics",
        refresh_cadence_hours=24 * 30,
        auto_collector="collect_margin_leverage_ratio",
    ),
    IndicatorDefinition(
        id="equity_fund_flows",
        name="US Equity Fund Flows (4-wk)",
        name_zh="美股基金资金流",
        category="capital",
        threshold_text=">+$30B/wk red / $10-30B/wk yellow / <$10B/wk green",
        research_prompt=(
            "Open ICI's free 'Weekly Estimated Long-Term Mutual Fund Flows' release "
            "(https://www.ici.org/research/stats/flows). Compute the 4-week average "
            "of net flows into 'Domestic Equity' funds (in $B/week). Map: 4-wk avg "
            ">$30B/wk → red, $10-30B → yellow, <$10B (including outflows) → green."
        ),
        default_source="ICI Weekly MF Flow Estimates",
        default_source_url="https://www.ici.org/research/stats/flows",
        refresh_cadence_hours=24 * 7,
        auto_collector="collect_equity_fund_flows",
    ),
    IndicatorDefinition(
        id="ipo_pipeline",
        name="IPO Pipeline State",
        name_zh="IPO 通道状态",
        category="capital",
        threshold_text="Flood = red / Active = yellow / Quiet = green",
        research_prompt=(
            "Open stockanalysis.com's free IPO list (https://stockanalysis.com/"
            "ipos/) and count how many IPOs priced in the trailing 30 days. "
            "Categorize: >20 IPOs/30d → 'Flood' → red (retail mania), 6-20 → "
            "'Active' → yellow (steady flow), <6 → 'Quiet' → green (risk-off "
            "primary market). Return the count and category."
        ),
        default_source="stockanalysis.com",
        default_source_url="https://stockanalysis.com/ipos/",
        auto_collector="collect_ipo_pipeline",
    ),
    # ── MARKET STRUCTURE ───────────────────────────────────────────
    IndicatorDefinition(
        id="pct_above_50dma",
        name="% S&P Above 50-day MA",
        name_zh="标普成分股在50日均线上方比例",
        category="market_structure",
        threshold_text="<30% red (oversold) / 30-75% green / >85% red (overbought)",
        research_prompt=(
            "Open StockCharts' free $SPXA50R quote page "
            "(https://stockcharts.com/h-sc/ui?s=$SPXA50R) — this is the "
            "authoritative free ticker for 'S&P 500 % Above 50-day MA'. Read the "
            "latest closing value. Map: <30% → red (oversold extreme), 30-75% → "
            "green (healthy participation), 75-85% → yellow, >85% → red "
            "(overbought extreme)."
        ),
        default_source="StockCharts $SPXA50R",
        default_source_url="https://stockcharts.com/h-sc/ui?s=$SPXA50R",
        auto_collector="collect_pct_above_50dma",
    ),
    IndicatorDefinition(
        id="spy_vs_rsp",
        name="SPY vs RSP 6M Spread",
        name_zh="SPY 与 RSP 6月差",
        category="market_structure",
        threshold_text=">+10% red / +5 to +10% yellow / <+5% green",
        research_prompt=(
            "Compute the 6-month total return spread between SPY (cap-weighted) "
            "and RSP (equal-weighted) S&P 500 ETFs. SPY return minus RSP return. "
            "A large positive spread means concentration in mega-caps. Map: "
            ">+10% → red, +5 to +10% → yellow, <+5% (incl. RSP-leading) → green."
        ),
        default_source="Yahoo Finance",
        default_source_url="https://finance.yahoo.com/compare/SPY-RSP",
        auto_collector="collect_spy_vs_rsp",
    ),
    IndicatorDefinition(
        id="vix_regime",
        name="VIX Regime",
        name_zh="VIX 状态",
        category="market_structure",
        threshold_text="<13 red (complacency) / 13-25 green / >30 red (stress)",
        research_prompt=(
            "Find the current CBOE VIX index level. Source: CBOE, Yahoo ^VIX. "
            "Map: <13 → red (complacency precedes corrections), 13-20 → green "
            "(normal), 20-25 → green/yellow (elevated), 25-30 → yellow, "
            ">30 → red (stress regime)."
        ),
        default_source="CBOE",
        default_source_url="https://www.cboe.com/tradable_products/vix/",
        refresh_cadence_hours=24,
        auto_collector="collect_vix_regime",
    ),
    IndicatorDefinition(
        id="vix_term_structure",
        name="VIX / VIX3M Term Structure",
        name_zh="VIX期限结构",
        category="market_structure",
        threshold_text=(
            "<0.85 red (complacent contango) / 0.85-1.0 green / >1.0 red (backwardation)"
        ),
        research_prompt=(
            "Compute the ratio VIX / VIX3M (3-month VIX). Source: CBOE, Yahoo "
            "^VIX and ^VIX3M. Deep contango (ratio <0.85) means the curve is "
            "complacently steep — investors are paying little for near-term "
            "protection. Backwardation (ratio >1.0) means stress now exceeds "
            "expected future stress. Map: <0.85 → red (complacency), "
            "0.85-0.95 → yellow, 0.95-1.0 → green, >1.0 → red (stress)."
        ),
        default_source="CBOE",
        default_source_url="https://www.cboe.com/tradable_products/vix/",
        refresh_cadence_hours=24,
        auto_collector="collect_vix_term_structure",
    ),
    IndicatorDefinition(
        id="zero_dte_share",
        name="0DTE Options Share of SPX Volume",
        name_zh="零日期权占比",
        category="market_structure",
        threshold_text=">55% red / 35-55% yellow / <35% green",
        research_prompt=(
            "Open Cboe's free '0DTE Options' insights hub "
            "(https://www.cboe.com/insights/posts/?topic=0dte). The most recent "
            "report quotes SPX 0DTE share of total SPX option volume as a "
            "percentage (often shown as a chart with a printed latest value). "
            "Read the latest figure. Map: >55% → red, 35-55% → yellow, <35% → "
            "green. Note the as-of date."
        ),
        default_source="Cboe 0DTE Insights",
        default_source_url="https://www.cboe.com/insights/posts/?topic=0dte",
    ),
    IndicatorDefinition(
        id="put_call_ratio",
        name="CBOE Equity Put/Call Ratio (21d MA)",
        name_zh="股票认沽认购比",
        category="market_structure",
        threshold_text="<0.55 red (complacency) / 0.55-0.85 green / >1.10 red (capitulation)",
        research_prompt=(
            "Open Cboe's free daily market statistics page "
            "(https://www.cboe.com/us/options/market_statistics/daily/). Take the "
            "Equity Put/Call Ratio for each of the last 21 trading days and "
            "average them (21d MA). Contrarian indicator: very low = complacency "
            "(red), normal = green, very high = capitulation (also red). "
            "Map: <0.55 → red, 0.55-0.85 → green, 0.85-1.10 → yellow, >1.10 → red."
        ),
        default_source="Cboe Daily Market Statistics",
        default_source_url="https://www.cboe.com/us/options/market_statistics/daily/",
        refresh_cadence_hours=24,
        auto_collector="collect_put_call_ratio",
    ),
    IndicatorDefinition(
        id="aaii_bull_bear",
        name="AAII Bull-Bear Spread",
        name_zh="AAII 多空差",
        category="market_structure",
        threshold_text=">+30pp red / +10 to +30pp yellow / <+10pp green",
        research_prompt=(
            "Open AAII's free 'Sentiment Survey Results' page "
            "(https://www.aaii.com/sentimentsurvey/sent_results). Read the latest "
            "week's Bullish % and Bearish % and compute the spread "
            "(bullish - bearish, in percentage points). Map: spread >+30pp → red "
            "(euphoria), +10 to +30pp → yellow, between -10 and +10pp → green, "
            "<-30pp → also red (capitulation). Note the survey end date."
        ),
        default_source="AAII Sentiment Survey",
        default_source_url="https://www.aaii.com/sentimentsurvey/sent_results",
        refresh_cadence_hours=24 * 7,
        auto_collector="collect_aaii_bull_bear",
    ),
    # ── CREDIT ─────────────────────────────────────────────────────
    IndicatorDefinition(
        id="hy_oas",
        name="High-Yield OAS Spread",
        name_zh="高收益债利差",
        category="credit",
        threshold_text=">500 bps red / 350-500 yellow / <350 green",
        research_prompt=(
            "Find the current ICE BofA US High Yield Index Option-Adjusted Spread "
            "in basis points. Source: FRED series BAMLH0A0HYM2. Map: >500 bps → "
            "red (stress), 350-500 → yellow (elevated), <350 → green (healthy)."
        ),
        default_source="FRED BAMLH0A0HYM2",
        default_source_url="https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
        refresh_cadence_hours=24,
        auto_collector="collect_hy_oas",
    ),
    IndicatorDefinition(
        id="ig_spread",
        name="Investment Grade OAS",
        name_zh="投资级债券利差",
        category="credit",
        threshold_text=">180 bps red / 120-180 yellow / <120 green",
        research_prompt=(
            "Find the current ICE BofA US Corporate Index Option-Adjusted Spread. "
            "Source: FRED series BAMLC0A0CM. Map: >180 bps → red, 120-180 → yellow, "
            "<120 → green."
        ),
        default_source="FRED BAMLC0A0CM",
        default_source_url="https://fred.stlouisfed.org/series/BAMLC0A0CM",
        auto_collector="collect_ig_spread",
    ),
    IndicatorDefinition(
        id="move_index",
        name="MOVE Index (Treasury Vol)",
        name_zh="MOVE 利率波动率",
        category="credit",
        threshold_text=">120 red / 80-120 yellow / <80 green",
        research_prompt=(
            "Find the current ICE BofA MOVE index level (the bond market's VIX, "
            "measuring Treasury option-implied vol). Sources: ICE, MarketWatch, "
            "Yahoo ^MOVE. Map: >120 → red (rate-vol stress), 80-120 → yellow, "
            "<80 → green."
        ),
        default_source="Yahoo ^MOVE",
        default_source_url="https://finance.yahoo.com/quote/%5EMOVE",
        refresh_cadence_hours=24,
        auto_collector="collect_move_index",
    ),
    IndicatorDefinition(
        id="bank_lending_standards",
        name="Bank Lending Standards (SLOOS)",
        name_zh="银行贷款标准",
        category="credit",
        threshold_text="Tightening >30% red / 0-30% yellow / Easing green",
        research_prompt=(
            "Find the latest Senior Loan Officer Opinion Survey (SLOOS) net "
            "percentage of banks tightening C&I lending standards (FRED series "
            "DRTSCILM, quarterly). Map: >+30% → red, 0 to +30% → yellow, "
            "easing (negative) → green."
        ),
        default_source="FRED DRTSCILM",
        default_source_url="https://fred.stlouisfed.org/series/DRTSCILM",
        refresh_cadence_hours=24 * 30,
        auto_collector="collect_bank_lending_standards",
    ),
    # ── FUNDAMENTALS ───────────────────────────────────────────────
    IndicatorDefinition(
        id="earnings_revision_breadth",
        name="Earnings Revision Breadth",
        name_zh="盈利预期修正广度",
        category="fundamentals",
        threshold_text="< -10% red / -10 to +10% yellow / > +10% green",
        research_prompt=(
            "Open Yardeni Research's free 'S&P 500 Earnings Revisions Index' page "
            "(https://yardeni.com/charts/sp-500-earnings-revisions/) — this is "
            "the canonical free chart of (upgrades − downgrades) / total. Read "
            "the latest weekly NERI / revision-breadth value (as a percent). "
            "Map: < -10% → red (heavy downgrades), -10 to +10% → yellow, "
            "> +10% → green."
        ),
        default_source="Yardeni Earnings Revisions",
        default_source_url="https://yardeni.com/charts/sp-500-earnings-revisions/",
    ),
    IndicatorDefinition(
        id="profit_margins",
        name="S&P 500 Net Margins",
        name_zh="标普500净利润率",
        category="fundamentals",
        threshold_text=">13% red (peak, mean-reversion risk) / 11-13% yellow / <11% green",
        research_prompt=(
            "Compute the S&P 500 trailing net profit margin as "
            "(Price/Sales ratio) ÷ (Price/Earnings ratio) — both shed their "
            "common price, leaving earnings/sales = net margin. Read both "
            "ratios from multpl.com (s-p-500-price-to-sales and s-p-500-pe-"
            "ratio). Map the resulting margin: >13% → red (historically high, "
            "mean-reversion risk), 11-13% → yellow, <11% → green."
        ),
        default_source="multpl.com (P/S ÷ P/E)",
        default_source_url="https://www.multpl.com/s-p-500-price-to-sales",
        auto_collector="collect_profit_margins",
    ),
    IndicatorDefinition(
        id="rev_vs_eps_growth",
        name="Revenue vs EPS Growth",
        name_zh="收入与EPS增长背离",
        category="fundamentals",
        threshold_text="EPS-Rev gap >5pp red / 2-5pp yellow / <2pp green",
        research_prompt=(
            "Open Yardeni's free 'S&P 500 Earnings & Revenues' PDF "
            "(https://yardeni.com/pub/peacockbillsales.pdf). Read the latest "
            "trailing 4-quarter YoY growth rates for both S&P 500 operating EPS "
            "and S&P 500 revenues. Compute EPS growth minus revenue growth in "
            "percentage points. Map: gap >5pp → red, 2-5pp → yellow, <2pp → green."
        ),
        default_source="Yardeni Earnings & Revenues (PDF)",
        default_source_url="https://yardeni.com/pub/peacockbillsales.pdf",
        auto_collector="collect_rev_vs_eps_growth",
    ),
    # ── MACRO ──────────────────────────────────────────────────────
    IndicatorDefinition(
        id="yield_curve_10_2",
        name="10Y-2Y Treasury Spread",
        name_zh="10年-2年期国债利差",
        category="macro",
        threshold_text="Inverted (<0) red / 0-50bps yellow / >50bps green",
        research_prompt=(
            "Find the current 10-year minus 2-year Treasury yield spread in "
            "basis points. Source: FRED series T10Y2Y. Map: <0 (inverted) → red, "
            "0 to +50bps → yellow, >+50bps → green. Note that uninversion after "
            "long inversion has historically preceded recessions."
        ),
        default_source="FRED T10Y2Y",
        default_source_url="https://fred.stlouisfed.org/series/T10Y2Y",
        refresh_cadence_hours=24,
        auto_collector="collect_yield_curve_10_2",
    ),
    IndicatorDefinition(
        id="fed_policy",
        name="Fed Policy Direction",
        name_zh="美联储政策方向",
        category="macro",
        threshold_text="Hiking red / Neutral yellow / Cutting green",
        research_prompt=(
            "Open the Fed's official FOMC calendar page "
            "(https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) "
            "and locate the most recent FOMC meeting press release. Read the "
            "policy action: rate hike, hold, or cut, and the forward guidance "
            "language. Categorize: hiking or signaling tightening → red, "
            "'hold / data-dependent' → yellow, cutting or signaling easing → "
            "green. Return a 1-sentence summary citing the meeting date."
        ),
        default_source="FRED DFEDTARU",
        default_source_url="https://fred.stlouisfed.org/series/DFEDTARU",
        refresh_cadence_hours=24 * 7,
        auto_collector="collect_fed_policy",
    ),
    IndicatorDefinition(
        id="dxy_trend",
        name="DXY 3-Month Trend",
        name_zh="美元指数3月趋势",
        category="macro",
        threshold_text=">+5% red (USD spike) / -5% to +5% green / <-5% yellow",
        research_prompt=(
            "Find the US Dollar Index (DXY) 3-month percent change. Source: "
            "Yahoo DX-Y.NYB, ICE. Map: >+5% → red (USD strength tightens global "
            "liquidity), -5% to +5% → green, <-5% → yellow (USD weakness signals "
            "risk-on but also dollar funding concerns)."
        ),
        default_source="ICE",
        default_source_url="https://finance.yahoo.com/quote/DX-Y.NYB",
        auto_collector="collect_dxy_trend",
    ),
]


def get_catalog() -> list[IndicatorDefinition]:
    """Return a fresh copy of the static indicator catalog."""
    return list(CATALOG)


def get_definition(indicator_id: str) -> IndicatorDefinition | None:
    for d in CATALOG:
        if d.id == indicator_id:
            return d
    return None
