# IRIS Design System — "Ledger"

Implemented from the **"IRIS Redesign v2"** Claude Design handoff (Ledger skin
only; the Quartz alternative was not adopted). An editorial, print-inspired
aesthetic: warm paper surfaces, serif display type, oxblood accent, hairline
rules instead of boxed cards. Light (paper) is the default theme; dark (warm
black) is a full variant via the header toggle.

## 1. Themes & atmosphere

- **Light (default):** flat warm paper `#faf9f6`, ink text `#16140f`,
  oxblood accent `#7d2230`. No shadows or gradients on the page — separation
  comes from hairline rules.
- **Dark:** warm black `#171510`, bone text `#f0ede4`, rose accent `#d98b96`
  (note: text **on** the accent flips to dark — use `--primary-ink`).
- Theme persists to `localStorage('theme')`; pre-paint script in
  `get_app_index_string()` applies it before first render. Default is light.
- Single fixed accent (no runtime accent picker); `config.py::COLOR_PALETTES`
  keeps `ledger` as the default entry.

## 2. Color tokens (`assets/style.css`)

| Role | Token | Light | Dark |
|---|---|---|---|
| Page / raised (menus) | `--bg-base` / `--bg-raised` | `#faf9f6` / `#fffefb` | `#171510` / `#201d16` |
| Surface / sunken | `--bg-surface/sunken` | `#f5f3ee` / `#f1efe8` | `#1d1a13` / `#121009` |
| Text | `--text-primary/secondary/muted` | `#16140f` / `#6b6557` / `#8d8775` | `#f0ede4` / `#9a937f` / bone 42% |
| Borders (4 tiers) | `--border-hair/subtle/default/strong` | ink 7/10/16/32% | bone 9/13/20/34% |
| Panel rules | `--rule-ink` | = `--text-primary` | = `--text-primary` |
| Accent ramp | `--primary-400..700` | `#96384a #7d2230 #6a1c29 #581723` | `#e3a3ac #d98b96 #c97783 #b86471` |
| Ink on accent | `--primary-ink` | `#ffffff` | `#171510` |
| Status | `--green/amber/red/blue-500` | `#1a5e45 #9a6b00 #a8232f #27506e` | `#7fc8a9 #d9b35c #e07a82 #8fb6d4` |
| Viz categorical | `SEGMENT_COLORS` (`utils/helpers.py`) | `#9d3a4a #b0673f #b08415 #2e8063 #41719a #8d8775 …` (mid-tones, read on both themes) | same |
| Waterfall | run-off `#b4434e` · changes `#4a7396` · new `#2e8063` | | |

Radii are tight (`--r-sm 2 / md 3 / lg 4 / xl 6`); shadows only on menus
(`--shadow-lg`).

## 3. Typography

- **Display / serif:** `Source Serif 4` (`--font-display`) — masthead, panel
  titles, KPI values, market composite scores, category heads.
- **Body:** `Instrument Sans` (`--font`) — UI labels, buttons, menus, tables.
- **Mono:** `IBM Plex Mono` (`--font-mono`) — numerals, axis labels, meta
  captions (uppercase, letterspaced).
- KPI labels: 10px uppercase `0.12em` tracking in body font (not mono).

## 4. Layout & shell

- **Masthead** (`components/layout.py::create_layout`):
  - Row 1: serif `IRIS` (26px) + "PORTFOLIO INTELLIGENCE" eyebrow, spacer,
    then controls — portfolio + time-window underline pills, ⌘K trigger,
    custom-metric (power-gated), theme ☾/☀, power bolt, contact, avatar.
    Pills are quiet underline buttons (`border-bottom` hairline → ink on hover).
  - **Double rule** (`.masthead-rule`): 2px over 1px ink — the Ledger signature.
  - Row 2: **☰ Index** dropdown (grouped page directory) + `Group / Page`
    breadcrumb (`#nav-breadcrumb`, updated instantly by `tab_switch_v2.js` and
    confirmed by `route_tabs`).
- **Index navigation**: tabs keep their `tab-{id}` button ids (all `route_tabs`
  wiring unchanged) but render as menu rows inside `.idx-menu`, grouped by
  `BaseTab.nav_group` — order: Home, Portfolio, Risk, Analysis, Tools
  (`NAV_GROUP_ORDER` in layout.py). Role-gated tabs stay `display:none`.
- **Panels**: `.card` = transparent section with a 1px ink top rule
  (`--rule-ink`) and serif 16px title — no boxes, no borders, no radius.
  `.drill-panel` opens with a 2px ink rule.
- **KPI strip**: hairline-divided columns (no boxes) — uppercase label, serif
  30px value, colored delta sub-line.
- **Segmented controls**: bordered strip, active = ink fill with paper text.
  Financial-trend metric chips (`.chip-radio`) are underline tabs.

## 5. Pages (Index directory)

| Group | Page | Notes |
|---|---|---|
| Home | **Overview** (`tabs/overview.py`) | Editorial landing: KPI figures, total-exposure line (2/3), Market-pulse digest (1/3, composite score + sparkline + top-5 severity indicators + "Full monitor →" jump), footer rule. |
| Portfolio | Portfolio Summary | Stacked bars + waterfall + drill-down + scrubber (unchanged functionality). |
| Portfolio | Financial Trend | Covenant chart + underline metric tabs + LOB table. |
| Risk | Market Insight | Ledger rollup strip (serif composite), serif category heads, flip cards: status-tinted front with 2px status top rule, back = raised surface with **status-colored** line chart + CSV download. |
| Analysis | role-gated tabs | Location / Projection / Backtesting. |
| Tools | Playground | Custom card builder. |

## 6. Popovers & dialogs

All anchored dropdowns (`.tw-wrap`/`.tw-menu`) inherit the raised menu surface
(`--bg-raised`, hairline border, 4px radius, `--shadow-lg`). The time-window
popover gains Ledger preset chips (3M/6M/1Y/2Y/ALL) that set the start/end
month dropdowns — Apply still commits, so behavior is unchanged. Center modals
(create-portfolio wizard, confirms) share the same chrome.

## 7. Charts

`utils/helpers.py::plotly_theme()` — transparent backgrounds, IBM Plex Mono,
text/grid colors overridden by CSS so they track the theme. Series colors come
from the Ledger `SEGMENT_COLORS` ramp (mid-tones chosen to read on paper and
warm black alike). Accent series use `#9d3a4a`.
