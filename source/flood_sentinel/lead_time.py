"""Empirical flood warning lead-time analysis relative to NOAA NWPS flood stages.

Evaluates operational advance warning times for interval-censored onsets (L, U]
with one-to-one event matching, cooldown deduplication, and NOAA flood category
stratification (Action, Minor, Moderate, Major) per plan.md Section 8.4.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def _parse_iso(timestamp_str: str) -> datetime:
    """Parse standard ISO 8601 UTC timestamp."""
    s = timestamp_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_sample_id_metadata(sample_id: str) -> tuple[str, datetime]:
    """Extract station site_no and issue timestamp from canonical sample_id.

    Example: '01646500_20180603T180000Z' -> ('01646500', 2018-06-03 18:00:00+00:00)
    """
    parts = sample_id.split("_")
    if len(parts) < 2:
        raise ValueError(f"Invalid sample_id format: {sample_id}")
    site_no = parts[0]
    time_part = parts[1]
    # Handle YYYYMMDDTHHMMSSZ
    if len(time_part) == 16 and time_part[8] == "T" and time_part.endswith("Z"):
        formatted = f"{time_part[:4]}-{time_part[4:6]}-{time_part[6:8]}T{time_part[9:11]}:{time_part[11:13]}:{time_part[13:15]}+00:00"
        issue_time = datetime.fromisoformat(formatted)
    else:
        issue_time = _parse_iso(time_part)
    return site_no, issue_time


@dataclass(frozen=True)
class LeadTimeRecord:
    """Detailed evaluation record for a single emitted warning alert."""
    sample_id: str
    site_no: str
    issue_time_utc: str
    alert_score: float
    matched_event_id: str | None
    matched_category: str | None
    onset_lower_utc: str | None
    onset_upper_utc: str | None
    lead_time_lower_hours: float | None
    lead_time_upper_hours: float | None
    lead_time_mid_hours: float | None
    is_advance_warning: bool | None
    is_false_alert: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LeadTimeSummary:
    """Aggregate lead-time performance and category-stratified recall."""
    total_eval_samples: int
    total_alerts: int
    matched_alerts: int
    false_alerts: int
    false_alert_rate: float
    total_events: int
    matched_events: int
    missed_events: int
    overall_event_recall: float
    recall_by_category: dict[str, float]
    mean_lead_time_hours: float | None
    median_lead_time_hours: float | None
    min_lead_time_hours: float | None
    max_lead_time_hours: float | None
    lead_times_by_category: dict[str, dict[str, float | None]]
    records: list[LeadTimeRecord]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["records"] = [r.to_dict() for r in self.records]
        return d


def load_event_intervals(source: Path | str | Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Load verified flood event intervals from file or sequence."""
    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.is_file():
            raise FileNotFoundError(f"Event intervals file not found: {p}")
        with p.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    return [dict(item) for item in source]


def evaluate_warning_lead_times(
    predictions: Sequence[Mapping[str, Any]],
    event_intervals: Path | str | Sequence[Mapping[str, Any]],
    threshold: float = 0.5,
    horizon_hours: float = 24.0,
    cooldown_hours: float = 12.0,
) -> LeadTimeSummary:
    """Evaluate operational advance warning times against verified flood episodes.

    Parameters:
        predictions: List of dicts with 'sample_id' and 'score' (and optional 'label').
        event_intervals: Path or records from data/event_intervals.csv.
        threshold: Score threshold triggering an alert (default: 0.5).
        horizon_hours: Maximum lookahead horizon for event association (default: 24.0h).
        cooldown_hours: Minimum hours between consecutive alerts on the same gauge
                        to deduplicate persistent warnings (default: 12.0h).

    Returns:
        LeadTimeSummary containing matched events, false alerts, and interval lead times.
    """
    events_raw = load_event_intervals(event_intervals)
    parsed_events: list[dict[str, Any]] = []
    for ev in events_raw:
        if not ev.get("onset_lower_utc") or not ev.get("onset_upper_utc"):
            continue
        parsed_events.append({
            "event_id": ev["event_id"],
            "site_no": str(ev["site_no"]),
            "category": str(ev.get("category", "action")).lower(),
            "onset_lower": _parse_iso(ev["onset_lower_utc"]),
            "onset_upper": _parse_iso(ev["onset_upper_utc"]),
            "onset_lower_str": ev["onset_lower_utc"],
            "onset_upper_str": ev["onset_upper_utc"],
        })

    # Sort predictions chronologically
    parsed_preds: list[dict[str, Any]] = []
    for p in predictions:
        sid = str(p["sample_id"])
        score = float(p["score"])
        site_no, issue_time = parse_sample_id_metadata(sid)
        parsed_preds.append({
            "sample_id": sid,
            "site_no": site_no,
            "issue_time": issue_time,
            "score": score,
            "is_alert": score >= threshold,
        })
    parsed_preds.sort(key=lambda x: (x["site_no"], x["issue_time"]))

    # Apply cooldown deduplication per station
    active_alerts: list[dict[str, Any]] = []
    last_alert_time: dict[str, datetime] = {}
    for pred in parsed_preds:
        if not pred["is_alert"]:
            continue
        site = pred["site_no"]
        t_issue = pred["issue_time"]
        if site in last_alert_time:
            dt_hours = (t_issue - last_alert_time[site]).total_seconds() / 3600.0
            if dt_hours < cooldown_hours:
                # Within cooldown: skip deduplicated follow-up alert
                continue
        last_alert_time[site] = t_issue
        active_alerts.append(pred)

    matched_event_ids: set[str] = set()
    records: list[LeadTimeRecord] = []
    matched_lead_times_mid: list[float] = []
    category_lead_times: dict[str, list[float]] = {cat: [] for cat in ("action", "minor", "moderate", "major")}

    for alert in active_alerts:
        site = alert["site_no"]
        t_alert = alert["issue_time"]
        score = alert["score"]

        # Search for eligible matching episode
        best_match = None
        min_lead = float("inf")

        for ev in parsed_events:
            if ev["site_no"] != site:
                continue
            if ev["event_id"] in matched_event_ids:
                continue  # One-to-one mapping rule

            onset_l = ev["onset_lower"]
            onset_u = ev["onset_upper"]

            # Lead time calculation
            lead_l_h = (onset_l - t_alert).total_seconds() / 3600.0
            lead_u_h = (onset_u - t_alert).total_seconds() / 3600.0

            # Eligible if onset is ahead of alert, within lookahead horizon
            if 0.0 <= lead_u_h <= horizon_hours or (lead_l_h >= 0.0 and lead_l_h <= horizon_hours):
                if lead_l_h < min_lead:
                    min_lead = lead_l_h
                    best_match = (ev, lead_l_h, lead_u_h)

        if best_match is not None:
            ev, lead_l_h, lead_u_h = best_match
            matched_event_ids.add(ev["event_id"])
            mid_h = (lead_l_h + lead_u_h) / 2.0
            matched_lead_times_mid.append(mid_h)
            cat = ev["category"]
            if cat in category_lead_times:
                category_lead_times[cat].append(mid_h)

            records.append(LeadTimeRecord(
                sample_id=alert["sample_id"],
                site_no=site,
                issue_time_utc=t_alert.isoformat(),
                alert_score=score,
                matched_event_id=ev["event_id"],
                matched_category=cat,
                onset_lower_utc=ev["onset_lower_str"],
                onset_upper_utc=ev["onset_upper_str"],
                lead_time_lower_hours=float(round(lead_l_h, 3)),
                lead_time_upper_hours=float(round(lead_u_h, 3)),
                lead_time_mid_hours=float(round(mid_h, 3)),
                is_advance_warning=lead_l_h > 0.0,
                is_false_alert=False,
            ))
        else:
            # Emitted alert had no matching onset within horizon
            records.append(LeadTimeRecord(
                sample_id=alert["sample_id"],
                site_no=site,
                issue_time_utc=t_alert.isoformat(),
                alert_score=score,
                matched_event_id=None,
                matched_category=None,
                onset_lower_utc=None,
                onset_upper_utc=None,
                lead_time_lower_hours=None,
                lead_time_upper_hours=None,
                lead_time_mid_hours=None,
                is_advance_warning=None,
                is_false_alert=True,
            ))

    # Event coverage statistics
    total_events_by_category: dict[str, int] = {cat: 0 for cat in ("action", "minor", "moderate", "major")}
    matched_events_by_category: dict[str, int] = {cat: 0 for cat in ("action", "minor", "moderate", "major")}
    for ev in parsed_events:
        cat = ev["category"]
        if cat in total_events_by_category:
            total_events_by_category[cat] += 1
            if ev["event_id"] in matched_event_ids:
                matched_events_by_category[cat] += 1

    recall_by_category: dict[str, float] = {}
    for cat, total in total_events_by_category.items():
        recall_by_category[cat] = float(matched_events_by_category[cat] / total) if total > 0 else 0.0

    total_events = len(parsed_events)
    matched_events = len(matched_event_ids)
    missed_events = total_events - matched_events
    overall_recall = float(matched_events / total_events) if total_events > 0 else 0.0

    total_alerts = len(active_alerts)
    matched_alerts = len(matched_event_ids)
    false_alerts = sum(1 for r in records if r.is_false_alert)
    false_alert_rate = float(false_alerts / total_alerts) if total_alerts > 0 else 0.0

    # Lead-time summary statistics
    mean_lead = float(np.mean(matched_lead_times_mid)) if matched_lead_times_mid else None
    median_lead = float(np.median(matched_lead_times_mid)) if matched_lead_times_mid else None
    min_lead = float(np.min(matched_lead_times_mid)) if matched_lead_times_mid else None
    max_lead = float(np.max(matched_lead_times_mid)) if matched_lead_times_mid else None

    category_summaries: dict[str, dict[str, float | None]] = {}
    for cat in ("action", "minor", "moderate", "major"):
        times = category_lead_times[cat]
        category_summaries[cat] = {
            "mean_lead_hours": float(np.mean(times)) if times else None,
            "median_lead_hours": float(np.median(times)) if times else None,
            "min_lead_hours": float(np.min(times)) if times else None,
            "max_lead_hours": float(np.max(times)) if times else None,
            "event_count": total_events_by_category[cat],
            "detected_count": matched_events_by_category[cat],
            "recall": recall_by_category[cat],
        }

    return LeadTimeSummary(
        total_eval_samples=len(predictions),
        total_alerts=total_alerts,
        matched_alerts=matched_alerts,
        false_alerts=false_alerts,
        false_alert_rate=false_alert_rate,
        total_events=total_events,
        matched_events=matched_events,
        missed_events=missed_events,
        overall_event_recall=overall_recall,
        recall_by_category=recall_by_category,
        mean_lead_time_hours=mean_lead,
        median_lead_time_hours=median_lead,
        min_lead_time_hours=min_lead,
        max_lead_time_hours=max_lead,
        lead_times_by_category=category_summaries,
        records=records,
    )
