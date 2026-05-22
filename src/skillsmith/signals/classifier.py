"""Qwen-based semantic predicate evaluator.

Four semantic predicates backed by a small local chat model.
All failures degrade to UNKNOWN — never raise.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from skillsmith.signals.predicates import PredicateContext, PredicateResult

if TYPE_CHECKING:
    from skillsmith.lm_client import OpenAICompatClient

_log = logging.getLogger(__name__)

_CLASSIFIER_PROMPT = """\
You are a classifier. Answer with one word: YES, NO, or UNKNOWN.

Criterion: {criterion}

Input:
{input_text}

Answer:"""

_MAX_INPUT_CHARS = 2000
_TIMEOUT_SECONDS = 2.0


def _call_classifier(
    criterion: str,
    input_text: str,
    lm_client: "OpenAICompatClient",
    model: str,
) -> PredicateResult:
    """Make a single classifier call. Returns UNKNOWN on any failure."""
    trimmed = input_text[:_MAX_INPUT_CHARS]
    prompt = _CLASSIFIER_PROMPT.format(criterion=criterion, input_text=trimmed)
    try:
        start = time.monotonic()
        resp = lm_client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            timeout=_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - start
        _log.debug("classifier call: %.2fs", elapsed)

        raw = ""
        if hasattr(resp, "choices") and resp.choices:
            raw = resp.choices[0].message.content or ""
        elif isinstance(resp, dict):
            raw = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

        word = raw.strip().upper().split()[0] if raw.strip() else ""
        if word == "YES":
            return PredicateResult.MET
        if word == "NO":
            return PredicateResult.NOT_MET
        return PredicateResult.UNKNOWN
    except Exception as exc:
        _log.debug("classifier UNKNOWN due to: %s", exc)
        return PredicateResult.UNKNOWN


def eval_user_intent_matches(
    args: dict,
    ctx: PredicateContext,
    lm_client: "OpenAICompatClient",
    model: str,
) -> PredicateResult:
    intent = args.get("intent", "")
    recent_count = args.get("recent_prompts", 1)
    text = (ctx.recent_prompt_text or "").strip()
    if not text or not intent:
        return PredicateResult.UNKNOWN
    criterion = f"The user's message indicates the intent: '{intent}'."
    return _call_classifier(criterion, text[:_MAX_INPUT_CHARS], lm_client, model)


def eval_agent_intent_matches(
    args: dict,
    ctx: PredicateContext,
    lm_client: "OpenAICompatClient",
    model: str,
) -> PredicateResult:
    intent = args.get("intent", "")
    # agent_response not in PredicateContext; use recent_prompt_text as proxy
    text = (ctx.recent_prompt_text or "").strip()
    if not text or not intent:
        return PredicateResult.UNKNOWN
    criterion = f"The agent's last response indicates the intent: '{intent}'."
    return _call_classifier(criterion, text, lm_client, model)


def eval_artifact_completeness(
    args: dict,
    ctx: PredicateContext,
    lm_client: "OpenAICompatClient",
    model: str,
) -> PredicateResult:
    from skillsmith.signals.predicates import _glob_files, _read_file

    path_pattern = args.get("path", "")
    criteria_text = args.get("criteria", "")
    if not path_pattern or not criteria_text:
        return PredicateResult.UNKNOWN

    files = _glob_files(ctx.project_root, path_pattern)
    if not files:
        return PredicateResult.NOT_MET

    content = _read_file(files[0])
    if content is None:
        return PredicateResult.UNKNOWN

    criterion = f"The document meets the following completeness criterion: {criteria_text}"
    return _call_classifier(criterion, content, lm_client, model)


def eval_prompt_topic_matches(
    args: dict,
    ctx: PredicateContext,
    lm_client: "OpenAICompatClient",
    model: str,
) -> PredicateResult:
    topics = args.get("topics", [])
    text = (ctx.recent_prompt_text or "").strip()
    if not text or not topics:
        return PredicateResult.UNKNOWN
    criterion = f"The message is about any of the following topics: {', '.join(topics)}."
    return _call_classifier(criterion, text, lm_client, model)


SEMANTIC_PREDICATES = {
    "user_intent_matches": eval_user_intent_matches,
    "agent_intent_matches": eval_agent_intent_matches,
    "artifact_completeness": eval_artifact_completeness,
    "prompt_topic_matches": eval_prompt_topic_matches,
}
