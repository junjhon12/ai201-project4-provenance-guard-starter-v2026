# Synthetic Milestone 5 attack set

This is a small, explicitly synthetic smoke/behavior set created because no
attack-set folder was present. It is intended to provide identical before/after
inputs for `run_attacks.py`, not statistically valid security or authorship
evidence.

- `false_positive_proxy` contains synthetic plain-language prose, not writing
  supplied or authored by the user.
- `evasion` and `ai_baseline` are synthetic score-probing inputs.
- `malformed_request` exercises missing text and non-object JSON handling.

The runs do not establish a real-world false-positive rate, factuality, fake
evidence detection, or reader comprehension.
