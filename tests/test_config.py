import config
import i18n


def test_invalid_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("MIC_INDEX", "abc")
    monkeypatch.setenv("WAKEWORD_THRESHOLD", "")
    monkeypatch.setenv("VOICE_RATE", "fast")
    monkeypatch.setenv("LANGUAGE", "klingon")
    config.reload()
    assert config.MIC_INDEX == -1
    assert config.WAKEWORD_THRESHOLD == 0.35
    assert config.VOICE_RATE == "+10%"
    assert config.LANGUAGE == "en"
    monkeypatch.undo()
    config.reload()


def test_voice_follows_the_language_unless_set(monkeypatch):
    monkeypatch.setenv("VOICE", "")
    monkeypatch.setenv("LANGUAGE", "pt")
    config.reload()
    assert config.VOICE == config.DEFAULT_VOICES["pt"]
    monkeypatch.setenv("VOICE", "en-GB-SoniaNeural")
    config.reload()
    assert config.VOICE == "en-GB-SoniaNeural"
    monkeypatch.undo()
    config.reload()


def test_every_language_has_every_spoken_text():
    assert set(i18n._TEXTS["en"]) == set(i18n._TEXTS["pt"])
    assert set(config.LANGUAGES) == set(i18n._TEXTS) == set(config.DEFAULT_VOICES)


def test_local_ollama_needs_no_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    config.reload()
    assert config.AI_CONFIGURED
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    config.reload()
    assert not config.AI_CONFIGURED
    monkeypatch.undo()
    config.reload()


def test_apply_writes_reloads_and_reports_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    for key in config.DEFAULTS:
        monkeypatch.delenv(key, raising=False)
    config.reload()

    restart = config.apply({"LLM_MODEL": "other-model", "MIC_INDEX": "2", "JUNK": "x"})
    assert restart == ["MIC_INDEX"]
    assert config.LLM_MODEL == "other-model" and config.MIC_INDEX == 2
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "LLM_MODEL=other-model" in text and "JUNK" not in text

    assert config.apply({"LLM_MODEL": "one-more"}) == []
    monkeypatch.undo()
    config.reload()


def test_empty_allowed_sites_means_none(monkeypatch):
    monkeypatch.setenv("ALLOWED_SITES", "")
    config.reload()
    assert config.ALLOWED_SITES == [] and config.current_values()["ALLOWED_SITES"] == ""
    monkeypatch.undo()
    config.reload()


def test_old_env_is_migrated_and_keeps_portuguese(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("LLM_API_KEY=k\nWAKEWORD_LIMIAR=0.3\nREPLICA=0\n", encoding="utf-8")
    monkeypatch.setattr(config, "ENV_FILE", env)
    config._migrate_env()
    values = config.envfile.read(env)
    assert values == {"LLM_API_KEY": "k", "WAKEWORD_THRESHOLD": "0.3", "FOLLOW_UP": "0", "LANGUAGE": "pt"}
    config._migrate_env()  # idempotent
    assert config.envfile.read(env) == values


def test_whisper_small_and_overlay_are_the_defaults(monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    monkeypatch.delenv("OVERLAY", raising=False)
    config.reload()
    assert config.WHISPER_MODEL == "small" and config.OVERLAY
    monkeypatch.setenv("OVERLAY", "0")
    config.reload()
    assert not config.OVERLAY
    monkeypatch.undo()
    config.reload()
