"""Market monitor — live web-fetch data model ported from Kestrel.

Runs the automated collectors (FRED CSV / Yahoo / scrape — no API keys) to
produce a snapshot of broad-market overheat indicators, scored red/yellow/green
and rolled up into a weighted risk score + verdict.

Only **automatically-collectable** indicators are included; the research-agent
indicators from the Kestrel catalog are dropped (per product decision).

Render path is non-blocking: ``get_snapshot()`` returns a cached / seeded
snapshot instantly. ``refresh()`` performs the live web fetch (used by the
"Refresh" button) and is the only slow path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import UTC, date, datetime
from pathlib import Path

from .collectors import COLLECTORS
from .definitions import CATALOG
from .models import TIER_THRESHOLDS, VERDICT_LABELS

log = logging.getLogger(__name__)

CATEGORY_LABEL: dict[str, str] = {
    "valuation": "Valuation",
    "capital": "Capital Flows",
    "market_structure": "Market Structure",
    "credit": "Credit",
    "fundamentals": "Fundamentals",
    "macro": "Macro",
}
CATEGORY_ORDER = ["valuation", "capital", "market_structure", "credit", "fundamentals", "macro"]

# Auto-fetch indicators only (drop research-agent-only catalog entries).
AUTO_DEFS = [d for d in CATALOG if d.auto_collector and d.auto_collector in COLLECTORS]
_AUTO_IDS = {d.id for d in AUTO_DEFS}

_TTL_SECONDS = 60 * 30  # treat a fetched snapshot as fresh for 30 min
_cache: dict = {"snapshot": None, "ts": 0.0}


# ── paths ────────────────────────────────────────────────────────────────────

def _repo_root() -> Path:
    # src/dashboard/data/market/monitor.py → repo root is parents[4]
    return Path(__file__).resolve().parents[4]


def _persist_path() -> Path:
    env = os.environ.get("MARKET_INSIGHT_JSON")
    if env:
        return Path(env)
    return _repo_root() / "data" / "market_insight.json"


def _kestrel_seed_path() -> Path:
    env = os.environ.get("KESTREL_MARKET_JSON")
    if env:
        return Path(env)
    return _repo_root().parent / "Kestrel" / "data" / "market_monitor_current.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── snapshot assembly ────────────────────────────────────────────────────────

def _seed_indicator(d) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "name_zh": d.name_zh,
        "category": d.category,
        "status": d.default_status,
        "value": None,
        "value_display": d.default_value_display,
        "threshold_text": d.threshold_text,
        "source_name": d.default_source,
        "source_url": d.default_source_url,
        "note": d.default_note,
        "last_updated": _now_iso(),
        "stale": True,
        "auto": True,
    }


def _compute_rollup(indicators: list[dict]) -> dict:
    total = len(indicators) or 1
    red = sum(1 for i in indicators if i["status"] == "red")
    yellow = sum(1 for i in indicators if i["status"] == "yellow")
    green = len(indicators) - red - yellow
    red_pct = (red / total) * 100.0
    weighted = ((red + 0.5 * yellow) / total) * 100.0
    verdict = "observation"
    for floor, label in TIER_THRESHOLDS:
        if red_pct >= floor:
            verdict = label
            break
    return {
        "red_count": red, "yellow_count": yellow, "green_count": green,
        "red_pct": red_pct, "weighted_risk_score": weighted,
        "verdict": verdict, "verdict_label": VERDICT_LABELS[verdict],
    }


def _wrap(indicators: list[dict], issue: int = 1) -> dict:
    snap = {
        "issue_number": issue,
        "as_of_date": date.today().isoformat(),
        "indicators": indicators,
        "generated_at": _now_iso(),
        "category_label": CATEGORY_LABEL,
        "category_order": CATEGORY_ORDER,
    }
    snap.update(_compute_rollup(indicators))
    return snap


# ── seeding (fast, no network) ───────────────────────────────────────────────

def _load_json(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        log.warning("market_monitor: failed reading %s: %s", path, e)
    return None


def _seed_snapshot() -> dict:
    """Build a snapshot without any network call.

    Priority: IRIS-D's own persisted JSON → Kestrel's snapshot (auto-only) →
    catalog defaults.
    """
    persisted = _load_json(_persist_path())
    if persisted and persisted.get("indicators"):
        inds = [i for i in persisted["indicators"] if i.get("id") in _AUTO_IDS]
        if inds:
            return _wrap(inds, issue=persisted.get("issue_number", 1))

    kestrel = _load_json(_kestrel_seed_path())
    if kestrel and kestrel.get("indicators"):
        seed_by_id = {i["id"]: i for i in kestrel["indicators"] if i.get("id") in _AUTO_IDS}
        inds = []
        for d in AUTO_DEFS:
            src = seed_by_id.get(d.id)
            base = _seed_indicator(d)
            if src:
                for k in ("status", "value", "value_display", "note",
                          "source_name", "source_url", "last_updated", "stale"):
                    if k in src and src[k] is not None:
                        base[k] = src[k]
            inds.append(base)
        return _wrap(inds, issue=kestrel.get("issue_number", 1))

    return _wrap([_seed_indicator(d) for d in AUTO_DEFS])


# ── live fetch (slow, network) ───────────────────────────────────────────────

async def _run_collectors() -> dict:
    coros = [COLLECTORS[d.auto_collector]() for d in AUTO_DEFS]
    results = await asyncio.gather(*coros, return_exceptions=True)
    out = {}
    for d, r in zip(AUTO_DEFS, results):
        if isinstance(r, Exception):
            log.warning("market_monitor: collector %s failed: %s", d.auto_collector, r)
            continue
        out[d.id] = r
    return out


def _fetch_snapshot(prior: dict | None) -> dict:
    """Run the live collectors and merge results onto seeded/prior indicators."""
    by_id = {}
    prior_by_id = {i["id"]: i for i in (prior or {}).get("indicators", [])}
    for d in AUTO_DEFS:
        ind = _seed_indicator(d)
        p = prior_by_id.get(d.id)
        if p:  # carry last-good values forward in case a collector fails
            for k in ("status", "value", "value_display", "note", "source_name", "source_url", "last_updated"):
                if k in p and p[k] is not None:
                    ind[k] = p[k]
        by_id[d.id] = ind

    try:
        results = asyncio.run(_run_collectors())
    except Exception as e:  # noqa: BLE001
        log.warning("market_monitor: live fetch failed: %s", e)
        results = {}

    for rid, res in results.items():
        ind = by_id.get(rid)
        if ind is None or not getattr(res, "ok", False):
            continue
        if res.status:
            ind["status"] = res.status
        if res.value_display is not None:
            ind["value_display"] = res.value_display
        if res.note:
            ind["note"] = res.note
        if res.source_used:
            ind["source_name"] = res.source_used
        ind["last_updated"] = _now_iso()
        ind["stale"] = False

    inds = [by_id[d.id] for d in AUTO_DEFS]
    issue = (prior or {}).get("issue_number", 0) + 1 if prior else 1
    return _wrap(inds, issue=issue)


def _persist(snap: dict) -> None:
    try:
        p = _persist_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(snap, indent=2))
    except Exception as e:  # noqa: BLE001
        log.warning("market_monitor: persist failed: %s", e)


# ── public API ───────────────────────────────────────────────────────────────

def get_snapshot() -> dict:
    """Return the current snapshot (cache → persisted/seed). Never hits the network."""
    if _cache["snapshot"] is None:
        _cache["snapshot"] = _seed_snapshot()
        _cache["ts"] = time.time()
    return _cache["snapshot"]


def refresh(indicator_id: str | None = None) -> dict:
    """Live web fetch via the ported collectors; updates cache + persisted JSON.

    ``indicator_id`` is accepted for per-card refresh but the collectors run as a
    batch (cheap, parallel), so it simply triggers a full refresh.
    """
    prior = _cache["snapshot"] or _seed_snapshot()
    snap = _fetch_snapshot(prior)
    _cache["snapshot"] = snap
    _cache["ts"] = time.time()
    _persist(snap)
    return snap
