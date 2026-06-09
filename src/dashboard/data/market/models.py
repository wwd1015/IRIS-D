"""Pydantic models for the market monitor."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


Category = Literal[
    "valuation",
    "capital",
    "market_structure",
    "credit",
    "fundamentals",
    "macro",
]

Status = Literal["red", "yellow", "green"]

Verdict = Literal["observation", "caution", "alert", "systemic_top"]

# Tier thresholds (red-light ratio %): mirrors aibubble-cn's scoring,
# slightly relaxed for broad-market signals (more indicators dilute extremes).
TIER_THRESHOLDS: list[tuple[float, Verdict]] = [
    (60.0, "systemic_top"),  # ≥60% red → systemic top
    (40.0, "alert"),  # 40-60%   → high-risk alert
    (25.0, "caution"),  # 25-40%   → moderate caution
    (0.0, "observation"),  # <25%     → observation
]

VERDICT_LABELS: dict[Verdict, str] = {
    "observation": "Observation",
    "caution": "Caution",
    "alert": "High-Risk Alert",
    "systemic_top": "Systemic Top",
}


class Indicator(BaseModel):
    """A single market overheat / oversold indicator at a point in time."""

    id: str = Field(description="Stable slug (e.g. 'vix', 'shiller_cape').")
    name: str
    name_zh: str | None = None
    category: Category
    status: Status
    value: float | None = Field(
        default=None,
        description="Numeric reading where applicable.",
    )
    value_display: str = Field(description="Pretty-printed value shown in the UI.")
    threshold_text: str = Field(
        description="Human-readable threshold rule (e.g. '>35 red / 25-35 yellow / <25 green').",
    )
    source_name: str = Field(description="Data source attribution shown to the user.")
    source_url: str | None = None
    note: str = Field(default="", description="Italic explanatory text under the value.")
    last_updated: datetime = Field(default_factory=_utcnow)
    stale: bool = Field(
        default=False,
        description="True when data is older than the indicator's refresh cadence.",
    )
    auto: bool = Field(
        default=False,
        description="True when this indicator is refreshed by an automated collector "
        "rather than the research agent.",
    )


class WoWChange(BaseModel):
    """Week-over-week change tag shown in the trend section."""

    indicator_id: str
    type: Literal["up", "down", "flat"]
    note: str


class NarrativeInterpretation(BaseModel):
    """LLM-synthesised reading of the full snapshot.

    The mechanical verdict (label + score) summarises *how many* indicators
    are red. This summarises *what story they tell together* — which
    tensions matter, what regime this most resembles, what would tip the
    verdict, and the implied tilt for a research-only operator.
    """

    headline: str = Field(description="One-sentence dominant story.")
    regime: str = Field(
        description="Short label for the macro regime (e.g. 'Late-cycle complacency').",
    )
    tensions: list[str] = Field(
        default_factory=list,
        description="Competing signals — what's pulling in different directions.",
    )
    key_drivers: list[str] = Field(
        default_factory=list,
        description="Indicators that most determine the current verdict, with why.",
    )
    historical_analog: str = Field(
        default="",
        description="Short reference to a comparable historical period, if any.",
    )
    watch_next: list[str] = Field(
        default_factory=list,
        description="Specific indicators / thresholds whose move would tip the verdict.",
    )
    action_bias: str = Field(
        default="",
        description="One-line research tilt the picture implies.",
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=_utcnow)
    model_used: str = ""


class IndicatorSnapshot(BaseModel):
    """A complete dashboard snapshot at a point in time."""

    issue_number: int = Field(default=1, ge=1)
    as_of_date: date
    indicators: list[Indicator]
    red_count: int = 0
    yellow_count: int = 0
    green_count: int = 0
    red_pct: float = Field(default=0.0, description="red_count / total × 100")
    weighted_risk_score: float = Field(
        default=0.0,
        description="(red × 1.0 + yellow × 0.5) / total × 100",
    )
    verdict: Verdict = "observation"
    verdict_label: str = "Observation"
    verdict_summary: str = ""
    interpretation: NarrativeInterpretation | None = Field(
        default=None,
        description="LLM-synthesised narrative reading of the full snapshot. "
        "None until `MarketMonitor.interpret()` is called.",
    )
    wow_changes: list[WoWChange] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)


class HistorySnapshot(BaseModel):
    """Compact historical row used to render the trend chart."""

    as_of_date: date
    weighted_risk_score: float
    red_pct: float
    verdict: Verdict


class IndicatorDefinition(BaseModel):
    """Static catalog entry describing one tracked indicator.

    The research agent + automated collectors mutate the *value/status* of
    indicators over time; the catalog defines the slots themselves.
    """

    id: str
    name: str
    name_zh: str | None = None
    category: Category
    threshold_text: str
    research_prompt: str = Field(
        description="Instruction for the LLM research agent: what to look up and how "
        "to map the answer to red/yellow/green.",
    )
    default_source: str = Field(
        description="Default source_name when no fresher value is recorded yet.",
    )
    default_source_url: str | None = Field(
        default=None,
        description="Default canonical URL the user can click to verify the value.",
    )
    default_status: Status = "green"
    default_value_display: str = "—"
    default_note: str = ""
    auto_collector: str | None = Field(
        default=None,
        description="Name of the automated collector function, when one exists.",
    )
    refresh_cadence_hours: int = Field(
        default=24 * 7,
        description="Hours after which the indicator is marked stale.",
    )


class RefreshResult(BaseModel):
    """Output of a single-indicator refresh call."""

    indicator_id: str
    ok: bool
    status: Status | None = None
    value_display: str | None = None
    note: str | None = None
    source_used: str | None = None
    error: str | None = None
