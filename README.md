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

Milestone 4 implements both signals and the combined score in `POST /submit`.
The route returns and logs the `model_score`, `style_score`, and
`combined_score`; confidence and label remain Milestone 3 placeholders until
Milestone 5. The full flow above describes the eventual label and appeal path.

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
| `confidence` | number | Milestone 3 placeholder (`0.0`); not a confidence estimate. |
| `label` | string | Milestone 3 placeholder stating that labeling is not implemented yet. |
| `model_score` | number, 0–1 | Predictability-based model signal; higher means more AI-like. |
| `style_score` | number, 0–1 | Shape-based style signal; higher means more AI-like. |
| `combined_score` | number, 0–1 | Equal-weight average of `model_score` and `style_score`. |

Missing text returns `400` with “No text provided.”, empty text returns `400`
with “Input is empty.”, and text longer than 10,000 characters returns `400`
with “Input exceeds the limit of 10,000 characters.” Other malformed or
invalid input and text too short to score also return `400` with a stable error
code and explanation. If the local detector cannot load, the route returns
`503` rather than manufacturing a score. Rejections are recorded separately;
they do not create a decision entry. `guess` and final confidence/label
behavior are deferred to Milestone 5.

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
current `AI_THRESHOLD` of `0.65`, so the planned label is `ai` and the reader
would see: “Our signals suggest this text may be AI-written. This is an
estimate, not proof.”

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
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- Paste the submission and log requests and responses here. -->

**A submission (Milestone 4 — both signals and the combined score)**

The request below is the sample payload; the response and matching log entry
were captured from an isolated Flask test-client run with temporary log storage.

```powershell
PS> '{"text":"Last Saturday I missed the bus, so I walked to the corner store instead. It was raining hard enough that my shoes squeaked when I went inside. The cashier laughed when I shook water off my jacket, and I bought a coffee I did not really need. I got home later than planned, but the walk ended up being the nicest part of my morning.","creator_id":"milestone4-sample"}' | curl.exe -i http://127.0.0.1:5000/submit -H 'Content-Type: application/json' --data-binary '@-'
```

```http
HTTP/1.1 200 OK
```

```json
{
  "combined_score": 0.66315,
  "confidence": 0.0,
  "content_id": "33f29453-fc61-4d45-bd63-0149990bb9a8",
  "label": "Pending Milestone 5: no label assigned yet.",
  "model_score": 0.7198,
  "style_score": 0.6065
}
```

**What the log shows afterwards**

```powershell
PS> curl.exe -i "http://127.0.0.1:5000/log?limit=1"
```

```http
HTTP/1.1 200 OK
```

```json
{
  "count": 1,
  "entries": [
    {
      "combined_score": 0.66315,
      "content_id": "33f29453-fc61-4d45-bd63-0149990bb9a8",
      "creator_id": "milestone4-sample",
      "guess": null,
      "label": "Pending Milestone 5: no label assigned yet.",
      "model_score": 0.7198,
      "status": "decided",
      "style_score": 0.6065,
      "timestamp": "2026-10-12T21:56:08+00:00"
    }
  ]
}
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
