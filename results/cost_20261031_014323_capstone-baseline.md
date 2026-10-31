# Cost measurement — capstone-baseline

- Produced by: `benchmark.py::main`
- Service: `http://127.0.0.1:5055` · model `gpt2` (local CPU)
- 10 measured runs after one warm-up · 2026-10-31 01:43
- Cost unit: seconds of local compute per `/submit` decision

## Result

- Average end-to-end: **77 ms** (**0.077 s of compute per run**)
- Median: 76 ms
- Fastest / slowest: 72 / 84 ms
- Total for 10 runs: 0.766 s
- API spend: **$0.00** — the model runs locally; no hosted API is called

## Where the time went

| Stage | Average ms | Share of total |
|---|---:|---:|
| `model_ms` | 76.4 | 99.7% |
| `style_ms` | 0.2 | 0.2% |
| `combine_ms` | 0.0 | 0.0% |
| `validation_ms` | 0.0 | 0.0% |

## Per-run durations

| Run | Duration ms | Model ms | Style ms | Guess |
|---:|---:|---:|---:|---|
| 1 | 76.1 | 75.9 | 0.2 | unsure |
| 2 | 79.1 | 78.9 | 0.2 | unsure |
| 3 | 76.4 | 76.2 | 0.2 | unsure |
| 4 | 77.4 | 77.2 | 0.2 | unsure |
| 5 | 72.4 | 72.2 | 0.2 | unsure |
| 6 | 75.7 | 75.5 | 0.2 | unsure |
| 7 | 84.2 | 84.0 | 0.2 | unsure |
| 8 | 74.6 | 74.4 | 0.2 | unsure |
| 9 | 74.1 | 73.9 | 0.2 | unsure |
| 10 | 75.8 | 75.6 | 0.2 | unsure |

## Hundred-a-day arithmetic

At 0.077 s per run, 100 runs per day is `100 × 0.077 = 7.7 s` of compute per day (about 0.1 minutes, or 0.00 hours). API spend is $0.00 per day.
