#!/usr/bin/env python3
"""
Run the five Unit 9 capstone criteria three times each.

    python app.py                       # in one terminal
    python capstone_eval.py --label before
    python capstone_eval.py --label after

The script only sends requests and records what came back. The verdicts are
decided against `criteria.md`, not invented here.

Outputs:
    results/capstone_<label>.md    human-readable run log + raw JSON
    results/capstone_<label>.json  machine-readable results
"""

import argparse
import datetime as dt
import json
import statistics
import time

import requests

import config

URL = f"http://{config.HOST}:{config.PORT}"

HUMAN_TEXT = (
    "Oh, what a morning! I missed the bus. Again. A cyclist splashed straight "
    "through a puddle; my coffee went flying, and somewhere in all that chaos a "
    "tiny dog stole half my muffin. Honestly, I laughed—there wasn't much else "
    "to do. By noon, everything had somehow worked out."
)
LIGHT_AI_TEXT = (
    "Many people are looking for ways to make their daily routines more "
    "efficient. A clear plan helps you stay focused, and it can also save time. "
    "In the end, small changes usually make the biggest difference—at least, "
    "that is what I keep telling myself."
)
CLEAR_AI_TEXT = (
    "Artificial intelligence is transforming the way organizations operate. It "
    "enables businesses to automate repetitive tasks, analyze large amounts of "
    "data, and improve decision-making. As these technologies continue to "
    "advance, organizations must consider both their opportunities and their "
    "potential challenges. A thoughtful approach can help ensure that AI is "
    "used effectively and responsibly."
)
CALIBRATION = [
    ("human-style control", HUMAN_TEXT),
    ("lightly edited AI", LIGHT_AI_TEXT),
    ("clearly AI", CLEAR_AI_TEXT),
]

REQUIRED_FIELDS = (
    ("timestamp", None),
    ("request_id", None),
    ("input.chars", ("input", "chars")),
    ("output.guess", ("output", "guess")),
    ("output.combined_score", ("output", "combined_score")),
    ("duration_ms", None),
    ("stages.model_ms", ("stages", "model_ms")),
)


def post(body=None, raw=None, timeout=120):
    if raw is not None:
        response = requests.post(
            f"{URL}/submit",
            data=raw.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    else:
        response = requests.post(f"{URL}/submit", json=body, timeout=timeout)
    try:
        payload = response.json()
    except ValueError:
        payload = {"_raw": response.text[:300]}
    return response.status_code, payload


def get(path):
    response = requests.get(f"{URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def field_value(entry, path):
    value = entry
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def is_complete(entry):
    missing = [
        name for name, path in REQUIRED_FIELDS
        if (entry.get(name) is None if path is None else field_value(entry, path) is None)
    ]
    return not missing, missing


def run_c1(trial, prefix):
    """10 successful submissions; every /runs record must be complete."""
    bodies = [
        {"text": HUMAN_TEXT, "creator_id": f"{prefix}_c1_{i}"}
        for i in range(1, 11)
    ]
    responses = []
    for body in bodies:
        status, payload = post(body)
        responses.append({"status": status, "guess": payload.get("guess")})

    entries = get("/runs?limit=5000")["entries"]
    mine = [
        entry for entry in entries
        if str(entry.get("creator_id", "")).startswith(prefix)
        and entry.get("event") == "decision"
    ]
    checks = []
    for entry in mine:
        complete, missing = is_complete(entry)
        checks.append({
            "request_id": entry.get("request_id"),
            "creator_id": entry.get("creator_id"),
            "complete": complete,
            "missing": missing,
        })
    complete_count = sum(1 for check in checks if check["complete"])
    return {
        "trial": trial,
        "expected": 10,
        "found": len(mine),
        "complete": complete_count,
        "pass": len(mine) == 10 and complete_count == 10,
        "responses": responses,
        "checks": checks,
        "sample_entry": mine[0] if mine else None,
    }


def run_c2(trial, prefix):
    """Warm up, then measure 10 client-side end-to-end latencies."""
    post({"text": HUMAN_TEXT, "creator_id": f"{prefix}_c2_warmup"})
    latencies = []
    responses = []
    for i in range(1, 11):
        started = time.perf_counter()
        status, payload = post({"text": HUMAN_TEXT, "creator_id": f"{prefix}_c2_{i}"})
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        latencies.append(round(elapsed_ms, 3))
        responses.append({"status": status, "guess": payload.get("guess"),
                          "elapsed_ms": round(elapsed_ms, 3)})

    under = sum(1 for value in latencies if value <= 5000.0)
    runs = get("/runs?limit=5000")["entries"]
    server_ms = [
        entry["duration_ms"] for entry in runs
        if str(entry.get("creator_id", "")).startswith(prefix)
        and entry.get("creator_id") != f"{prefix}_c2_warmup"
        and entry.get("event") == "decision"
        and isinstance(entry.get("duration_ms"), (int, float))
    ]
    return {
        "trial": trial,
        "expected_under": 9,
        "under_5000": under,
        "latencies_ms": latencies,
        "median_ms": round(statistics.median(latencies), 3),
        "max_ms": max(latencies),
        "server_side_ms": server_ms,
        "pass": under >= 9,
        "responses": responses,
    }


def run_c3(trial, prefix):
    """Five deliberate failures must return 4xx/503 and be logged."""
    flood_creator = f"{prefix}_c3_flood"

    # Exhaust the 10/minute bucket, then make the 11th request fail with 429.
    for i in range(10):
        post({"text": HUMAN_TEXT, "creator_id": flood_creator})
    status_429, payload_429 = post({"text": HUMAN_TEXT, "creator_id": flood_creator})

    failures = []
    failures.append({
        "case": "rate_limited",
        "status": status_429,
        "payload": payload_429,
        "creator_id": flood_creator,
    })

    cases = [
        ("missing_text", {"creator_id": f"{prefix}_c3_missing"}),
        ("empty_text", {"text": "", "creator_id": f"{prefix}_c3_empty"}),
        ("invalid_json", None),
        ("text_too_large", {"text": "word " * 2501,
                            "creator_id": f"{prefix}_c3_large"}),
    ]
    for case, body in cases:
        if case == "invalid_json":
            status, payload = post(raw="{not valid json")
            creator = None
        else:
            status, payload = post(body)
            creator = body.get("creator_id")
        failures.append({
            "case": case,
            "status": status,
            "payload": payload,
            "creator_id": creator,
        })

    time.sleep(0.2)  # let the append-only log settle
    runs = get("/runs?limit=5000")["entries"]
    mine = [
        entry for entry in runs
        if entry.get("event") == "rejected"
        and (
            str(entry.get("creator_id", "")).startswith(prefix)
            or entry.get("error") == "invalid_json"
        )
    ]

    checks = []
    for failure in failures:
        expected_creator = failure["creator_id"]
        match = next(
            (
                entry for entry in reversed(mine)
                if entry.get("error")
                and (
                    (expected_creator is not None and entry.get("creator_id") == expected_creator)
                    or (expected_creator is None and entry.get("error") == "invalid_json")
                )
            ),
            None,
        )
        ok_status = failure["status"] in (400, 404, 429, 503)
        ok_log = bool(
            match
            and match.get("timestamp")
            and match.get("request_id")
            and isinstance(match.get("duration_ms"), (int, float))
            and match.get("error")
        )
        checks.append({
            "case": failure["case"],
            "status": failure["status"],
            "status_ok": ok_status,
            "logged": ok_log,
            "log_error": match.get("error") if match else None,
            "log_request_id": match.get("request_id") if match else None,
            "log_duration_ms": match.get("duration_ms") if match else None,
        })

    passed = sum(1 for check in checks if check["status_ok"] and check["logged"])
    return {
        "trial": trial,
        "expected": 5,
        "passed": passed,
        "pass": passed == 5,
        "checks": checks,
        "failures": failures,
    }


def run_c4(trial, prefix):
    """Compare GET /metrics against GET /runs after a controlled batch."""
    for i in range(4):
        post({"text": HUMAN_TEXT, "creator_id": f"{prefix}_c4_{i}"})
    post({"text": "", "creator_id": f"{prefix}_c4_bad"})

    runs = get("/runs?limit=5000")["entries"]
    metrics = get("/metrics")

    decisions = [entry for entry in runs if entry.get("event") == "decision"]
    rejections = [entry for entry in runs if entry.get("event") == "rejected"]
    decision_durations = [
        entry["duration_ms"] for entry in decisions
        if isinstance(entry.get("duration_ms"), (int, float))
    ]
    expected_average_s = (
        statistics.mean(decision_durations) / 1000.0 if decision_durations else None
    )
    reported_average_s = metrics.get("compute_seconds_per_decision")
    average_delta = (
        abs(reported_average_s - expected_average_s)
        if reported_average_s is not None and expected_average_s is not None
        else None
    )
    counts_ok = (
        metrics.get("total_runs") == len(runs)
        and metrics.get("decisions") == len(decisions)
        and metrics.get("rejections") == len(rejections)
    )
    average_ok = average_delta is not None and average_delta <= 0.001
    return {
        "trial": trial,
        "metrics": metrics,
        "run_counts": {
            "total_runs": len(runs),
            "decisions": len(decisions),
            "rejections": len(rejections),
        },
        "expected_average_seconds": round(expected_average_s, 6)
        if expected_average_s is not None else None,
        "reported_average_seconds": reported_average_s,
        "average_delta_seconds": round(average_delta, 6)
        if average_delta is not None else None,
        "counts_ok": counts_ok,
        "average_ok": average_ok,
        "pass": counts_ok and average_ok,
    }


def run_c5(trial, prefix):
    """Existing decision path: response shape and all three labels."""
    rows = []
    for name, text in CALIBRATION:
        status, payload = post({"text": text, "creator_id": f"{prefix}_c5_{name}"})
        rows.append({
            "input": name,
            "status": status,
            "guess": payload.get("guess"),
            "label": payload.get("label"),
            "content_id": payload.get("content_id"),
            "model_score": payload.get("model_score"),
            "style_score": payload.get("style_score"),
            "combined_score": payload.get("combined_score"),
        })

    required = ("content_id", "guess", "label", "model_score",
                "style_score", "combined_score")
    shape_ok = all(
        row["status"] == 200 and all(row.get(field) is not None for field in required)
        for row in rows
    )
    labels = {row.get("guess") for row in rows}
    coverage_ok = labels == {"human", "unsure", "ai"}
    return {
        "trial": trial,
        "rows": rows,
        "labels_seen": sorted(label for label in labels if label),
        "shape_ok": shape_ok,
        "coverage_ok": coverage_ok,
        "pass": shape_ok and coverage_ok,
    }


RUNNERS = {
    1: run_c1,
    2: run_c2,
    3: run_c3,
    4: run_c4,
    5: run_c5,
}

TITLES = {
    1: "Structured log completeness",
    2: "Warm latency",
    3: "Failure observability",
    4: "Metrics accuracy",
    5: "Regression and label coverage",
}

TARGETS = {
    1: "10/10 complete records",
    2: "9/10 under 5,000 ms",
    3: "5/5 failures 4xx/503 and logged",
    4: "exact counts; average within 0.001 s",
    5: "3/3 shape; all three labels",
}


def main():
    global URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--label", default="before")
    parser.add_argument("--url", default=URL)
    args = parser.parse_args()
    URL = args.url

    health = get("/health")
    print(f"service {URL} · model loaded={health.get('detector_loaded')}")

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"capstone_{args.label}_{stamp}"
    # Two creators share a prefix but criterion 3 uses its own bucket.
    results = {"label": args.label, "started": dt.datetime.now().isoformat(),
               "url": URL, "trials": args.trials, "criteria": {}}

    for number in range(1, 6):
        print(f"\nCriterion {number} — {TITLES[number]}")
        trials = []
        for trial in range(1, args.trials + 1):
            trial_prefix = f"{prefix}_c{number}_t{trial}"
            result = RUNNERS[number](trial, trial_prefix)
            trials.append(result)
            print(f"  trial {trial}: {'PASS' if result['pass'] else 'FAIL'}")
        overall = all(trial["pass"] for trial in trials)
        results["criteria"][str(number)] = {
            "title": TITLES[number],
            "target": TARGETS[number],
            "trials": trials,
            "verdict": "MET" if overall else "MISSED",
        }

    write_report(results, args)
    print("\nVerdicts:")
    for number, criterion in results["criteria"].items():
        print(f"  {number}. {criterion['title']}: {criterion['verdict']}")


def write_report(results, args):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = config.RESULTS_DIR / f"capstone_{args.label}_{stamp}"

    lines = [
        f"# Capstone run log — {args.label}",
        "",
        "- Produced by: `capstone_eval.py::main`",
        f"- Service: `{results['url']}`",
        f"- {results['trials']} trials per criterion · {results['started']}",
        "",
        "| Criterion | Target | Trial 1 | Trial 2 | Trial 3 | Verdict |",
        "|---|---|---|---|---|---|",
    ]

    for number, criterion in results["criteria"].items():
        cells = []
        for trial in criterion["trials"]:
            if number == "1":
                cells.append(f"{trial['complete']}/{trial['expected']} complete")
            elif number == "2":
                cells.append(f"{trial['under_5000']}/10 under 5s")
            elif number == "3":
                cells.append(f"{trial['passed']}/5")
            elif number == "4":
                cells.append("counts+avg OK" if trial["pass"] else "mismatch")
            else:
                cells.append(
                    f"{sum(1 for row in trial['rows'] if row['status'] == 200)}/3, "
                    f"{len(trial['labels_seen'])} labels"
                )
        lines.append(
            f"| {number}. {criterion['title']} | {criterion['target']} | "
            f"{' | '.join(cells)} | **{criterion['verdict']}** |"
        )

    lines += ["", "---", "", "## Raw trial output", ""]
    for number, criterion in results["criteria"].items():
        lines += [f"### {number}. {criterion['title']}", "",
                  "```json",
                  json.dumps(criterion["trials"], indent=2, ensure_ascii=False),
                  "```", ""]

    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    base.with_suffix(".json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nWrote {base.with_suffix('.md').relative_to(config.ROOT)}")
    print(f"Wrote {base.with_suffix('.json').relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
