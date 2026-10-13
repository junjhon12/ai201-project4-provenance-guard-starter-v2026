# Attack run — before

- Produced by: `run_attacks.py::main`
- Service: `app.py::submit`
- 8 attacks · 2026-10-13 09:29
- Auto-marked BROKE (5xx, crash, no response): **0**
- Left for you to judge: **8**

The Verdict column is blank where a script can't honestly decide. Whether
an evasion worked depends on where you put your thresholds — read the
`targets` column, look at what came back, and write HELD or BROKE yourself.

Each attack submits as creator_id `attacker_<id>`, and the content_id it
came back with is in the table — either one will match this run against your
audit log when you go looking for the ten entries to paste.

| ID | Family | Targeting | Status | Content ID | Guess | Score | Verdict |
|---|---|---|---|---|---|---|---|
| FP01 | false_positive_proxy | Synthetic plain-language prose; not authenticated human writing | 200 | `e8b26ff3-ab6f-4b6e-80c4-7f5e2a9f95a6` | unsure | 0.000 |  |
| FP02 | false_positive_proxy | Synthetic everyday prose; not authenticated human writing | 200 | `8771f0b1-7cb5-4808-9878-b090118c7621` | unsure | 0.000 |  |
| EV01 | evasion | Synthetic typo-heavy prose tests whether errors change the score | 200 | `c8879b4e-45db-44c1-bbc1-08a70d527ae0` | unsure | 0.000 |  |
| EV02 | evasion | Synthetic formal prose probes predictable language-model scoring | 200 | `58925ba0-a739-4583-9e3d-b9151fed11b2` | ai | 0.000 |  |
| AI01 | ai_baseline | Synthetic polished generic prose used only as a score probe | 200 | `ce522a68-52bf-4bb5-aacc-90fcf17515f9` | unsure | 0.000 |  |
| MR01 | malformed_request | JSON object without required text field | 400 | `—` | — | — |  |
| MR02 | malformed_request | JSON array instead of an object | 400 | `—` | — | — |  |
| MR03 | malformed_request | Unparseable JSON body | 400 | `—` | — | — |  |

---

## By family

| Family | Attacks | Auto-BROKE | Left to judge |
|---|---|---|---|
| `ai_baseline` | 1 | 0 | 1 |
| `evasion` | 2 | 0 | 2 |
| `false_positive_proxy` | 2 | 0 | 2 |
| `malformed_request` | 3 | 0 | 3 |

> The **false_positive** family is the one to look at hardest. Those are
> written to be genuine human writing that reads as machine-like. Every one
> your service calls AI is a real writer it would have accused.

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
  "content_id": "e8b26ff3-ab6f-4b6e-80c4-7f5e2a9f95a6",
  "creator_id": "attacker_FP01",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.4611,
  "style_score": 0.5009,
  "label": "We can't tell from these signals whether this text was written by a person or with AI.",
  "error": null,
  "verdict": ""
}
```

### FP02 — `false_positive_proxy`

*Targeting:* Synthetic everyday prose; not authenticated human writing

```json
{
  "id": "FP02",
  "status": 200,
  "content_id": "8771f0b1-7cb5-4808-9878-b090118c7621",
  "creator_id": "attacker_FP02",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.6407,
  "style_score": 0.5018,
  "label": "We can't tell from these signals whether this text was written by a person or with AI.",
  "error": null,
  "verdict": ""
}
```

### EV01 — `evasion`

*Targeting:* Synthetic typo-heavy prose tests whether errors change the score

```json
{
  "id": "EV01",
  "status": 200,
  "content_id": "c8879b4e-45db-44c1-bbc1-08a70d527ae0",
  "creator_id": "attacker_EV01",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.4166,
  "style_score": 0.5683,
  "label": "We can't tell from these signals whether this text was written by a person or with AI.",
  "error": null,
  "verdict": ""
}
```

### EV02 — `evasion`

*Targeting:* Synthetic formal prose probes predictable language-model scoring

```json
{
  "id": "EV02",
  "status": 200,
  "content_id": "58925ba0-a739-4583-9e3d-b9151fed11b2",
  "creator_id": "attacker_EV02",
  "guess": "ai",
  "confidence": 0.0,
  "model_score": 0.7073,
  "style_score": 0.6023,
  "label": "Our signals suggest this text may have been written with AI, but this is not proof.",
  "error": null,
  "verdict": ""
}
```

### AI01 — `ai_baseline`

*Targeting:* Synthetic polished generic prose used only as a score probe

```json
{
  "id": "AI01",
  "status": 200,
  "content_id": "ce522a68-52bf-4bb5-aacc-90fcf17515f9",
  "creator_id": "attacker_AI01",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.644,
  "style_score": 0.5106,
  "label": "We can't tell from these signals whether this text was written by a person or with AI.",
  "error": null,
  "verdict": ""
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
  "verdict": ""
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
  "verdict": ""
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
  "verdict": ""
}
```
