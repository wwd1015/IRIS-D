# IRIS-D Design System

Implemented from the **"IRIS-D Redesign"** Claude Design handoff. A data-dense,
warm-blue dashboard aesthetic with IBM Plex typography, mono numerals, and
border-disciplined surfaces. Both light and dark themes are first-class.

> The previous "warm editorial / terracotta" direction is retained only as a
> selectable accent (`terracotta`, `sage`) via the runtime accent picker.

## 1. Themes & atmosphere

- **Default accent:** warm blue `#4B6BFB` (`--primary-500`). The brand mark, nav
  underline, KPI accent bars, drill panels, chart highlights, and pills all key
  off the primary ramp + its derived `--primary-tint` / `--primary-border`.
- **Light:** near-white surfaces (`--bg-base #ffffff` on `--bg-deep #f7f7f3`),
  cool-neutral text (`#1a1c24` → `#8a92a3`).
- **Dark:** deep slate surfaces (`--bg-base #111217` on `#0b0c10`) with a faint
  radial primary glow on the body; text in white at 94/62/40% opacity.
- **Accents (swappable):** warmBlue (default), emerald, amber, rose, violet,
  slate, terracotta, sage. Defined in `src/dashboard/config.py::COLOR_PALETTES`;
  cycled by the header sliders icon (persists to `localStorage`).

## 2. Color tokens (`assets/style.css`)

| Role | Token | Light | Dark |
|---|---|---|---|
| Page / base / raised | `--bg-deep/base/raised` | `#f7f7f3` / `#ffffff` | `#0b0c10` / `#111217` / `#16181f` |
| Surface / sunken | `--bg-surface/sunken` | `#fafaf6` / `#f1f1ec` | `#1a1c24` / `#0a0b0f` |
| Text | `--text-primary/secondary/muted` | `#1a1c24` / `#5a6271` / `#8a92a3` | white 94% / 62% / 40% |
| Borders (4 tiers) | `--border-hair/subtle/default/strong` | black 5/7/12/22% | white 4/7/11/20% |
| Primary ramp | `--primary-400..700` | `#6B8AFF #4B6BFB #3B5BDB #2B4BC7` | — |
| Status | `--green/amber/red/blue-500` | `#16a34a #d97706 #dc2626 #2563eb` | `#22c55e #f59e0b #ef4444 #3b82f6` |
| Viz categorical | `SEGMENT_COLORS` (`utils/helpers.py`) | `#6B8AFF #A78BFA #34D399 #F59E0B #FB7185 #60A5FA …` | same |
| Waterfall | run-off `#F87171` · changes `#60A5FA` · new `#34D399` | | |

Accent swaps also set `--primary-glow-rgb`, `--primary-tint` (8%), and
`--primary-border` (28%) so tints/borders track the chosen accent.

## 3. Typography

- **Sans / display:** `IBM Plex Sans` (`--font-sans`, `--font-display`). Loaded
  in `get_app_index_string()`; mirrored in the Tailwind `fontFamily`.
- **Mono:** `IBM Plex Mono` (`--font-mono`) — used for **all numeric/tabular
  figures**: KPI values, table cells, axis labels, badges, pills, chips.
- **Scale:** `--fs-3xs 10` · `2xs 11` · `xs 12` · `sm 13` · `base 14` · `lg 16` ·
  `xl 20` · `2xl 28` · `3xl 38` (px).
- Headings use tight letter-spacing (`-0.02em`); labels use mono uppercase with
  `0.1em` tracking.

## 4. Layout & shell

- **Header (two rows)** — `components/layout.py::create_layout`:
  - Row 1 (`.header-row-1`): brand mark + `IRIS-D v2.4`, portfolio pill, time
    pill, ⌘K search (`.cmd-hint`), spacer, role chip, bell, theme/accent/power/
    contact icon-buttons, avatar.
  - Row 2 (`.header-row-2`): numbered nav tabs (`.navtab` + `.tab-badge`), active
    tab underlined in primary.
- **Content** lives in `.main-scroll` (padding `24px 32px`).
- **Sections** (`.section` / `.section-head` / `.section-title`) group content;
  controls sit in the section head.
- **Cards** (`.card` / `.card-head` / `.card-body`) and the KPI strip
  (`.kpi-strip` of `.kpi`) are the primary containers.

Icons are monochrome CSS `mask-image` glyphs (`.ic .ic-<name>`) that inherit
`currentColor`, so they adapt to theme + hover. Helper: `controls.py::icon()`.

## 5. Signature components

- **KPI card** (`.kpi`): mono label, large display value, delta chip (`.kpi-delta
  up/down`), inline data-URI sparkline, left accent bar.
- **Stacked composition chart** + **draggable timeline scrubber** (`.scrubber`,
  `assets/scrubber.js`) + **click-to-detail drill panel** (`.detail-panel`).
- **Period-over-period waterfall** with run-off/changes/new + summary stats.
- **Facility grid** (`.facility-grid` / `.facility-mini`) — top movers with
  status dots + delta chips.
- **Borrower-credit trend** (Financial Trends): metric chips (`.chip-radio`),
  covenant threshold line + shaded breach zone + prior-year ghost, comparison
  strip, per-segment breach table (`.drill-table`).
- **⌘K command palette** (`.cmd-overlay` / `assets/command_palette.js`) — jump to
  tabs, run actions; client-side filter + keyboard nav.

## 6. Charts (Plotly)

Transparent backgrounds; text + gridlines are overridden by CSS to follow the
theme. Font is IBM Plex Mono. Categorical series use `SEGMENT_COLORS`. Status and
covenant cues use the status palette. See `utils/helpers.py::plotly_theme`.

## 7. Motion

- `--ease cubic-bezier(0.2,0.7,0.2,1)`, `--ease-out cubic-bezier(0,0,0.2,1)`.
- `.rise` entrance (transform only — always visible), `.drill-panel` slide-in,
  `.cmd-modal` pop, pulsing accent dots. Respects `prefers-reduced-motion`.

## 8. Don'ts

- Don't hardcode warm terracotta tones in new charts — use `SEGMENT_COLORS` /
  status tokens / `#4B6BFB`.
- Don't use sans for numerals — tabular figures use `--font-mono`.
- Don't add a 5th border weight or new shadow — reuse the 4 border tiers + 3
  shadow tiers.
- Keep element IDs stable — header controls and callbacks bind by ID.
