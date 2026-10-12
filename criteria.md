# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1.

**Criterion — False positives:** Of 100 human-written samples, no more than 20 may be labeled True (false-positive rate ≤20%). If “True” means AI-generated, this means at least 80 must be labeled False.



**Why this target:**
Human-written text should rarely be misclassified as machine-generated. A 20% ceiling keeps false accusations low and makes the label trustworthy. If your original 80% figure was intentional, note that it allows a very high false-positive rate and should be tightened.

---

## 2.

**Criterion — Factuality:** In 100 outputs, at least 85% of verifiable factual claims must be supported by evidence—such as a citation, source, or reproducible check. Unsupported claims must be labeled uncertain or removed.



**Why this target:**
85% is a practical minimum for trust. Below this, factual errors become common enough to undermine decisions.


---

## 3.

**Criterion — Bad input:** For missing text, empty text, and text over the size limit (e.g., >X characters or words), the service must reject the input with a specific error and must not produce a normal answer.

Missing text: “No text provided.”

Empty text: “Input is empty.”

Oversized text: “Input exceeds the limit of X.”


**Why this target:**
Boundary cases must fail safely and predictably so users know why no output was produced and tests can verify behavior.


---

## 4.

**Criterion — Fake evidence:** Of 50 cases containing fake evidence—fabricated citations, nonexistent sources, or quotes not present in the cited source—the system must flag or refuse to use that evidence in at least 95% of cases.


**Why this target:**
Fabricated evidence is a high-severity failure. A 95% target makes it rare and measurable; the 5% tolerance acknowledges hard cases without normalizing the behavior.


---

## 5.

**Criterion — Explanation quality:**  In 30 tests, at least 80% of readers must be able to state, after reading the system’s explanation:
what the system decided,
the main reason for that decision, and
what evidence or condition would change it.


**Why this target:**
An explanation is only useful if readers can understand the decision and know what to do next. This measures comprehension and actionability, not just satisfaction.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
