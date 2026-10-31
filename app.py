#!/usr/bin/env python3
"""
Provenance Guard — the web service.

    python app.py

Then, in another terminal:

    curl -X POST http://127.0.0.1:5000/ping \
      -H "Content-Type: application/json" \
      -d '{"message": "hello"}'

That's the example route. It works right now, before you've written anything.
**Leave it alone** — it's your control. When something breaks later, check that
`/ping` still answers: if it does, the problem is in your handler; if it
doesn't, it's the service itself.

Routes:

    POST /ping        the worked example. Already works. Don't edit it
    POST /submit      score text with both signals and return a reader-facing label
    POST /appeal      record a writer's request for review
    GET  /log         the audit log. Already works
    GET  /health      is the service up, and is the model loaded
"""

import hashlib
import time
import uuid

from flask import Flask, g, jsonify, request

import audit
import config
import detector
import instrumentation
import scoring
import stylometry

app = Flask(__name__)


# ── Request instrumentation — UNIT 9 ──────────────────────────────────────────
# Every request gets an id and a start time before any handler runs, so both
# successes and failures can be timed and correlated in the run log.

@app.before_request
def _start_request_timer():
    g.request_id = str(uuid.uuid4())
    g.request_started = time.perf_counter()


def _request_id() -> str:
    return getattr(g, "request_id", None) or str(uuid.uuid4())


def _elapsed_ms() -> float | None:
    started = getattr(g, "request_started", None)
    if started is None:
        return None
    return (time.perf_counter() - started) * 1000.0


def _input_summary(payload, text: str | None = None) -> dict:
    """The part of the request worth keeping after the fact."""
    if isinstance(text, str):
        return {"chars": len(text), "words": len(text.split()), "preview": text[:120]}
    if isinstance(payload, dict) and isinstance(payload.get("text"), str):
        value = payload["text"]
        return {"chars": len(value), "words": len(value.split()), "preview": value[:120]}
    return {
        "chars": None,
        "words": None,
        "preview": None,
        "body_type": type(payload).__name__,
    }


# ── Rate limiting — UNIT 8 ────────────────────────────────────────────────────
# /submit is limited by creator_id with the per-minute and per-day values in
# config.py. If limiting is disabled there, this decorator becomes a no-op.
#
# The storage backend is preconfigured, which stops Flask-Limiter printing a
# warning on every start. In-memory is right for one laptop and wrong for
# anything real — a restart forgets every count.

class _LimiterOff:
    """
    Stands in for the real limiter while rate limiting is off.

    Its decorator returns the route untouched, allowing the active route
    decorator to remain in place while limiting is disabled.
    """

    def limit(self, *args, **kwargs):
        return lambda view: view


limiter = _LimiterOff()
if config.RATE_LIMITING_ENABLED:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def rate_limit_key():
        """
        Use creator_id when available and the remote address as a fallback.

        This is a per-creator limit, so a client that rotates IDs can avoid
        sharing a bucket.
        """
        payload = request.get_json(silent=True)
        # A body that parses as JSON but isn't an object — a bare list or
        # string — has no .get. Without this guard the key function raises
        # BEFORE the route runs, and a malformed request becomes a 500 that
        # looks like your handler crashed when your handler never ran.
        if not isinstance(payload, dict):
            return get_remote_address()
        creator = payload.get("creator_id")
        return creator if isinstance(creator, str) and creator.strip() else get_remote_address()

    limiter = Limiter(
        key_func=rate_limit_key,
        app=app,
        storage_uri=config.RATE_LIMIT_STORAGE,
        default_limits=[],
    )

    @app.errorhandler(429)
    def rate_limited(exc):
        """
        A rejected request still leaves a trace.

        ⚠️ An attack that shows up only as an absence is one you'll never find.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        creator_id = payload.get("creator_id", "unknown")
        request_id = _request_id()
        duration_ms = _elapsed_ms()
        audit.log_rejection(
            creator_id=creator_id,
            reason="rate_limited",
            limit=str(exc.description),
            request_id=request_id,
            duration_ms=round(duration_ms, 3) if duration_ms is not None else None,
        )
        instrumentation.record_run(
            request_id=request_id,
            event="rejected",
            endpoint=request.path,
            creator_id=creator_id,
            input=_input_summary(payload),
            output={"error": "rate_limited", "limit": str(exc.description)},
            duration_ms=duration_ms,
            stages={"limiter_ms": duration_ms},
            status="rejected",
            error="rate_limited",
        )
        return jsonify({
            "error": "rate_limited",
            "message": "Too many submissions. Try again shortly.",
            "limit": str(exc.description),
        }), 429


# ── The worked example. Already works. Don't edit. ────────────────────────────

@app.post("/ping")
def ping():
    """
    Everything a route needs, in six lines.

    JSON arrives as a dict. You pull things out of it. You return a dict and
    the framework turns it into a response. That's the whole idea.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "ok": True,
        "you_sent": payload.get("message"),
        "service": "provenance-guard",
    })


@app.get("/health")
def health():
    """Is the service up, and has the model been downloaded yet?"""
    import detector

    loaded = detector._model is not None
    return jsonify({
        "ok": True,
        "detector_model": config.DETECTOR_MODEL,
        "detector_loaded": loaded,
        "rate_limiting": config.RATE_LIMITING_ENABLED,
        "log_entries": len(audit.read_entries()),
        "run_entries": len(instrumentation.read_runs()),
    })


# ── SUBMISSION ROUTE ──────────────────────────────────────────────────────────

@app.post("/submit")
@limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute;{config.RATE_LIMIT_PER_DAY}/day")
def submit():
    """Score text with both signals, assign a label, and log the decision.

    Expects JSON:
        {"text": "...", "creator_id": "..."}

    The final response schema will include:
        {"content_id": "...", "guess": "...", "confidence": 0.0, "label": "...",
         "model_score": 0.0, "style_score": 0.0, "combined_score": 0.0}

    ⚠️ **Both signal scores go in the response, not just the log.** Unit 8's
    `run_attacks.py` and `run_eval.py` read `model_score` and `style_score`
    straight off this response and put them in your reports. Leave them out and
    every row of next unit's evidence says `null` — which is exactly the
    diagnostic you need to name a stage and a mechanism. You do not want to
    find that out after running the attack set.

    ─────────────────────────────────────────────────────────────────────────
    Build it in three passes. Do not skip ahead — the ordering is how you tell
    a broken route from a broken signal.

    **Milestone 3 — the route answers.**
      1. Return a hardcoded response. Confirm `curl` gets it back before you
         add any logic at all.
      2. Then pull `text` and `creator_id` out of the payload.
      3. Then call ONE signal — `detector.model_signal(text)` — and put the
         real number in.
      4. Log every submission with `audit.log_decision(...)`. The content_id
         matters: `/appeal` needs it, and a student who skips it rebuilds this
         whole flow later.

    **Milestone 4 — the second signal and the score.**
      5. Add `stylometry.style_signal(text)`.
      6. Combine them with `scoring.combine_signals(...)`.
      7. Log BOTH signal scores alongside the combined one, and put them in the
         response too. Next unit you can't diagnose anything without them.

    **The label.**
      8. `scoring.score_to_label(...)` and put the real label in the response.

    ─────────────────────────────────────────────────────────────────────────
    Worth deciding early, because unit 8's attack set will decide it for you:
    what should this do when `text` is missing, empty, or enormous? A crash on
    a malformed input is one of the most common real failures there is.
    """
    payload = request.get_json(silent=True)
    request_id = _request_id()
    started = time.perf_counter()
    creator_id = "unknown"
    creator_valid = False
    if isinstance(payload, dict):
        supplied_creator_id = payload.get("creator_id")
        if isinstance(supplied_creator_id, str) and supplied_creator_id.strip():
            creator_id = supplied_creator_id.strip()
            creator_valid = True

    def reject(error: str, message: str, status: int = 400):
        duration_ms = (time.perf_counter() - started) * 1000.0
        audit.log_rejection(
            creator_id=creator_id,
            reason=error,
            error=error,
            request_id=request_id,
            duration_ms=round(duration_ms, 3),
        )
        instrumentation.record_run(
            request_id=request_id,
            event="rejected",
            endpoint="/submit",
            creator_id=creator_id,
            input=_input_summary(payload),
            output={"error": error, "message": message},
            duration_ms=duration_ms,
            stages={"validation_ms": round(duration_ms, 3)},
            status="rejected",
            error=error,
        )
        return jsonify({"error": error, "message": message}), status

    if not isinstance(payload, dict):
        return reject("invalid_json", "Request body must be a JSON object.")

    if "text" not in payload or payload["text"] is None:
        return reject("missing_text", "No text provided.")

    text = payload["text"]
    if not isinstance(text, str):
        return reject("invalid_text", "Text must be a string.")
    if not text.strip():
        return reject("empty_text", "Input is empty.")
    if len(text) > config.MAX_SUBMISSION_CHARS:
        return reject(
            "text_too_large",
            f"Input exceeds the limit of {config.MAX_SUBMISSION_CHARS:,} characters.",
        )

    if not creator_valid:
        return reject("invalid_creator_id", "A non-empty creator_id is required.")

    validation_ms = (time.perf_counter() - started) * 1000.0

    model_started = time.perf_counter()
    try:
        model_score = detector.model_signal(text)
    except detector.DetectorUnavailable:
        return reject(
            "detector_unavailable",
            "The local detector is unavailable.",
            status=503,
        )
    except ValueError:
        return reject(
            "text_too_short",
            "Text is too short to score; provide a few sentences.",
        )
    model_ms = (time.perf_counter() - model_started) * 1000.0

    style_started = time.perf_counter()
    style_score = stylometry.style_signal(text)
    style_ms = (time.perf_counter() - style_started) * 1000.0

    combine_started = time.perf_counter()
    combined_score = scoring.combine_signals(model_score, style_score)
    guess, label = scoring.score_to_label(combined_score)
    content_id = str(uuid.uuid4())
    combine_ms = (time.perf_counter() - combine_started) * 1000.0

    duration_ms = (time.perf_counter() - started) * 1000.0
    stages = {
        "validation_ms": round(validation_ms, 3),
        "model_ms": round(model_ms, 3),
        "style_ms": round(style_ms, 3),
        "combine_ms": round(combine_ms, 3),
    }
    output = {
        "content_id": content_id,
        "guess": guess,
        "model_score": model_score,
        "style_score": style_score,
        "combined_score": combined_score,
        "label": label,
    }
    input_summary = _input_summary(payload, text)
    input_summary["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    model_info = detector.model_metadata()

    audit.log_decision(
        content_id=content_id,
        creator_id=creator_id,
        guess=guess,
        model_score=model_score,
        style_score=style_score,
        combined_score=combined_score,
        label=label,
        status="decided",
        request_id=request_id,
        duration_ms=round(duration_ms, 3),
        stages=stages,
        model_revision=model_info.get("revision"),
    )
    instrumentation.record_run(
        request_id=request_id,
        event="decision",
        endpoint="/submit",
        creator_id=creator_id,
        input=input_summary,
        output=output,
        duration_ms=duration_ms,
        stages=stages,
        status="decided",
        error=None,
        model=model_info,
    )
    return jsonify({
        "content_id": content_id,
        "guess": guess,
        "model_score": model_score,
        "style_score": style_score,
        "combined_score": combined_score,
        "confidence": 0.0,
        "label": label,
    })


@app.post("/appeal")
def appeal():
    """Record a writer's request to have a decision reviewed.

    Expects JSON:
        {"content_id": "...", "reasoning": "..."}

    Should:
      1. Check the content_id actually exists — `audit.entries_for(id)` tells
         you. A typo here fails silently and looks like a broken endpoint,
         which is the single most common way this milestone eats an hour.
      2. Record the appeal with `audit.log_appeal(...)`, which moves the item
         to `under_review`.
      3. Confirm to the writer. No automatic re-checking needed.

    This is the smallest endpoint in the project and the one that matters most
    to the person on the other end. It's the only thing standing between a
    wrong accusation and nothing at all.
    """
    payload = request.get_json(silent=True)
    request_id = _request_id()
    started = time.perf_counter()
    creator_id = "unknown"

    def reject(error: str, message: str, status: int = 400):
        duration_ms = (time.perf_counter() - started) * 1000.0
        audit.log_rejection(
            creator_id=creator_id,
            reason=error,
            error=error,
            request_id=request_id,
            duration_ms=round(duration_ms, 3),
        )
        instrumentation.record_run(
            request_id=request_id,
            event="rejected",
            endpoint="/appeal",
            creator_id=creator_id,
            input=_input_summary(payload),
            output={"error": error, "message": message},
            duration_ms=duration_ms,
            stages={"validation_ms": round(duration_ms, 3)},
            status="rejected",
            error=error,
        )
        return jsonify({"error": error, "message": message}), status

    if not isinstance(payload, dict):
        return reject("invalid_json", "Request body must be a JSON object.")

    content_id = payload.get("content_id")
    if not isinstance(content_id, str) or not content_id.strip():
        return reject("invalid_content_id", "A non-empty content_id is required.")
    content_id = content_id.strip()

    reasoning = payload.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        return reject("invalid_reasoning", "A non-empty reasoning string is required.")

    lookup_started = time.perf_counter()
    original = next(
        (
            entry
            for entry in audit.entries_for(content_id)
            if entry.get("status") == "decided" and entry.get("event") != "appeal"
        ),
        None,
    )
    lookup_ms = (time.perf_counter() - lookup_started) * 1000.0
    if original is None:
        return reject(
            "unknown_content_id",
            "No decision was found for this content_id.",
            status=404,
        )
    creator_id = original["creator_id"]

    write_started = time.perf_counter()
    audit.log_appeal(
        content_id=content_id,
        creator_id=creator_id,
        reasoning=reasoning.strip(),
    )
    write_ms = (time.perf_counter() - write_started) * 1000.0
    duration_ms = (time.perf_counter() - started) * 1000.0

    instrumentation.record_run(
        request_id=request_id,
        event="appeal",
        endpoint="/appeal",
        creator_id=creator_id,
        input={
            "content_id": content_id,
            "reasoning_chars": len(reasoning.strip()),
            "reasoning_preview": reasoning.strip()[:120],
        },
        output={"content_id": content_id, "status": "under_review"},
        duration_ms=duration_ms,
        stages={
            "pre_lookup_ms": round(max(duration_ms - lookup_ms - write_ms, 0.0), 3),
            "lookup_ms": round(lookup_ms, 3),
            "write_ms": round(write_ms, 3),
        },
        status="under_review",
        error=None,
    )
    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal has been received for review.",
    })


# ── Already works ─────────────────────────────────────────────────────────────

@app.get("/log")
def get_log():
    """
    The audit log, most recent last.

        curl "http://127.0.0.1:5000/log?limit=10"

    You need this in unit 8 to paste entries into your README, and you need it
    now to see whether your logging is actually working.
    """
    limit = request.args.get("limit", type=int)
    entries = audit.read_entries(limit=limit)
    return jsonify({"count": len(entries), "entries": entries})


# ── Observability endpoints — UNIT 9 ─────────────────────────────────────────

@app.get("/runs")
def get_runs():
    """
    The structured run log, oldest first.

        curl "http://127.0.0.1:5000/runs?limit=10"

    Unlike `/log`, this records the operational facts: input shape, output
    shape, total duration, per-stage milliseconds, and failure reasons.
    """
    limit = request.args.get("limit", type=int)
    entries = instrumentation.read_runs(limit=limit)
    return jsonify({"count": len(entries), "entries": entries})


@app.get("/metrics")
def get_metrics():
    """Aggregate counts, latency, stage timings, and compute cost per run."""
    return jsonify(instrumentation.summarize_runs())


def main():
    print(f"Provenance Guard on http://{config.HOST}:{config.PORT}")
    print(f"  detector model:  {config.DETECTOR_MODEL}")
    print(f"  rate limiting:   {'ON' if config.RATE_LIMITING_ENABLED else 'off (config.py)'}")
    print(f"  audit log:       {config.AUDIT_LOG}")
    print(f"  run log:         {config.RUN_LOG}")
    print()
    print("Check it's alive:")
    print(f'  curl -X POST http://{config.HOST}:{config.PORT}/ping \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"message\": \"hello\"}'")
    print()
    # debug=True hands out an interactive debugger, so it's local-only — see config.py
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
