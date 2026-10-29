import brain


def test_shorten_drops_repetition_and_limits_sentences():
    assert brain._shorten("Forty.Forty.") == "Forty."
    assert brain._shorten("One. Two. Three.") == "One. Two."


def test_shorten_does_not_split_decimals():
    assert brain._shorten("It costs 3.5 dollars.") == "It costs 3.5 dollars."


def test_shorten_cuts_long_text():
    r = brain._shorten("word " * 100)
    assert len(r) <= 221 and r.endswith(".")


def test_trim_always_starts_at_a_user_message(monkeypatch):
    monkeypatch.setattr(brain.config, "HISTORY_MAX_MSGS", 3)
    brain._history[:] = [
        {"role": "user"}, {"role": "assistant"}, {"role": "tool"}, {"role": "assistant"}, {"role": "user"},
    ]
    brain._trim()
    assert brain._history[0]["role"] == "user"
    assert len(brain._history) <= 3
    brain._history.clear()


def test_without_a_key_it_asks_to_configure(monkeypatch):
    monkeypatch.setattr(brain.config, "AI_CONFIGURED", False)
    monkeypatch.setattr(brain.config, "LANGUAGE", "en")
    assert "key" in brain.reply("hi").lower()
    assert brain._history == []


class _FakeResponse:
    status_code = 400
    headers = {}
    request = None


def _bad_request(message):
    return brain.openai.BadRequestError(message, response=_FakeResponse(), body=None)


def _fake_client(outcomes):
    class Completions:
        calls = 0

        def create(self, **_):
            outcome = outcomes[Completions.calls]
            Completions.calls += 1
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    class Client:
        chat = type("Chat", (), {"completions": Completions()})()

    return Client, Completions


def test_complete_retries_once_on_a_malformed_tool_call(monkeypatch):
    client, completions = _fake_client([_bad_request("tool call validation failed"), "ok"])
    monkeypatch.setattr(brain.llm, "client", lambda: client)
    assert brain._complete("system") == "ok"
    assert completions.calls == 2


def test_complete_does_not_retry_other_errors_or_loop_forever(monkeypatch):
    import pytest
    client, completions = _fake_client([_bad_request("model not found")])
    monkeypatch.setattr(brain.llm, "client", lambda: client)
    with pytest.raises(brain.openai.BadRequestError):
        brain._complete("system")
    assert completions.calls == 1

    client, completions = _fake_client([_bad_request("tool x"), _bad_request("tool x")])
    monkeypatch.setattr(brain.llm, "client", lambda: client)
    with pytest.raises(brain.openai.BadRequestError):
        brain._complete("system")
    assert completions.calls == 2
