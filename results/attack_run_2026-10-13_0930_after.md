# Attack run — after

- Produced by: `run_attacks.py::main`
- Service: `app.py::submit`
- 8 attacks · 2026-10-13 09:30
- 5xx, crash, or no-response failures: **0**
- Verdicts below are operational judgments against each synthetic target, not
  proof of the text's true authorship.

For the evasion and AI-baseline probes, `ai` is treated as the expected
detection result and `unsure` as a bypass. The inputs are synthetic and their
authorship is not authenticated, so these marks describe observed behavior,
not verified attacks on known AI-written text.

Each attack submits as creator_id `attacker_<id>`, and the content_id it
came back with is in the table — either one will match this run against your
audit log when you go looking for the ten entries to paste.

| ID | Family | Targeting | Status | Content ID | Guess | Combined score | Verdict |
|---|---|---|---|---|---|---|---|
| FP01 | false_positive_proxy | Synthetic plain-language prose; not authenticated human writing | 200 | `6fc16ad1-546e-4c2c-aca5-955a9b5c0eab` | unsure | 0.4810 | HELD — no AI accusation |
| FP02 | false_positive_proxy | Synthetic everyday prose; not authenticated human writing | 200 | `61e9fae0-00ff-4ad8-ad45-2302fa5e6326` | unsure | 0.5713 | HELD — no AI accusation |
| EV01 | evasion | Synthetic typo-heavy prose tests whether errors change the score | 200 | `79ed09ce-0cdb-461d-b53a-3e06d5a039f0` | unsure | 0.4925 | BROKE — bypassed the expected AI label |
| EV02 | evasion | Synthetic formal prose probes predictable language-model scoring | 200 | `f17d9474-05a2-406a-baa6-c5fe996b0dbf` | ai | 0.6548 | HELD — crossed the AI threshold |
| AI01 | ai_baseline | Synthetic polished generic prose used only as a score probe | 200 | `094d6795-4c78-40c0-9410-e68c924ca7fb` | unsure | 0.5773 | BROKE — baseline probe remained unsure |
| MR01 | malformed_request | JSON object without required text field | 400 | `—` | — | — | HELD — rejected at route |
| MR02 | malformed_request | JSON array instead of an object | 400 | `—` | — | — | HELD — rejected at route |
| MR03 | malformed_request | Unparseable JSON body | 400 | `—` | — | — | HELD — rejected at route |

---

## By family

| Family | Attacks | HELD | BROKE |
|---|---|---|---|
| `ai_baseline` | 1 | 0 | 1 |
| `evasion` | 2 | 1 | 1 |
| `false_positive_proxy` | 2 | 2 | 0 |
| `malformed_request` | 3 | 3 | 0 |

> The `false_positive_proxy` cases are synthetic everyday prose, not
> authenticated human writing. An `ai` result would only count as a verified
> false positive after confirming the author was human.

---

## What came back

The detail behind the table. Paste the interesting failures into your
README — the ones that show something, not the ten easiest.

### FP01 — `false_positive_proxy`

*Targeting:* Synthetic plain-language prose; not authenticated human writing

```json
{
  "id": "FP01",
  "status": 200,
  "content_id": "6fc16ad1-546e-4c2c-aca5-955a9b5c0eab",
  "creator_id": "attacker_FP01",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.4611,
  "style_score": 0.5009,
  "label": "The signals do not support a clear authorship label. This is not an accusation; a fuller sample or independent review could change the result.",
  "error": null,
  "verdict": "HELD — no AI accusation"
}
```

### FP02 — `false_positive_proxy`

*Targeting:* Synthetic everyday prose; not authenticated human writing

```json
{
  "id": "FP02",
  "status": 200,
  "content_id": "61e9fae0-00ff-4ad8-ad45-2302fa5e6326",
  "creator_id": "attacker_FP02",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.6407,
  "style_score": 0.5018,
  "label": "The signals do not support a clear authorship label. This is not an accusation; a fuller sample or independent review could change the result.",
  "error": null,
  "verdict": "HELD — no AI accusation"
}
```

### EV01 — `evasion`

*Targeting:* Synthetic typo-heavy prose tests whether errors change the score

```json
{
  "id": "EV01",
  "status": 200,
  "content_id": "79ed09ce-0cdb-461d-b53a-3e06d5a039f0",
  "creator_id": "attacker_EV01",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.4166,
  "style_score": 0.5683,
  "label": "The signals do not support a clear authorship label. This is not an accusation; a fuller sample or independent review could change the result.",
  "error": null,
  "verdict": "BROKE — bypassed the expected AI label"
}
```

### EV02 — `evasion`

*Targeting:* Synthetic formal prose probes predictable language-model scoring

```json
{
  "id": "EV02",
  "status": 200,
  "content_id": "f17d9474-05a2-406a-baa6-c5fe996b0dbf",
  "creator_id": "attacker_EV02",
  "guess": "ai",
  "confidence": 0.0,
  "model_score": 0.7073,
  "style_score": 0.6023,
  "label": "The combined scores fall in an AI-like range. This is not proof of AI authorship; independent review or relevant drafting context could change the result.",
  "error": null,
  "verdict": "HELD — crossed the AI threshold"
}
```

### AI01 — `ai_baseline`

*Targeting:* Synthetic polished generic prose used only as a score probe

```json
{
  "id": "AI01",
  "status": 200,
  "content_id": "094d6795-4c78-40c0-9410-e68c924ca7fb",
  "creator_id": "attacker_AI01",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.644,
  "style_score": 0.5106,
  "label": "The signals do not support a clear authorship label. This is not an accusation; a fuller sample or independent review could change the result.",
  "error": null,
  "verdict": "BROKE — baseline probe remained unsure"
}
```

### MR01 — `malformed_request`

*Targeting:* JSON object without required text field

```json
{
  "id": "MR01",
  "status": 400,
  "content_id": null,
  "creator_id": "attack_missing_text",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": "HELD — rejected at route"
}
```

### MR02 — `malformed_request`

*Targeting:* JSON array instead of an object

```json
{
  "id": "MR02",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": "HELD — rejected at route"
}
```

### MR03 — `malformed_request`

*Targeting:* Unparseable JSON body

```json
{
  "id": "MR03",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": "HELD — rejected at route"
}
```
