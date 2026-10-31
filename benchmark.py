#!/usr/bin/env python3
"""
Measure the cost of one Provenance Guard run.

    python app.py                 # in one terminal
    python benchmark.py           # in another

The service runs GPT-2 locally, so the real cost is seconds of compute, not API
spend. This sends one warm-up request and then N measured requests, reads the
structured run log back through `GET /runs`, and reports the average total and
per-stage milliseconds. It writes `results/cost_<date>.md`.

Why a warm-up: the first request loads ~550 MB of model weights into memory.
That load is real, but it is a startup cost paid once, not a per-run cost.
"""

import argparse
import datetime as dt
import statistics

import requests

import config

TEXT = (
    "The committee reviewed the proposed schedule and considered the effects on "
    "staffing, cost, and access. Although the revised plan requires additional "
    "preparation, it gives each department more time to respond. Members agreed "
    "that the change should be evaluated after the first quarter, when reliable "
    "figures are available."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--url", default=f"http://{config.HOST}:{config.PORT}")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    health = requests.get(f"{args.url}/health", timeout=10).json()
    print(f"service: {args.url}")
    print(f"model: {health.get('detector_model')} loaded={health.get('detector_loaded')}")

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"bench_{stamp}_{args.label or 'run'}"

    # Warm the model so the measurement is a per-run cost, not startup.
    warm = requests.post(
        f"{args.url}/submit",
        json={"text": TEXT, "creator_id": f"{prefix}_warmup"},
        timeout=120,
    )
    warm.raise_for_status()
    print(f"warm-up: {warm.status_code}")

    durations = []
    for i in range(1, args.runs + 1):
        response = requests.post(
            f"{args.url}/submit",
            json={"text": TEXT, "creator_id": f"{prefix}_{i}"},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        print(f"  {i:>2}/{args.runs} {response.status_code} "
              f"{payload.get('guess')} combined={payload.get('combined_score')}")

    runs = requests.get(f"{args.url}/runs?limit=1000", timeout=10).json()["entries"]
    measured = [
        entry for entry in runs
        if str(entry.get("creator_id", "")).startswith(prefix)
        and entry.get("creator_id") != f"{prefix}_warmup"
        and entry.get("event") == "decision"
    ]
    if len(measured) < args.runs:
        raise SystemExit(
            f"expected {args.runs} measured runs, found {len(measured)} in /runs"
        )

    for entry in measured:
        durations.append(entry["duration_ms"])

    stages = {}
    for entry in measured:
        for name, value in (entry.get("stages") or {}).items():
            stages.setdefault(name, []).append(value)

    average_ms = statistics.mean(durations)
    average_s = average_ms / 1000.0
    total_s = sum(durations) / 1000.0
    stage_averages = {name: statistics.mean(values) for name, values in stages.items()}

    lines = [
        f"# Cost measurement{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `benchmark.py::main`",
        f"- Service: `{args.url}` · model `{health.get('detector_model')}` (local CPU)",
        f"- {args.runs} measured runs after one warm-up · "
        f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "- Cost unit: seconds of local compute per `/submit` decision",
        "",
        "## Result",
        "",
        f"- Average end-to-end: **{average_ms:.0f} ms** "
        f"(**{average_s:.3f} s of compute per run**)",
        f"- Median: {statistics.median(durations):.0f} ms",
        f"- Fastest / slowest: {min(durations):.0f} / {max(durations):.0f} ms",
        f"- Total for {args.runs} runs: {total_s:.3f} s",
        f"- API spend: **$0.00** — the model runs locally; no hosted API is called",
        "",
        "## Where the time went",
        "",
        "| Stage | Average ms | Share of total |",
        "|---|---:|---:|",
    ]
    for name, value in sorted(stage_averages.items(), key=lambda kv: -kv[1]):
        share = (value / average_ms * 100.0) if average_ms else 0.0
        lines.append(f"| `{name}` | {value:.1f} | {share:.1f}% |")

    lines += [
        "",
        "## Per-run durations",
        "",
        "| Run | Duration ms | Model ms | Style ms | Guess |",
        "|---:|---:|---:|---:|---|",
    ]
    for i, entry in enumerate(measured, 1):
        stages_for_run = entry.get("stages") or {}
        lines.append(
            f"| {i} | {entry['duration_ms']:.1f} | "
            f"{stages_for_run.get('model_ms', 0):.1f} | "
            f"{stages_for_run.get('style_ms', 0):.1f} | "
            f"{entry.get('output', {}).get('guess', '—')} |"
        )

    hundred_seconds = average_s * 100
    lines += [
        "",
        "## Hundred-a-day arithmetic",
        "",
        f"At {average_s:.3f} s per run, 100 runs per day is "
        f"`100 × {average_s:.3f} = {hundred_seconds:.1f} s` of compute per day "
        f"(about {hundred_seconds / 60:.1f} minutes, or "
        f"{hundred_seconds / 3600:.2f} hours). API spend is $0.00 per day.",
        "",
    ]

    config.RESULTS_DIR.mkdir(exist_ok=True)
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"cost_{stamp}{label}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines[:12]))
    print(f"\nWrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
