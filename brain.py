import json
import logging
import re
import time

import openai

import config
import i18n
import llm
import tools

log = logging.getLogger("jully")

SYSTEM = (
    "You are Jully, a voice assistant running on the user's PC. "
    "Your reply will be SPOKEN aloud: answer in {language}, in at most one or two short sentences, "
    "with no markdown, lists, emojis or links. "
    "To act on the computer, use the tools; after using them, confirm in a few words. "
    "Never say you did something without having called the matching tool. "
    "If the request is impossible with the tools, say so simply. "
    "Always write numbers as digits (70, 13.20, 3 thousand), never spelled out; the voice reads them fine. "
    "Be direct like Siri: go straight to the answer, with no introduction, no explaining your reasoning and "
    "no offer of extra help at the end. Examples: "
    "'what is 20 plus 50' -> '70'; "
    "'what is photosynthesis' -> 'It is how plants turn sunlight into energy.'; "
    "'copy 115' -> 'Done, copied.'"
)

_history = []
_last_use = 0.0


def _extra():
    # gpt-oss "thinks" before answering; low effort = much faster replies
    if config.LLM_MODEL.startswith("openai/gpt-oss"):
        return {"extra_body": {"reasoning_effort": "low"}}
    return {}


def _trim():
    """Keep only the last messages, always starting at a user message."""
    while len(_history) > config.HISTORY_MAX_MSGS:
        _history.pop(0)
        while _history and _history[0]["role"] != "user":
            _history.pop(0)


def _shorten(text, max_sentences=2, max_chars=220):
    """Safety net: drop repeated sentences and speak only the beginning."""
    # split after . ! ? even without a space ("Forty.Forty."), but not in "3.5"
    sentences = re.split(r"(?<=[.!?])\s*(?=[^\W\d_])", text.strip())
    unique = []
    for s in sentences:
        s = s.strip()
        if s and (not unique or s.lower() != unique[-1].lower()):
            unique.append(s)
    short = " ".join(unique[:max_sentences])
    if len(short) > max_chars:
        short = short[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "."
    return short


def _complete(system):
    """Ask the model. Some models occasionally emit a malformed tool call, which the API rejects with a
    400; that is random, so one retry usually fixes it."""
    for attempt in (1, 2):
        try:
            return llm.client().chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "system", "content": f"{system} Now it is {tools.date_and_time()}."}]
                         + _history,
                tools=[{"type": "function", "function": s} for s in tools.schemas()],
                max_tokens=600,  # models that "think" spend part of this before answering
                temperature=0.4,
                **_extra(),
            )
        except openai.BadRequestError as e:
            if attempt == 2 or "tool" not in str(e).lower():
                raise
            log.warning("invalid tool call from the model, retrying: %s", e)


def clear_history():
    _history.clear()


def reply(question):
    global _last_use
    if time.monotonic() - _last_use > config.HISTORY_TTL_S:
        _history.clear()
    _last_use = time.monotonic()

    if not config.AI_CONFIGURED:
        return i18n.t("need_api_key")

    _history.append({"role": "user", "content": question})
    system = SYSTEM.format(language=config.LANGUAGES[config.LANGUAGE])
    try:
        for _ in range(5):
            r = _complete(system)
            m = r.choices[0].message
            entry = {"role": "assistant", "content": "" if m.tool_calls else (m.content or "")}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in m.tool_calls
                ]
            _history.append(entry)

            if not m.tool_calls:
                _trim()
                return _shorten(m.content or "")

            for tc in m.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    result = "Error: invalid arguments, try again."
                else:
                    log.info("tool %s %s", tc.function.name, args)
                    result = tools.execute(tc.function.name, args)
                _history.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        return i18n.t("too_many_steps")
    except Exception:
        log.exception("error talking to the model")
        _history.clear()
        return i18n.t("llm_error")
