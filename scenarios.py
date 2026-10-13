"""
What your test runs. ← UNIT 8, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
false positives needs your own writing. One about label coverage needs inputs
across the score range. One about the appeal path needs a real content_id.

`run_eval.py` runs everything here three times. The current Milestone 5
scenarios use synthetic inputs because no personal writing or evaluation data
was provided. They exercise the request/response path but cannot establish
real-world false-positive rates, factuality, fake-evidence detection, or reader
comprehension.

A scenario carries **either** of these:

    "texts"   a list of strings. Each is sent as {"text": ..., "creator_id": ...}
              with a creator_id made up for you. Use this for most criteria.

    "bodies"  a list of whole request bodies, sent exactly as written. Use this
              when the malformed request IS the point — empty text, no `text`
              field at all, something enormous. A bad-input criterion needs it,
              because you cannot express "the field is missing" as a string.
"""

SCENARIOS = [
    {
        "name": "synthetic human-like prose proxy",
        "criterion": 1,
        "texts": [
            "I keep a list on the fridge because otherwise I forget what we need. "
            "This week it has apples, rice, and the coffee that ran out yesterday. "
            "I will probably add something else before Saturday.",
            "The bus was late again, so I walked the last few blocks. It was cold "
            "but not unpleasant, and I had enough time to stop for a sandwich. "
            "I got home a little after six.",
            "Our group met after class to divide up the work. I took the first "
            "section because I already had notes from last week. We agreed to "
            "check in again on Thursday.",
        ],
    },
    {
        "name": "synthetic factual-claim examples",
        "criterion": 2,
        "texts": [
            "Water freezes at zero degrees Celsius at standard atmospheric "
            "pressure. This is a familiar physical property of pure water. "
            "The exact freezing point can shift when substances are dissolved.",
            "Earth travels around the Sun once each year. A day is tied to "
            "Earth's rotation on its axis. These motions help define common "
            "units of time.",
            "The Pacific Ocean is larger than the Atlantic Ocean. It covers a "
            "substantial part of Earth's surface. Ocean measurements depend "
            "on how their boundaries are defined.",
        ],
    },
    {
        "name": "bad input boundaries",
        "criterion": 3,
        "bodies": [
            {"text": "", "creator_id": "eval_bad_empty"},
            {"creator_id": "eval_bad_missing"},
            {"text": "word " * 2501, "creator_id": "eval_bad_huge"},
        ],
    },
    {
        "name": "synthetic fabricated-citation examples",
        "criterion": 4,
        "texts": [
            "A report claims that a fictional institute proved this result in "
            "2023. It cites a made-up journal and an invented volume number. "
            "No verification of the source is included.",
            "The passage attributes a quotation to a nonexistent book and gives "
            "a page number. The quotation is presented as exact evidence. "
            "There is no reliable source attached.",
            "This paragraph refers to a fabricated study by authors who do not "
            "exist. It supplies a plausible title and publication year. "
            "The citation itself is unsupported.",
        ],
    },
    {
        "name": "synthetic explanation-output probes",
        "criterion": 5,
        "texts": [
            "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten.",
            "The committee considered several alternatives before making its "
            "decision. Each proposal was reviewed against the same documented "
            "requirements. The final option was selected after that comparison.",
            "Our research begins with a short question. We collect a few useful "
            "examples and look for a pattern. The conclusion should stay close "
            "to what those examples actually show.",
        ],
    },
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
