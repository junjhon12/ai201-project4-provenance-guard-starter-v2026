# Cost measurement — capstone-after

- Produced by: `benchmark.py::main`
- Service: `http://127.0.0.1:5055` · model `gpt2` (local CPU)
- 10 measured runs after one warm-up · 2026-10-31 01:46
- Cost unit: seconds of local compute per `/submit` decision

## Result

- Average end-to-end: **73 ms** (**0.073 s of compute per run**)
- Median: 73 ms
- Fastest / slowest: 70 / 78 ms
- Total for 10 runs: 0.733 s
- API spend: **$0.00** — the model runs locally; no hosted API is called

## Where the time went

| Stage | Average ms | Share of total |
|---|---:|---:|
| `model_ms` | 73.1 | 99.7% |
| `style_ms` | 0.2 | 0.2% |
| `combine_ms` | 0.0 | 0.0% |
| `validation_ms` | 0.0 | 0.0% |

## Per-run durations

| Run | Duration ms | Model ms | Style ms | Guess |
|---:|---:|---:|---:|---|
| 1 | 76.7 | 76.5 | 0.2 | unsure |
| 2 | 73.0 | 72.8 | 0.2 | unsure |
| 3 | 76.3 | 76.1 | 0.2 | unsure |
| 4 | 69.8 | 69.6 | 0.2 | unsure |
| 5 | 72.0 | 71.8 | 0.2 | unsure |
| 6 | 70.5 | 70.4 | 0.2 | unsure |
| 7 | 77.9 | 77.7 | 0.2 | unsure |
| 8 | 71.2 | 71.0 | 0.2 | unsure |
| 9 | 73.0 | 72.8 | 0.2 | unsure |
| 10 | 72.8 | 72.6 | 0.2 | unsure |

## Hundred-a-day arithmetic

At 0.073 s per run, 100 runs per day is `100 × 0.073 = 7.3 s` of compute per day (about 0.1 minutes, or 0.00 hours). API spend is $0.00 per day.
