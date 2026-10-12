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

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

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

The submit and appeal routes are still `501 not_implemented` in this starter;
this is the intended flow and contract to build, not a claim that they already
work.

### Endpoint contracts

These are the planned contracts for the two endpoints this unit builds. Requests
use a JSON object with `Content-Type: application/json`.

#### `POST /submit`

**Request fields**

| Field | Type | Meaning |
|---|---|---|
| `text` | string | The text to score; must contain non-whitespace text long enough for the detector. |
| `creator_id` | string | Identifier for the submitting writer; used to associate the decision and any appeal. |

**Successful response (`200`)**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | Unique identifier for this submission, returned for future appeals. |
| `guess` | string | One of `ai`, `human`, or `unsure`. |
| `confidence` | number, 0–1 | The combined AI-likelihood score (not a calibrated probability); included because the existing evaluation tools read this field. |
| `label` | string | Plain-language result shown to the reader. |
| `model_score` | number, 0–1 | Predictability-based model signal; higher means more AI-like. |
| `style_score` | number, 0–1 | Text-shape signal; higher means more AI-like. |

Malformed JSON, missing or invalid fields, and text too short to score should
return `400` with `{"error": "<stable_code>", "message": "<plain explanation>"}`.
If the local detector cannot load, return `503` with the same error shape rather
than manufacturing a score. Do not create a decision log entry when no decision
was made; log the rejection separately.

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
an illustrative trace, suppose the model score is `0.90`; while stylometry is
still its starter stub, its score is `0.50`. With the starter's equal weights,
the combined score is `(0.5 × 0.90) + (0.5 × 0.50) = 0.70`. That is above the
current `AI_THRESHOLD` of `0.65`, so the planned label is `ai` and the reader
would see: “Our signals suggest this text may be AI-written. This is an
estimate, not proof.”

Those scores are an example, not an observed model run: the submit route is not
built yet, stylometry is a stub, and these weights and thresholds are
placeholders to be tested and revisited. The harm is still clear: a human
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

**The rule:**

**The numbers:**

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:** Plain,
conventional human writing could be highly predictable to the model (high
model score) while having uneven sentence lengths or punctuation (lower style
score). The planned equal-weight average would temper either signal with the
other; if they differ sharply, the result moves toward the middle and should
land in `unsure` rather than treating either signal as proof. This needs to be
checked with actual calibration inputs once both signals are implemented.



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "creator_id": "..."}'
```

```json

```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "...", "reasoning": "..."}'
```

```json

```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json

```

---

## How I Used AI

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

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



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



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
