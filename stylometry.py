"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures describe sentence-length spread, vocabulary repetition, and
punctuation density. Their normalized average forms the style signal.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics
import unicodedata


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    Coefficient of variation for sentence word counts.

    Returns:
        Sample standard deviation divided by the mean sentence length, or 0
        when fewer than two non-empty sentences are available.
    """
    lengths = [len(words(sentence)) for sentence in sentences(text)]
    lengths = [length for length in lengths if length > 0]
    if len(lengths) < 2:
        return 0.0

    mean_length = statistics.mean(lengths)
    return statistics.stdev(lengths) / mean_length if mean_length else 0.0


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words.

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.

    Worth knowing before you rely on it: this measure falls as text gets
    longer, because common words repeat. Two texts of different lengths aren't
    directly comparable on it, and if your test inputs vary a lot in length,
    that alone can look like a signal.
    """
    tokens = words(text)
    return len(set(tokens)) / len(tokens) if tokens else 0.0


def punctuation_density(text: str) -> float:
    """
    Unicode punctuation characters as a fraction of all characters.

    Returns:
        A float from 0 to 1, or 0 for empty text.
    """
    if not text:
        return 0.0

    punctuation_count = sum(
        unicodedata.category(character).startswith("P") for character in text
    )
    return punctuation_count / len(text)


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.**

    Combine your three measures into one number. Same direction as
    `detector.model_signal`, so that `scoring.combine_signals` can treat them
    the same way — if one of your signals runs backwards, everything above it
    is wrong in a way that's hard to see.

    It averages inverse spread (regularity), inverse type-token ratio
    (repetition), and normalized inverse punctuation density. A one-sentence
    input gets a neutral regularity component; text without words gets a
    neutral overall score.
    """
    if not words(text):
        return 0.5

    sentence_list = [sentence for sentence in sentences(text) if words(sentence)]
    if len(sentence_list) < 2:
        regularity = 0.5
    else:
        spread = sentence_length_spread(text)
        regularity = 1.0 / (1.0 + spread)

    repetition = 1.0 - type_token_ratio(text)
    conventional_punctuation = 1.0 - min(punctuation_density(text) / 0.10, 1.0)
    return round((regularity + repetition + conventional_punctuation) / 3.0, 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
