"""
Structured run instrumentation for Provenance Guard.

Every `/submit` and `/appeal` request writes one JSON object per line to
`logs/runs.jsonl`. Unlike the decision-focused audit log, this file is about
*operating* the service: what came in, what came out, how long each stage took,
and whether the request succeeded or failed.

Named fields, always present:

    timestamp      UTC ISO-8601 seconds
    request_id     unique id for this HTTP request
    event          "decision" | "rejected" | "appeal"
    endpoint       "/submit" or "/appeal"
    creator_id     caller identifier, or "unknown"
    input          {chars, words, preview, ...}
    output         {guess, combined_score, ...} or {error, ...}
    duration_ms    wall-clock milliseconds for the whole request
    stages         per-stage milliseconds
    status         "decided" | "rejected" | "under_review"
    error          stable error code or None

The file is append-only JSONL so a crashed process cannot leave a half-written
record, and `read_runs` skips a malformed line instead of losing the rest.
"""

import json
import statistics
import threading
from datetime import datetime, timezone

import config

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_run(
    *,
    request_id: str,
    event: str,
    endpoint: str,
    creator_id: str = "unknown",
    input: dict | None = None,
    output: dict | None = None,
    duration_ms: float | None = None,
    stages: dict | None = None,
    status: str = "decided",
    error: str | None = None,
    **extra,
) -> dict:
    """Append one structured run record."""
    entry = {
        "timestamp": _now(),
        "request_id": request_id,
        "event": event,
        "endpoint": endpoint,
        "creator_id": creator_id,
        "input": input or {},
        "output": output or {},
        "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
        "stages": stages or {},
        "status": status,
        "error": error,
    }
    entry.update(extra)
    return _append(entry)


def _append(entry: dict) -> dict:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        with config.RUN_LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return entry


def read_runs(limit: int | None = None) -> list[dict]:
    """Read run records back, oldest first. A bad line is skipped."""
    if not config.RUN_LOG.exists():
        return []

    entries = []
    for line in config.RUN_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries[-limit:] if limit else entries


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(int(round((len(ordered) - 1) * fraction)), len(ordered) - 1)
    return round(ordered[index], 3)


def _average(values: list[float]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def summarize_runs(entries: list[dict] | None = None) -> dict:
    """
    Aggregate the run log without adding new logging code.

    This is what `GET /metrics` returns: totals, success/error counts, latency
    distribution, and the average seconds of compute per completed decision.
    """
    entries = read_runs() if entries is None else entries

    decisions = [entry for entry in entries if entry.get("event") == "decision"]
    rejections = [entry for entry in entries if entry.get("event") == "rejected"]
    appeals = [entry for entry in entries if entry.get("event") == "appeal"]

    durations = [
        entry["duration_ms"]
        for entry in entries
        if isinstance(entry.get("duration_ms"), (int, float))
    ]
    decision_durations = [
        entry["duration_ms"]
        for entry in decisions
        if isinstance(entry.get("duration_ms"), (int, float))
    ]

    stage_samples: dict[str, list[float]] = {}
    for entry in decisions:
        for name, value in (entry.get("stages") or {}).items():
            if isinstance(value, (int, float)):
                stage_samples.setdefault(name, []).append(value)

    error_counts: dict[str, int] = {}
    for entry in entries:
        error = entry.get("error")
        if error:
            error_counts[error] = error_counts.get(error, 0) + 1

    average_decision_ms = _average(decision_durations)
    return {
        "total_runs": len(entries),
        "decisions": len(decisions),
        "rejections": len(rejections),
        "appeals": len(appeals),
        "error_counts": error_counts,
        "latency_ms": {
            "average": _average(durations),
            "p50": _percentile(durations, 0.50),
            "p95": _percentile(durations, 0.95),
            "max": round(max(durations), 3) if durations else None,
        },
        "decision_latency_ms": {
            "average": average_decision_ms,
            "p50": _percentile(decision_durations, 0.50),
            "p95": _percentile(decision_durations, 0.95),
            "max": round(max(decision_durations), 3) if decision_durations else None,
        },
        "stage_average_ms": {
            name: _average(values) for name, values in sorted(stage_samples.items())
        },
        "compute_seconds_per_decision": (
            round(average_decision_ms / 1000.0, 4)
            if average_decision_ms is not None
            else None
        ),
    }
