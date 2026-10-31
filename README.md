# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 9 — CAPSTONE ═════════════════════════ -->

# Capstone (Unit 9) — Provenance Guard

## What This Extends

This capstone extends **Provenance Guard**, the system I built in Units 7 and 8.
It is the same repository and the same service: a Flask web service that scores
submitted text with a local GPT-2 model signal and a stylometry signal, combines
them, returns a reader-facing label, records decisions in an audit log, accepts
appeals, and rate-limits `/submit`.

**What is new in this unit:** an operational layer around the existing service.
Every successful decision and every handled rejection now writes a structured
run record with a request id, input shape, output shape, total duration,
per-stage timings, and status. Two read-only observability endpoints (`GET /runs` and `GET /metrics`)
expose those records without changing code. The run path is documented for a
clean checkout, and one run's cost is measured in seconds of local compute
rather than estimated from a pricing page.

## The Shape

**Shape A — Deploy and instrument.** The extension is the operational layer: a
reproducible local run path plus instrumentation that makes the running system
observable after the fact. I chose Path B (local with logs) because the detector
loads ~550 MB of GPT-2 weights into memory; the free hosting tier provides
512 MB, so a hosted deployment would be killed before its first request. Path B
is the documented answer for this system, not a fallback.

**Out of scope (decided in Milestone 1):**

- **No new detection signal or retriever.** The model signal and style signal
  stay as they are; I am not adding a third signal or replacing GPT-2.
- **No threshold recalibration.** The `HUMAN_THRESHOLD` / `AI_THRESHOLD` values
  and the 0.5/0.5 weights stay unchanged; this unit is about observing the
  system, not re-tuning its decisions.
- **No hosted deployment or web interface.** A free host cannot hold the model,
  and the existing JSON API is the interface under test.
- **No changes to the audit log's append-only decision record.** The new run log
  is separate evidence; the audit log keeps its existing shape.

The extension was built and tested in one unit. It adds instrumentation, two
read-only endpoints, a documented run path, and a benchmark script — nothing
that requires retraining or redesigning the detector.

## Running It

**Path B — local with logs.** The system runs on this machine, started by
`python app.py`, with the exact environment and setup commands in
[RUNNING.md](RUNNING.md). It is not hosted because the detector loads about
550 MB of GPT-2 weights into memory and a free host provides 512 MB.

On this machine port 5000 was already held by another local service, so the
committed evidence was produced with `$env:PORT=5055; python app.py` and every
URL below uses `127.0.0.1:5055`. The default in `RUNNING.md` is still 5000.

`logs/runs.jsonl` is the committed run record. `GET /runs` reads it back and
`GET /metrics` summarizes it.

## Instrumentation

Every successful decision, every handled rejection, and every rate-limit
rejection writes one JSON object per line to `logs/runs.jsonl`. A decision
record holds:

| Field | What it records |
|---|---|
| `timestamp` | UTC ISO-8601 time, seconds |
| `request_id` | unique id for this HTTP request |
| `event` | `decision`, `rejected`, or `appeal` |
| `endpoint` | `/submit` or `/appeal` |
| `creator_id` | caller identifier, or `unknown` |
| `input` | `chars`, `words`, `preview`, and (after the improvement) `sha256` |
| `output` | `content_id`, `guess`, both signal scores, `combined_score`, `label` |
| `duration_ms` | wall-clock milliseconds for the whole request |
| `stages` | `validation_ms`, `model_ms`, `style_ms`, `combine_ms` |
| `status` | `decided`, `rejected`, or `under_review` |
| `error` | stable error code, or `null` on success |
| `model` | after the improvement: model name, revision, torch/transformers versions, dtype, device |

Rejections write the same record with `event="rejected"`, the error code in
`error`, and the response explanation in `output`. The 429 handler writes one
too, so a rate-limited request is never visible only as an absence.

**Ten entries pasted from `logs/runs.jsonl`** (produced by `app.py::submit` and
`capstone_eval.py::main`, after the improvement):

```jsonl
{"timestamp": "2026-10-31T05:46:23+00:00", "request_id": "d217d280-fa09-473a-9131-67cc0004d86d", "event": "decision", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c5_t2_c5_lightly edited AI", "input": {"chars": 249, "words": 44, "preview": "Many people are looking for ways to make their daily routines more efficient. A clear plan helps you stay focused, and i", "sha256": "d746ffcdb3332d32f98a466f59d51e9ac5772d406c805dfd7783d4193da3ba5f"}, "output": {"content_id": "4125fec8-9d59-420d-8ecb-660cfd30ba90", "guess": "ai", "model_score": 0.8293, "style_score": 0.5252, "combined_score": 0.67725, "label": "The combined scores fall in an AI-like range. This is not proof of AI authorship; independent review or relevant drafting context could change the result."}, "duration_ms": 74.622, "stages": {"validation_ms": 0.002, "model_ms": 74.398, "style_ms": 0.201, "combine_ms": 0.021}, "status": "decided", "error": null, "model": {"name": "gpt2", "revision": "607a30d783dfa663caf39e06633721c8d4cfcd7e", "torch": "2.14.1+cpu", "transformers": "4.57.6", "dtype": "torch.float32", "device": "cpu"}}
{"timestamp": "2026-10-31T05:46:23+00:00", "request_id": "6029b3cf-858e-45ce-bbb2-54068f6955e1", "event": "decision", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c5_t2_c5_clearly AI", "input": {"chars": 393, "words": 52, "preview": "Artificial intelligence is transforming the way organizations operate. It enables businesses to automate repetitive task", "sha256": "e1a3b2157e5356a04aea24afbc2bc50c8862c79b5d59043a229b3429707b5aa2"}, "output": {"content_id": "c6cd6c40-b32c-43de-9761-b6069c88a8ee", "guess": "ai", "model_score": 0.8012, "style_score": 0.5626, "combined_score": 0.6819, "label": "The combined scores fall in an AI-like range. This is not proof of AI authorship; independent review or relevant drafting context could change the result."}, "duration_ms": 84.309, "stages": {"validation_ms": 0.002, "model_ms": 84.085, "style_ms": 0.2, "combine_ms": 0.022}, "status": "decided", "error": null, "model": {"name": "gpt2", "revision": "607a30d783dfa663caf39e06633721c8d4cfcd7e", "torch": "2.14.1+cpu", "transformers": "4.57.6", "dtype": "torch.float32", "device": "cpu"}}
{"timestamp": "2026-10-31T05:46:23+00:00", "request_id": "a150c1c9-bbd5-452d-90f8-aa4ac0b1651e", "event": "decision", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c5_t3_c5_human-style control", "input": {"chars": 272, "words": 48, "preview": "Oh, what a morning! I missed the bus. Again. A cyclist splashed straight through a puddle; my coffee went flying, and so", "sha256": "60395c6c8afbd9e338c2357f21e746970ea080cfdc4128c0799e698a6d439f9a"}, "output": {"content_id": "4c7811f2-df91-4c36-8bd8-4d44c3f769f6", "guess": "unsure", "model_score": 0.3997, "style_score": 0.374, "combined_score": 0.38685, "label": "The signals do not support a clear authorship label. This is not an accusation; a fuller sample or independent review could change the result."}, "duration_ms": 84.304, "stages": {"validation_ms": 0.003, "model_ms": 84.076, "style_ms": 0.202, "combine_ms": 0.022}, "status": "decided", "error": null, "model": {"name": "gpt2", "revision": "607a30d783dfa663caf39e06633721c8d4cfcd7e", "torch": "2.14.1+cpu", "transformers": "4.57.6", "dtype": "torch.float32", "device": "cpu"}}
{"timestamp": "2026-10-31T05:46:23+00:00", "request_id": "43d023bd-8cfd-4013-9f9d-33fb9f7a5117", "event": "decision", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c5_t3_c5_lightly edited AI", "input": {"chars": 249, "words": 44, "preview": "Many people are looking for ways to make their daily routines more efficient. A clear plan helps you stay focused, and i", "sha256": "d746ffcdb3332d32f98a466f59d51e9ac5772d406c805dfd7783d4193da3ba5f"}, "output": {"content_id": "b5f7691e-3fa3-44af-8e29-9433aa137ee0", "guess": "ai", "model_score": 0.8293, "style_score": 0.5252, "combined_score": 0.67725, "label": "The combined scores fall in an AI-like range. This is not proof of AI authorship; independent review or relevant drafting context could change the result."}, "duration_ms": 72.048, "stages": {"validation_ms": 0.002, "model_ms": 71.833, "style_ms": 0.191, "combine_ms": 0.022}, "status": "decided", "error": null, "model": {"name": "gpt2", "revision": "607a30d783dfa663caf39e06633721c8d4cfcd7e", "torch": "2.14.1+cpu", "transformers": "4.57.6", "dtype": "torch.float32", "device": "cpu"}}
{"timestamp": "2026-10-31T05:46:23+00:00", "request_id": "45f125d3-0482-45a3-99de-19cf5169bc4d", "event": "decision", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c5_t3_c5_clearly AI", "input": {"chars": 393, "words": 52, "preview": "Artificial intelligence is transforming the way organizations operate. It enables businesses to automate repetitive task", "sha256": "e1a3b2157e5356a04aea24afbc2bc50c8862c79b5d59043a229b3429707b5aa2"}, "output": {"content_id": "29199d3a-7d42-4727-921e-40645ebd893a", "guess": "ai", "model_score": 0.8012, "style_score": 0.5626, "combined_score": 0.6819, "label": "The combined scores fall in an AI-like range. This is not proof of AI authorship; independent review or relevant drafting context could change the result."}, "duration_ms": 75.717, "stages": {"validation_ms": 0.003, "model_ms": 75.499, "style_ms": 0.192, "combine_ms": 0.023}, "status": "decided", "error": null, "model": {"name": "gpt2", "revision": "607a30d783dfa663caf39e06633721c8d4cfcd7e", "torch": "2.14.1+cpu", "transformers": "4.57.6", "dtype": "torch.float32", "device": "cpu"}}
{"timestamp": "2026-10-31T05:46:21+00:00", "request_id": "602ee7e0-7eb5-4d7d-a9c9-d5d03fd071b8", "event": "rejected", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c3_t3_c3_flood", "input": {"chars": 272, "words": 48, "preview": "Oh, what a morning! I missed the bus. Again. A cyclist splashed straight through a puddle; my coffee went flying, and so"}, "output": {"error": "rate_limited", "limit": "10 per 1 minute"}, "duration_ms": 0.472, "stages": {"limiter_ms": 0.4723999882116914}, "status": "rejected", "error": "rate_limited"}
{"timestamp": "2026-10-31T05:46:21+00:00", "request_id": "7134bbc3-5a1f-4403-91ad-859dcdcd54dc", "event": "rejected", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c3_t3_c3_missing", "input": {"chars": null, "words": null, "preview": null, "body_type": "dict"}, "output": {"error": "missing_text", "message": "No text provided."}, "duration_ms": 0.002, "stages": {"validation_ms": 0.002}, "status": "rejected", "error": "missing_text"}
{"timestamp": "2026-10-31T05:46:21+00:00", "request_id": "2aef4d31-fdf1-44fd-aabe-cea6aa4a9f6f", "event": "rejected", "endpoint": "/submit", "creator_id": "unknown", "input": {"chars": null, "words": null, "preview": null, "body_type": "NoneType"}, "output": {"error": "invalid_json", "message": "Request body must be a JSON object."}, "duration_ms": 0.002, "stages": {"validation_ms": 0.002}, "status": "rejected", "error": "invalid_json"}
{"timestamp": "2026-10-31T05:46:21+00:00", "request_id": "0517b186-b654-485f-b005-68067c3e020f", "event": "rejected", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c3_t3_c3_large", "input": {"chars": 12505, "words": 2501, "preview": "word word word word word word word word word word word word word word word word word word word word word word word word "}, "output": {"error": "text_too_large", "message": "Input exceeds the limit of 10,000 characters."}, "duration_ms": 0.008, "stages": {"validation_ms": 0.008}, "status": "rejected", "error": "text_too_large"}
{"timestamp": "2026-10-31T05:46:22+00:00", "request_id": "e186e4e9-9123-4c31-84cc-e6c8bcf0032a", "event": "rejected", "endpoint": "/submit", "creator_id": "capstone_after_20261031_014606_c4_t3_c4_bad", "input": {"chars": 0, "words": 0, "preview": ""}, "output": {"error": "empty_text", "message": "Input is empty."}, "duration_ms": 0.002, "stages": {"validation_ms": 0.002}, "status": "rejected", "error": "empty_text"}
```

## What It Costs

The real cost is **local CPU compute**, not API spend. `benchmark.py` sends one
warm-up request (which loads the model once), then ten measured `/submit`
requests, reads their `duration_ms` back from `GET /runs`, and writes
`results/cost_<date>.md`.

- Baseline measurement: **0.077 s of compute per warm run** (median 76 ms,
  fastest 72 ms, slowest 84 ms over ten runs).
- After the improvement: **0.073 s per warm run** (median 73 ms, fastest 70 ms,
  slowest 78 ms).
- API spend: **$0.00 per run** — the model runs locally and no hosted API is
  called.
- Cold start: the first request after a restart took **6.31 s** while GPT-2
  loaded. That is a one-time startup cost, not a per-run cost.

**Hundred-a-day arithmetic:** at 0.073 s per run, `100 × 0.073 = 7.3 s` of
compute per day, or about 0.12 minutes (0.002 hours). If the process restarts
once that day, add one 6.31 s cold start, for about 13.6 s total. API spend
remains $0.00.

## Run Log and Verdicts

`capstone_eval.py --label before` ran the five criteria three times each.
Complete evidence:
[`results/capstone_before_20261031_014442.md`](./results/capstone_before_20261031_014442.md)
and
[`results/capstone_before_20261031_014442.json`](./results/capstone_before_20261031_014442.json).

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Structured log completeness | 10/10 complete records | 10/10 | 10/10 | 10/10 | **MET** |
| 2. Warm latency | 9/10 under 5,000 ms | 10/10 (max 110.5 ms) | 10/10 (max 99.3 ms) | 10/10 (max 116.2 ms) | **MET** |
| 3. Failure observability | 5/5 failures 4xx/503 and logged | 5/5 | 5/5 | 5/5 | **MET** |
| 4. Metrics accuracy | exact counts; average within 0.001 s | counts exact; Δ 0.000042 s | counts exact; Δ 0.000027 s | counts exact; Δ 0.000045 s | **MET** |
| 5. Regression and label coverage | 3/3 shape; all three labels | 3/3 shape, 2 labels | 3/3 shape, 2 labels | 3/3 shape, 2 labels | **MISSED** |

Only criterion 5 is missed, so it is the only one with a diagnosis.

**Real output for each criterion** — from `results/capstone_before_20261031_014442.md`,
produced by `capstone_eval.py::main`, trial 1 unless noted.

Criterion 1 — completeness summary and one checked record:

```json
{"trial": 1, "expected": 10, "found": 10, "complete": 10, "pass": true}
{"request_id": "5a3f8980-f4df-455d-8484-6bbebf79cdf1", "creator_id": "capstone_before_20261031_014430_c1_t1_c1_1", "complete": true, "missing": []}
```

Criterion 2 — ten client-side end-to-end latencies, all under 5,000 ms:

```json
{"trial": 1, "under_5000": 10, "latencies_ms": [86.178, 93.204, 88.526, 92.326, 85.23, 88.374, 85.06, 110.477, 90.633, 94.803], "median_ms": 89.579, "max_ms": 110.477, "pass": true}
```

Criterion 3 — every deliberate failure returned 4xx and was logged:

```json
{"trial": 1, "passed": 5, "checks": [
  {"case": "rate_limited", "status": 429, "status_ok": true, "logged": true, "log_error": "rate_limited", "log_request_id": "cdf02bfd-3e45-4394-ac5a-3d1f2e773bde", "log_duration_ms": 1.143},
  {"case": "missing_text", "status": 400, "status_ok": true, "logged": true, "log_error": "missing_text", "log_request_id": "f6ae8e65-6d17-4c38-9342-1c2582ecf293", "log_duration_ms": 0.002},
  {"case": "empty_text", "status": 400, "status_ok": true, "logged": true, "log_error": "empty_text", "log_request_id": "e2052467-6f5e-4d9f-80bb-c12f1bba8eb1", "log_duration_ms": 0.002},
  {"case": "invalid_json", "status": 400, "status_ok": true, "logged": true, "log_error": "invalid_json", "log_request_id": "c36d5034-1ca1-4edf-9634-d10e77a8e522", "log_duration_ms": 0.001},
  {"case": "text_too_large", "status": 400, "status_ok": true, "logged": true, "log_error": "text_too_large", "log_request_id": "e9fbc031-946e-436f-902c-03f11dd601e7", "log_duration_ms": 0.007}
]}
```

Criterion 4 — `/metrics` agrees with `/runs`:

```json
{"trial": 1, "metrics": {"total_runs": 135, "decisions": 119, "rejections": 16, "compute_seconds_per_decision": 0.1363}, "run_counts": {"total_runs": 135, "decisions": 119, "rejections": 16}, "reported_average_seconds": 0.1363, "expected_average_seconds": 0.136258, "average_delta_seconds": 4.2e-05, "pass": true}
```

Criterion 5 — all six fields present, but only two labels:

```json
{"trial": 1, "rows": [
  {"input": "human-style control", "status": 200, "guess": "unsure", "model_score": 0.3997, "style_score": 0.374, "combined_score": 0.38685},
  {"input": "lightly edited AI", "status": 200, "guess": "ai", "model_score": 0.8293, "style_score": 0.5252, "combined_score": 0.67725},
  {"input": "clearly AI", "status": 200, "guess": "ai", "model_score": 0.8012, "style_score": 0.5626, "combined_score": 0.6819}
], "labels_seen": ["ai", "unsure"], "shape_ok": true, "coverage_ok": false, "pass": false}
```

**Diagnosis of the miss — criterion 5.** Stage: `detector.model_signal` feeding
`scoring.combine_signals`, then `scoring.score_to_label`. Mechanism: the
human-style control scored `0.3997` on the model signal, not the `0.3209`
recorded in the Unit 7 README. Its style score was `0.374`, so the equal-weight
average was `0.38685` — `0.03685` above `HUMAN_THRESHOLD = 0.35`. The label
mapper therefore returned `unsure`. The two AI texts both returned `ai`, so the
trial saw only two of the three labels. Every response had all six fields and
HTTP 200, so this is not an instrumentation or route regression; it is a
calibration-boundary miss. The pattern is a single miss at the model-signal
boundary, not three separate failures.

## The Improvement

**What I changed:** Added `detector.model_metadata()` and recorded it, plus an
input SHA-256, on every successful decision. Each record now names the model
(`gpt2`), the exact model revision
(`607a30d783dfa663caf39e06633721c8d4cfcd7e`), `torch` and `transformers`
versions, dtype, and device. Signal calculations, weights, thresholds, routes,
and response fields did not change.

**Which diagnosis pointed at it:** Criterion 5's miss could not be attributed:
the score was `0.3997` where the Unit 7 README recorded `0.3209`, but the log
did not say which model revision or library versions produced either number. A
future run can now be matched to the exact environment, and the input SHA-256
identifies the text that produced a score.

### After the improvement — same five criteria, three trials

Complete evidence:
[`results/capstone_after_20261031_014623.md`](./results/capstone_after_20261031_014623.md)
and
[`results/capstone_after_20261031_014623.json`](./results/capstone_after_20261031_014623.json).

| Criterion | Before (T1 / T2 / T3) | After (T1 / T2 / T3) | Before verdict | After verdict |
|---|---|---|---|---|
| 1. Log completeness | 10/10 / 10/10 / 10/10 | 10/10 / 10/10 / 10/10 | MET | MET |
| 2. Warm latency | 10/10 / 10/10 / 10/10 under 5s | 10/10 / 10/10 / 10/10 under 5s | MET | MET |
| 3. Failure observability | 5/5 / 5/5 / 5/5 | 5/5 / 5/5 / 5/5 | MET | MET |
| 4. Metrics accuracy | exact / exact / exact (Δ ≤ 4.5e-5 s) | exact / exact / exact (Δ ≤ 3.5e-5 s) | MET | MET |
| 5. Regression and labels | 3/3 shape, 2 labels each | 3/3 shape, 2 labels each | MISSED | MISSED |

The after run used
[`results/cost_20261031_014632_capstone-after.md`](./results/cost_20261031_014632_capstone-after.md):
0.073 s per warm run versus 0.077 s before, so the added fingerprint did not
make a measurable cost difference.

**Did it help, and how do I know:** It did **not** change criterion 5's verdict
or any score — the human-style control still returns `0.3997 / 0.374 / 0.38685`
and `unsure`. It helped the diagnosis, not the behaviour: the after log now
names the exact model revision and runtime that produced the score, so the
calibration drift can be investigated instead of guessed at. The trade is a
slightly larger record (the `model` object and input hash), which did not show
up in the measured per-run latency.

## What's Still Broken

**Criterion 5 — human-label coverage (still missed).** The system's label bands
are reachable in principle, but these three calibration texts produce only
`unsure` and `ai` in this runtime. What I would do: re-measure the three
calibration texts on the exact target runtime, store the model fingerprint and
the resulting scores as the reference, then decide whether the model signal's
perplexity midpoint or the `HUMAN_THRESHOLD` needs recalibration. I stopped
because threshold/midpoint recalibration was explicitly out of scope for this
unit, and changing the calibration inputs would be changing the test rather
than fixing the system.

**The one thing I would do first if this were real and I had another unit:**
capture a controlled calibration run on the deployment machine and compare it
with the Unit 7 table, using the new fingerprint to separate environment drift
from a code change. That one measurement decides whether the fix belongs in the
detector's midpoint, the label threshold, or the documented calibration set;
without it, any of those changes would be a guess. The clean-checkout test
already found one concrete source of drift: a fresh install resolved
`torch 2.15.0+cpu` while the evidence environment runs `torch 2.14.1+cpu`
because `requirements.txt` bounds torch without pinning the exact build.

## How I Used AI (capstone)

**Moment 1 — criteria review.** I asked AI to review the five drafted criteria
as if it could not ask me what I meant. It flagged that criterion 5 required all
three labels from three specific calibration texts and could fail if two of
them landed in the same band. I kept the criterion because it was the honest
regression check, and the first run then missed it exactly that way. I did not
let the model rewrite the target.

**Moment 2 — cost measurement.** I asked AI to inspect the first cost report
against the run log. It noticed the report averaged eleven rows, including the
warm-up, so the 6.3 s model load was being counted as a per-run cost. I changed
`benchmark.py` to exclude the warm-up creator, re-ran ten measured requests,
and used the corrected 0.077 s figure.

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

# Previous units — Provenance Guard (Units 7–8)

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

1. A reader's client sends `POST /submit` with the text and a `creator_id`.
   The route parses the JSON and checks that it contains usable input.
2. The route assigns a `content_id` so this submission can be identified later,
   including if its writer appeals.
3. `detector.model_signal` scores how predictable the text is to the local
   language model. It adds a 0–1 model score; higher means more AI-like.
4. `stylometry.style_signal` measures sentence-length spread, vocabulary
   repetition, and punctuation patterns without interpreting the text. It adds
   a separate 0–1 style score; higher also means more AI-like.
5. `scoring.combine_signals` combines the two scores into one 0–1 score, and
   `scoring.score_to_label` maps that score to `ai`, `human`, or `unsure` and a
   sentence intended for the reader.
6. The route appends the decision, both signal scores, combined score, label,
   and identifiers to the audit log. This preserves what was decided and makes
   a later appeal traceable.
7. The route returns JSON with the `content_id`, scores, guess, and reader-facing
   label; the client displays that label. A writer can send the `content_id` and
   their reasoning to `POST /appeal`, which records the appeal for review.

`POST /submit` returns and logs both signal scores, the combined score, the
machine-readable guess, and the reader-facing label. `confidence` remains
`0.0` as a placeholder; it is not a confidence estimate. A writer can appeal a
decision through `POST /appeal`, which appends an `under_review` entry without
replacing the original decision.

### Endpoint contracts

Requests use a JSON object with `Content-Type: application/json`.

#### `POST /submit`

**Request fields**

| Field | Type | Meaning |
|---|---|---|
| `text` | string | The text to score; must contain non-whitespace text long enough for the detector and be at most 10,000 characters. |
| `creator_id` | string | Identifier for the submitting writer; used to associate the decision and any appeal. |

**Successful response (`200`)**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | Unique identifier for this submission, returned for future appeals. |
| `guess` | string | Machine-readable category: `human`, `unsure`, or `ai`. |
| `confidence` | number | Placeholder (`0.0`); not a confidence estimate. |
| `label` | string | Full reader-facing sentence for the selected category. |
| `model_score` | number, 0–1 | Predictability-based model signal; higher means more AI-like. |
| `style_score` | number, 0–1 | Shape-based style signal; higher means more AI-like. |
| `combined_score` | number, 0–1 | Equal-weight average of `model_score` and `style_score`. |

Missing text returns `400` with “No text provided.”, empty text returns `400`
with “Input is empty.”, and text longer than 10,000 characters returns `400`
with “Input exceeds the limit of 10,000 characters.” Other malformed or
invalid input and text too short to score also return `400` with a stable error
code and explanation. If the local detector cannot load, the route returns
`503` rather than manufacturing a score. Rejections are recorded separately;
they do not create a decision entry. The `guess` and reader-facing `label` are
populated for every successful submission.

#### `POST /appeal`

**Request fields**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | The identifier returned by `/submit`. |
| `reasoning` | string | The writer's explanation of why the decision should be reviewed. |

**Successful response (`200`)**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | The submission whose decision is under review. |
| `status` | string | `under_review` after the appeal is recorded. |
| `message` | string | Confirmation that the appeal was received, not that the label has been changed. |

Missing or invalid fields should return `400` with the error shape above; an
unknown `content_id` should return `404`. The appeal record is appended beside
the original decision, not substituted for it. The route looks up the original
decision to associate the appeal with its `creator_id`.

### Following a false positive

Consider a real writer who uses plain, conventional sentences. Predictable
wording can give them a high model score even though they wrote the work. For
an illustrative trace, suppose the model score is `0.90` and the style score
is `0.50`. With equal weights,
the combined score is `(0.5 × 0.90) + (0.5 × 0.50) = 0.70`. That is above the
current `AI_THRESHOLD` of `0.65`, so the label is `ai` and the reader
sees: “Our signals suggest this text may have been written with AI, but this
is not proof.”

Those scores are an example, not an observed model run; the weights and
thresholds remain settings to be revisited after calibration. The harm is
still clear: a human
writer receives an AI accusation from a signal that measures predictability,
not authorship. The response must include a `content_id`; the writer can submit
it with their reasoning to `/appeal`. The service records the appeal as
`under_review` without erasing the original result, so a person can review it.


---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** `detector.model_signal` uses local GPT-2 perplexity as a
measure of how predictable the text is to that model. Low perplexity maps to a
higher 0–1 AI-likelihood score.

**Why that might differ between human and AI writing:** A language model tends
to produce likely next words, so generated text may be easy for a similar model
to predict. Human writing can be less predictable because of unusual choices
and unexpected turns.

**What it can't see:** It cannot establish who wrote the text or understand
authorship. A person writing plainly, using common words, or writing in a
second language can look predictable; ornate or unusual human writing can look
surprising. Predictability is not proof of AI authorship.

### Signal two — the style signal

**What it measures:** `stylometry.style_signal` measures sentence-length
variation, unique words relative to total words, and punctuation density. It
looks at the text's form, not its meaning.

**How it is scored:** Sentence-length spread is the sample standard deviation
of sentence word counts divided by their mean (coefficient of variation);
fewer than two usable sentences give a neutral spread component of `0.50`.
Vocabulary repetition is `1 - type_token_ratio`. Punctuation density is
Unicode punctuation characters divided by all characters; its component is
`1 - min(density / 0.10, 1.0)`. `style_signal` is the equal average of these
three components, rounded to four decimals. Text with no words receives the
neutral style score `0.50`. These directions are rough heuristics, not
authorship evidence; in particular, type-token ratio is sensitive to length.

**Why that might differ between human and AI writing:** Generated prose can
settle into similarly sized sentences, repeat familiar vocabulary, and use
punctuation in regular ways. Human writing may be more uneven and idiosyncratic.

**What it can't see:** It cannot read or interpret the text, verify its
author, or tell meaningful variation from noise. Typos, inserted punctuation,
or a quotation can change its measurements without changing who wrote the
surrounding text. Its vocabulary ratio also changes with text length.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:** Take an equal-weight average of the model and style scores.
Disagreement pulls the result toward `0.50`; it does not let either signal
alone make the decision.

**The numbers:** `WEIGHT_MODEL_SIGNAL = 0.50` and
`WEIGHT_STYLE_SIGNAL = 0.50` in `config.py`. For example, scores `0.90` and
`0.10` combine to `0.50`. The separate label-band thresholds remain
`HUMAN_THRESHOLD = 0.35` and `AI_THRESHOLD = 0.65` in `config.py`.

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:** For the
lightly edited AI sample, the model score was `0.7467` (above the `0.65` AI
threshold), while the style score was `0.5252` (below it). The equal average,
`0.6360`, lands in the unsure band instead of treating the model score alone
as proof.

### Calibration run

Run the same four text types through `detector.model_signal` and
`stylometry.style_signal`, then calculate the configured average. The first
three are the shared comparison set (AI-like, human-style, and lightly edited
AI-like); formal human-style writing is the fourth stress case. The human-style
examples are constructed controls, not independently verified human
authorship. These scores are calibration observations, not a validated
detector benchmark.

| Input | Model score | Style score | Combined score | Observation |
|---|---:|---:|---:|---|
| Clearly AI | 0.8012 | 0.5626 | 0.6819 | Both point above the AI threshold after averaging. |
| Human-style control | 0.3209 | 0.3740 | 0.3475 | Both are low; combined score is just below the human threshold. |
| Lightly edited AI | 0.7467 | 0.5252 | 0.6360 | Model alone crosses the AI threshold; style and combined scores do not. |
| Formal human-style | 0.5705 | 0.6136 | 0.5920 | Both lean high, but the average remains unsure. |

**Where the signals agree or split:** On the clearly AI and human-style
examples, both signals land on the same side of `0.50`. The lightly edited AI
sample is the split case: the model score is above `AI_THRESHOLD = 0.65`, while
the style score is below it. The formal human-style sample is also a false-
positive risk: both scores are above `0.50`.

**What the disagreement case demonstrates:** Equal weighting moves the
lightly edited AI sample from a model-only AI result (`0.7467`) to an unsure
combined result (`0.6360`). The style signal can temper an accusation, but it
can also let edited AI text avoid a high-confidence AI label.

**Calibration inputs** (run verbatim to reproduce the table):

- Clearly AI: “Artificial intelligence is transforming the way organizations
  operate. It enables businesses to automate repetitive tasks, analyze large
  amounts of data, and improve decision-making. As these technologies continue
  to advance, organizations must consider both their opportunities and their
  potential challenges. A thoughtful approach can help ensure that AI is used
  effectively and responsibly.”
- Human-style control: “Oh, what a morning! I missed the bus. Again. A cyclist
  splashed straight through a puddle; my coffee went flying, and somewhere in
  all that chaos a tiny dog stole half my muffin. Honestly, I laughed—there
  wasn't much else to do. By noon, everything had somehow worked out.”
- Lightly edited AI: “Many people are looking for ways to make their daily
  routines more efficient. A clear plan helps you stay focused, and it can
  also save time. In the end, small changes usually make the biggest
  difference—at least, that is what I keep telling myself.”
- Formal human-style: “The committee reviewed the proposed schedule and
  considered the effects on staffing, cost, and access. Although the revised
  plan requires additional preparation, it gives each department more time to
  respond. Members agreed that the change should be evaluated after the first
  quarter, when reliable figures are available.”



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 ≤ score ≤ 0.35 | Our signals suggest this text was probably written by a person. |
| unsure | 0.35 < score < 0.65 | We can't tell from these signals whether this text was written by a person or with AI. |
| high-confidence AI | 0.65 ≤ score ≤ 1.00 | Our signals suggest this text may have been written with AI, but this is not proof. |

**Why I worded the "unsure" one this way:**
It says plainly that the signals cannot tell, and it does not accuse the writer
of using AI. That matters because a person may have written every word
themselves.

**Live-model reachability check**

These are actual `POST /submit` results from the local model using the
calibration examples above. Each score produced the category shown:

| Example | Combined score | Guess |
|---|---:|---|
| Human-style control | 0.34745 | `human` |
| Lightly edited AI | 0.63595 | `unsure` |
| Clearly AI | 0.68190 | `ai` |



---

## Sample Run

The following submission, appeal, and log lookup were captured with the live
local model through a Flask test client and temporary audit-log storage. The
`content_id` was returned by the submission immediately before the appeal.

**A submission**

Request to `POST /submit`:

```json
{
  "text": "Oh, what a morning! I missed the bus. Again. A cyclist splashed straight through a puddle; my coffee went flying, and somewhere in all that chaos a tiny dog stole half my muffin. Honestly, I laughed—there wasn't much else to do. By noon, everything had somehow worked out.",
  "creator_id": "milestone5-sample"
}
```

Response (`200`):

```json
{
  "combined_score": 0.34745000000000004,
  "confidence": 0.0,
  "content_id": "51926f77-a8f5-46b8-8c6b-6d0e30f5b2b5",
  "guess": "human",
  "label": "Our signals suggest this text was probably written by a person.",
  "model_score": 0.3209,
  "style_score": 0.374
}
```

**An appeal for that submission**

Request to `POST /appeal`:

```json
{
  "content_id": "51926f77-a8f5-46b8-8c6b-6d0e30f5b2b5",
  "reasoning": "I wrote this text myself and would like a person to review the decision."
}
```

Response (`200`):

```json
{
  "content_id": "51926f77-a8f5-46b8-8c6b-6d0e30f5b2b5",
  "message": "Your appeal has been received for review.",
  "status": "under_review"
}
```

**`GET /log?limit=2` afterwards** (`200`):

```json
{
  "count": 2,
  "entries": [
    {
      "combined_score": 0.34745000000000004,
      "content_id": "51926f77-a8f5-46b8-8c6b-6d0e30f5b2b5",
      "creator_id": "milestone5-sample",
      "guess": "human",
      "label": "Our signals suggest this text was probably written by a person.",
      "model_score": 0.3209,
      "status": "decided",
      "style_score": 0.374,
      "timestamp": "2026-10-12T23:14:12+00:00"
    },
    {
      "content_id": "51926f77-a8f5-46b8-8c6b-6d0e30f5b2b5",
      "creator_id": "milestone5-sample",
      "event": "appeal",
      "reasoning": "I wrote this text myself and would like a person to review the decision.",
      "status": "under_review",
      "timestamp": "2026-10-12T23:14:12+00:00"
    }
  ]
}
```

---

## How I Used AI

**Moment 1**

- *What I asked for:* I asked AI to compare my Unit 7 submission checklist
  with the repository before making changes.
- *What came back:* It found that the submission flow, combining rule, label
  variants, and sample run were already documented, while this AI-use section
  still had placeholders. It also noticed that the separate Unit 8 sections
  were still blank.
- *What I changed:* I left the completed Unit 7 write-ups intact, filled in
  the missing AI-use section, and kept the Unit 8 template for its own
  milestone.

**Moment 2**

- *What I asked for:* I asked AI to check the documented combining rule
  against the scoring code and calibration example.
- *What came back:* It verified that `scoring.py::combine_signals` takes the
  equal-weight average configured in `config.py`; the model/style scores
  `0.7467` and `0.5252` therefore combine to `0.6360`, in the unsure band.
- *What I changed:* I kept the README's code reference, weights, thresholds,
  and calibration figures aligned with the implementation, and described the
  result as uncertainty rather than proof of authorship.

**Moment 3 — Unit 8**

- *What I asked for:* I asked AI to compare the existing run artifacts and README against the
  Milestone 6 requirements, then help make verdicts and limitations explicit.
- *What came back:* It identified blank report verdict tables, blank attack marks, and a
  “What's Still Broken” section without a next step for each failure.
- *What I changed:* I filled the summaries from committed evidence, added synthetic-only caveats,
  and reviewed each held/broke judgment against the recorded response. I did not add human-writing
  or reader-study results that were not collected.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 10 per minute, 200 per day

**Why those numbers and not others:**
Ten submissions per minute leaves room for a writer to revise and resubmit
quickly, while 200 per day supports sustained legitimate use. The per-minute
limit stops a rapid script from mapping the thresholds; the daily cap limits
continued probing over time.

**What a caller counts as:** requests share a bucket by `creator_id`; if it is
missing or invalid, the limiter falls back to the remote address. Since a
client can choose its `creator_id`, rotating IDs can evade this local
per-creator limit.

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

The flood test recorded 10 decisions and 5 `rate_limited` rejections in
`/log`; `/health` reported `rate_limiting: true`.

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --set attack_sets/synthetic_m5 --label before`. -->

The earlier rate-limit flood is recorded in
[`results/flood_2026-10-13_0729.md`](./results/flood_2026-10-13_0729.md): ten
requests returned 200, then five returned 429. The provenance run uses the explicitly synthetic eight-row set in
`attack_sets/synthetic_m5`. The complete run is
[`results/attack_run_2026-10-13_0929_before.md`](./results/attack_run_2026-10-13_0929_before.md).
Five scoreable submissions returned 200; three malformed requests returned
400; none crashed or returned 5xx. The five guesses were `unsure`, `unsure`,
`unsure`, `ai`, `unsure`, in that order. All eight verdicts below are judgments
against their synthetic targets. `confidence` in the harness
is a placeholder, so the combined scores come from the corresponding audit
entries and report JSON. The false-positive proxies are not authenticated
human writing, and the evasion/baseline inputs have no verified authorship.

| ID | Outcome | Verdict |
|---|---|---|
| FP01 | `200`, unsure, combined score 0.4810 | HELD — no AI accusation |
| FP02 | `200`, unsure, combined score 0.5713 | HELD — no AI accusation |
| EV01 | `200`, unsure, combined score 0.4925 | BROKE — remained below the expected AI label |
| EV02 | `200`, ai, combined score 0.6548 | HELD — crossed the AI threshold |
| AI01 | `200`, unsure, combined score 0.5773 | BROKE — baseline probe remained unsure |
| MR01 | `400`, missing `text` | HELD — rejected at route |
| MR02 | `400`, JSON array instead of object | HELD — rejected at route |
| MR03 | `400`, invalid JSON | HELD — rejected at route |

**Ten audit log entries from the baseline run**

These are the five scoring requests, three malformed-request rejections, and
the first two bad-input rejections from the three-trial evaluation. Full
before/after request evidence is in the linked reports.

```jsonl
{"timestamp":"2026-10-13T13:29:52+00:00","content_id":"e8b26ff3-ab6f-4b6e-80c4-7f5e2a9f95a6","creator_id":"attacker_FP01","guess":"unsure","model_score":0.4611,"style_score":0.5009,"combined_score":0.481,"label":"We can't tell from these signals whether this text was written by a person or with AI.","status":"decided"}
{"timestamp":"2026-10-13T13:29:52+00:00","content_id":"8771f0b1-7cb5-4808-9878-b090118c7621","creator_id":"attacker_FP02","guess":"unsure","model_score":0.6407,"style_score":0.5018,"combined_score":0.57125,"label":"We can't tell from these signals whether this text was written by a person or with AI.","status":"decided"}
{"timestamp":"2026-10-13T13:29:52+00:00","content_id":"c8879b4e-45db-44c1-bbc1-08a70d527ae0","creator_id":"attacker_EV01","guess":"unsure","model_score":0.4166,"style_score":0.5683,"combined_score":0.49245000000000005,"label":"We can't tell from these signals whether this text was written by a person or with AI.","status":"decided"}
{"timestamp":"2026-10-13T13:29:52+00:00","content_id":"58925ba0-a739-4583-9e3d-b9151fed11b2","creator_id":"attacker_EV02","guess":"ai","model_score":0.7073,"style_score":0.6023,"combined_score":0.6548,"label":"Our signals suggest this text may have been written with AI, but this is not proof.","status":"decided"}
{"timestamp":"2026-10-13T13:29:52+00:00","content_id":"ce522a68-52bf-4bb5-aacc-90fcf17515f9","creator_id":"attacker_AI01","guess":"unsure","model_score":0.644,"style_score":0.5106,"combined_score":0.5773,"label":"We can't tell from these signals whether this text was written by a person or with AI.","status":"decided"}
{"timestamp":"2026-10-13T13:29:52+00:00","creator_id":"attack_missing_text","event":"rejected","status":"rejected","reason":"missing_text","error":"missing_text"}
{"timestamp":"2026-10-13T13:29:52+00:00","creator_id":"unknown","event":"rejected","status":"rejected","reason":"invalid_json","error":"invalid_json"}
{"timestamp":"2026-10-13T13:29:52+00:00","creator_id":"unknown","event":"rejected","status":"rejected","reason":"invalid_json","error":"invalid_json"}
{"timestamp":"2026-10-13T13:29:58+00:00","creator_id":"eval_bad_empty","event":"rejected","status":"rejected","reason":"empty_text","error":"empty_text"}
{"timestamp":"2026-10-13T13:29:58+00:00","creator_id":"eval_bad_missing","event":"rejected","status":"rejected","reason":"missing_text","error":"missing_text"}
```

**Attack diagnosis:** FP01 and FP02 were held at the combining/label-mapping
stage: their combined scores (0.4810 and 0.5713) remained in the unsure band,
below the 0.65 AI threshold. EV01 broke through the intended evasion check:
its model/style scores (0.4166 and 0.5683) averaged to 0.4925, so it mapped to
unsure instead of the expected AI label. EV02's scores (0.7073 and 0.6023)
averaged to 0.6548, just over the AI threshold. AI01 broke the baseline probe
at the same combining/label-mapping stage: its scores (0.6440 and 0.5106)
averaged to 0.5773 and remained unsure. MR01–MR03 were held by route
validation before either signal ran.
Because the content's true authorship is unknown, these marks describe
observed outputs against the stated synthetic expectations, not confirmed
authorship attacks.

---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

`run_eval.py --label before` and `run_eval.py --label after` each ran the five
scenarios three times. The complete JSON evidence is in
[`results/run_2026-10-13_0929_before.md`](./results/run_2026-10-13_0929_before.md)
and [`results/run_2026-10-13_0930_after.md`](./results/run_2026-10-13_0930_after.md).
The table gives each scenario's three outputs per trial; each text scenario
contained three synthetic inputs. These runs do not meet the original sample
sizes or authenticity requirements.

| Criterion / scenario | Before: Trials 1 / 2 / 3 | After: Trials 1 / 2 / 3 | Assessment |
|---|---|---|---|
| 1. False positives — synthetic human-like prose proxy | `unsure, unsure, unsure` / same / same | `unsure, unsure, unsure` / same / same | **UNVERIFIED** — 3 synthetic proxies per trial, not 100 authenticated human samples. No proxy received an `ai` label, but this is not a measured false-positive rate. |
| 2. Factuality — synthetic factual-claim examples | `unsure, unsure, ai` / same / same | `unsure, unsure, ai` / same / same | **MISSED by implementation** — classification output is not factuality checking or source verification. |
| 3. Bad input — empty, missing, oversized | `400, 400, 400` / same / same | `400, 400, 400` / same / same | **MET for these cases** — all three rejection reasons (`empty_text`, `missing_text`, `text_too_large`) were logged in every trial; no normal result was returned. |
| 4. Fake evidence — synthetic fabricated-citation examples | `human, unsure, unsure` / same / same | `human, unsure, unsure` / same / same | **MISSED by implementation** — the signals classify prose; they do not verify citations or quotations. |
| 5. Explanation quality — synthetic output probes | `ai, unsure, unsure` / same / same | `ai, unsure, unsure` / same / same | **UNVERIFIED** — wording was improved, but no 30-reader comprehension study was conducted. |

Repeated outputs were identical across all three trials. The synthetic set has
only three texts per text scenario and does not establish the 100-sample,
50-case, or 30-reader targets in [criteria.md](./criteria.md).

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->

- **Criterion 2 — factuality (MISSED by implementation inspection).** Stage:
  route / service contract. Mechanism: `/submit` accepts text for authorship
  scoring; it does not extract factual claims or retrieve/check supporting
  sources. Neither signal, the combining rule, nor the label mapping measures
  whether a claim is true.
- **Criterion 4 — fake evidence (MISSED by implementation inspection).** Stage:
  route / service contract. Mechanism: the request path has no citation,
  source-existence, or quote-to-source check, so fabricated evidence is never
  specifically flagged or refused. This is the same missing verification
  capability as criterion 2, not 50 separate signal failures.
- **Criterion 5 — explanation quality (UNVERIFIED).** Stage: label mapping.
  Mechanism: the original `scoring.score_to_label` text named the broad result
  but not a useful next step or a condition that could change it. This wording
  gap was the one chosen for the improvement below. The revised text now names
  the result, cautions that it is not proof, and offers a fuller sample or
  independent review; without 30 reader tests, comprehension remains
  unverified.
- **Recorded flood attack — HELD.** Stage: route limiter, before `/submit`.
  Mechanism: ten requests in the creator's one-minute bucket returned 200;
  the next five returned 429 and were logged as `rate_limited`. This establishes
  the configured limit for this one-creator flood, not resistance to rotating
  creator IDs. The synthetic provenance/evasion results are recorded above but
  are not an authentic attack set.
- **Criterion 1 — false positives (UNVERIFIED).** Three synthetic human-like
  proxies per trial all received `unsure`, not `ai`. They are not authenticated
  human writing and do not satisfy the 100-sample target, so no real-world
  false-positive rate can be inferred.
- **Criterion 3 — bad input (MET for the checked cases).** Stage: route.
  Mechanism: `/submit` checks for missing, empty, and over-limit text before
  calling either signal; the rejection helper returns an error response and
  logs the rejection. The existing audit entries confirm the three rejection
  reasons, while the route contains the criterion's exact messages. No
  remaining miss is evidenced for this criterion.



---

## The Improvement

**What I changed:** Only the three reader-facing strings returned by
`scoring.score_to_label` in [scoring.py](./scoring.py). Each now states what the
scores indicate, cautions that the result is not proof, and identifies a fuller
sample or independent review (or relevant drafting context for the AI-like
band) as something that could change the result. The signal calculations,
weights, thresholds, and route behavior did not change.

**Which diagnosis pointed at it:** Criterion 5's diagnosis above: the label
mapping did not name evidence or a condition that could change a result.

### Attack Run — After

<!-- Same format. `run_attacks.py --set attack_sets/synthetic_m5 --label after` -->

The complete post-change report is
[`results/attack_run_2026-10-13_0930_after.md`](./results/attack_run_2026-10-13_0930_after.md).
Here is the direct comparison; `Score` is the logged combined score (the API's
`confidence` field remains a placeholder).

| Attack | Before: status / guess / score | After: status / guess / score | Difference |
|---|---|---|---|
| FP01 — synthetic plain prose | 200 / `unsure` / 0.4810 | 200 / `unsure` / 0.4810 | HELD both; none |
| FP02 — synthetic everyday prose | 200 / `unsure` / 0.5713 | 200 / `unsure` / 0.5713 | HELD both; none |
| EV01 — typo-heavy prose | 200 / `unsure` / 0.4925 | 200 / `unsure` / 0.4925 | BROKE both; none |
| EV02 — formal prose | 200 / `ai` / 0.6548 | 200 / `ai` / 0.6548 | HELD both; none |
| AI01 — polished generic prose | 200 / `unsure` / 0.5773 | 200 / `unsure` / 0.5773 | BROKE both; none |
| MR01 — missing text | 400 / rejected | 400 / rejected | HELD both; none |
| MR02 — JSON array | 400 / rejected | 400 / rejected | HELD both; none |
| MR03 — invalid JSON | 400 / rejected | 400 / rejected | HELD both; none |

Both runs had zero 5xx/crash outcomes and carry the same operational verdicts
as the baseline table. The three malformed requests were rejected at the route;
the five classification probes have no verified authorship labels.

**Did it help, and how do I know:**

It helped the diagnosed wording gap: labels now state the result is not proof
and give a review/sample condition. It did **not** change any score, guess, or
HTTP outcome in this attack set, and it cannot be said to improve reader
comprehension without the required reader study. The unchanged outputs are the
honest measured result of changing explanation text only.

---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->

The detector still cannot validate factual claims or fabricated citations
(criteria 2 and 4). For criterion 2, I would add claim extraction and a
traceable source/reproducibility check; for criterion 4, I would check that
cited works exist and that quoted text matches the cited source. I stopped
because the existing service only scores authorship and this milestone did
not include building a source-verification pipeline; the current synthetic
claims cannot validate one.

Criterion 1 is still unverified: all three synthetic human-like proxies per
trial landed in `unsure`, but they are not authenticated human writing and do
not meet the 100-sample target. I would collect consented human-written
samples, run the same three-trial evaluation, and measure the false-positive
rate; I stopped because no such labeled writing set was supplied. Criterion 5
is also unverified: the revised explanation names uncertainty, cautions that
the result is not proof, and gives a review/sample condition, but no readers
were tested. I would run the specified 30-reader comprehension study; I
stopped because no participants or study results were available.

Two probes were marked BROKE in both attack runs. EV01 returned `unsure` at
0.4925 rather than the expected AI label; I would test a known-provenance
evasion corpus and then recalibrate the model/style signals and threshold,
but stopped rather than tune against unauthenticated synthetic text. AI01
returned `unsure` at 0.5773; I would test a larger labeled AI baseline set and
evaluate the score boundary, but stopped because this single synthetic probe
cannot justify changing the threshold. These BROKE marks are operational
judgments only: neither input's true authorship was verified. FP01/FP02 and
EV02 were HELD on the observed label criterion, while MR01–MR03 were rejected
at route validation; those outcomes also do not establish broader robustness.

**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->

I would keep the cautious wording and prefer an `unsure` result over an
unsupported high-confidence accusation, while preserving a clear route to
independent review. Writers bear the cost of false accusations; the service
owner bears the cost of more AI-written text remaining unflagged.

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
