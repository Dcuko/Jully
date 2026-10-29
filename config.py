import os
import re
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

import envfile

ROOT = Path(__file__).parent
ENV_FILE = ROOT / ".env"

# Setting names used before the project was translated to English.
LEGACY_KEYS = {
    "WAKEWORD_LIMIAR": "WAKEWORD_THRESHOLD",
    "MIC_GANHO": "MIC_GAIN",
    "VOZ_LIMIAR_MIN": "MIN_SPEECH_LEVEL",
    "VOZ": "VOICE",
    "VELOCIDADE_VOZ": "VOICE_RATE",
    "REPLICA": "FOLLOW_UP",
    "VER_TELA": "SCREEN_CAPTURE",
    "CIDADE": "CITY",
    "SITES_PERMITIDOS": "ALLOWED_SITES",
}


def _migrate_env():
    # Old installs spoke Portuguese only, so keep that language when upgrading.
    if envfile.rename_keys(ENV_FILE, LEGACY_KEYS) and "LANGUAGE" not in envfile.read(ENV_FILE):
        envfile.save(ENV_FILE, {"LANGUAGE": "pt"})


_migrate_env()
load_dotenv(ENV_FILE)

# Languages Jully can speak and understand: name used in the prompt and default voice.
LANGUAGES = {"en": "English", "pt": "Brazilian Portuguese"}
DEFAULT_VOICES = {"en": "en-US-AriaNeural", "pt": "pt-BR-FranciscaNeural"}

# Defaults for everything that can be set in the .env (and in the settings window).
DEFAULTS = {
    "LLM_API_KEY": "",
    "LLM_BASE_URL": "https://api.groq.com/openai/v1",
    "LLM_MODEL": "llama-3.1-8b-instant",
    "LLM_VISION_MODEL": "meta-llama/llama-4-scout-17b-16e-instruct",
    "LANGUAGE": "en",
    "WHISPER_MODEL": "base",
    "WHISPER_DEVICE": "cpu",
    "VOICE": "",  # empty = default voice of the language
    "VOICE_RATE": "+10%",
    "WAKEWORD": "hey_jarvis",
    "WAKEWORD_THRESHOLD": "0.35",
    "MIC_INDEX": "-1",
    "MIC_GAIN": "3",
    "MIN_SPEECH_LEVEL": "200",
    "FOLLOW_UP": "1",
    "SCREEN_CAPTURE": "screen",
    "CITY": "",
    "ALLOWED_SITES": "google.com, youtube.com, github.com, wikipedia.org, whatsapp.com, "
                     "spotify.com, netflix.com, twitch.tv, reddit.com, linkedin.com",
}

# Changes to these keys only apply after a restart (the microphone and detector stay open).
RESTART_KEYS = {"WAKEWORD", "MIC_INDEX"}

# Recording after the wake word
END_SILENCE_S = 0.8      # silence that ends the request
SPEECH_WAIT_S = 3.0      # give up if nobody speaks
MAX_REQUEST_S = 12.0

# Short conversation memory
HISTORY_MAX_MSGS = 12
HISTORY_TTL_S = 300

# Only these names can be opened by voice (besides the allowed sites)
HOME = Path.home()
APPS = {
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "settings": "ms-settings:",
    "downloads": str(HOME / "Downloads"),
    "documents": str(HOME / "Documents"),
    "pictures": str(HOME / "Pictures"),
    "desktop": str(HOME / "Desktop"),
}

SCREENSHOTS_DIR = HOME / "Pictures" / "Jully Screenshots"
NOTES_FILE = HOME / "Documents" / "Jully Notes" / "notes.txt"
TIMERS_FILE = ROOT / "timers.json"


def _text(key):
    return os.environ.get(key, "").strip() or DEFAULTS[key]


def _number(key, kind):
    try:
        return kind(os.environ.get(key, "").strip() or DEFAULTS[key])
    except ValueError:
        return kind(DEFAULTS[key])


def _is_local(url):
    return (urlparse(url).hostname or "") in ("localhost", "127.0.0.1", "::1")


def reload():
    """Read the environment again and update this module's settings."""
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_VISION_MODEL, AI_CONFIGURED, LANGUAGE
    global WHISPER_MODEL, WHISPER_DEVICE, VOICE, VOICE_RATE
    global WAKEWORD, WAKEWORD_THRESHOLD, MIC_INDEX, MIC_GAIN, MIN_SPEECH_LEVEL
    global FOLLOW_UP, SCREEN_CAPTURE, CITY, ALLOWED_SITES

    LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
    LLM_BASE_URL = _text("LLM_BASE_URL")
    LLM_MODEL = _text("LLM_MODEL")
    LLM_VISION_MODEL = _text("LLM_VISION_MODEL")
    AI_CONFIGURED = bool(LLM_API_KEY) or _is_local(LLM_BASE_URL)  # local Ollama needs no key

    LANGUAGE = _text("LANGUAGE")
    if LANGUAGE not in LANGUAGES:
        LANGUAGE = DEFAULTS["LANGUAGE"]
    WHISPER_MODEL = _text("WHISPER_MODEL")
    WHISPER_DEVICE = _text("WHISPER_DEVICE")
    VOICE = os.environ.get("VOICE", "").strip() or DEFAULT_VOICES[LANGUAGE]
    VOICE_RATE = _text("VOICE_RATE")
    if not re.fullmatch(r"[+-]\d+%", VOICE_RATE):
        VOICE_RATE = DEFAULTS["VOICE_RATE"]

    # Wake word (openWakeWord): the name of a ready-made model ("hey_jarvis")
    # or the path to a .onnx you trained (e.g. models/hey_jully.onnx).
    wake = _text("WAKEWORD")
    WAKEWORD = str(ROOT / wake) if wake.endswith((".onnx", ".tflite")) else wake
    WAKEWORD_THRESHOLD = _number("WAKEWORD_THRESHOLD", float)
    MIC_INDEX = _number("MIC_INDEX", int)  # -1 = Windows default
    MIC_GAIN = _number("MIC_GAIN", int)  # amplifies weak microphones
    MIN_SPEECH_LEVEL = _number("MIN_SPEECH_LEVEL", float)  # minimum volume that counts as speech

    FOLLOW_UP = _text("FOLLOW_UP") == "1"  # keep listening after a reply, no wake word needed
    SCREEN_CAPTURE = _text("SCREEN_CAPTURE")  # "screen" (all monitors) or "window" (active window only)
    CITY = os.environ.get("CITY", "").strip()
    ALLOWED_SITES = [
        s.strip().lower().removeprefix("www.")
        for s in os.environ.get("ALLOWED_SITES", DEFAULTS["ALLOWED_SITES"]).split(",")
        if s.strip()
    ]


def current_values():
    """Settings as they are in the environment, with defaults where empty (to fill the settings window)."""
    values = {}
    for key in DEFAULTS:
        if key in ("LLM_API_KEY", "CITY"):  # empty is a valid value
            values[key] = os.environ.get(key, "").strip()
        elif key == "ALLOWED_SITES":  # empty = no site allowed
            values[key] = os.environ.get(key, DEFAULTS[key]).strip()
        else:
            values[key] = _text(key)
    values["VOICE"] = VOICE
    return values


def apply(new):
    """Write to the .env, update the environment and reload. Returns the keys that need a restart."""
    before = current_values()
    new = {k: str(v).strip() for k, v in new.items() if k in DEFAULTS}
    envfile.save(ENV_FILE, new, template=ROOT / ".env.example")
    os.environ.update(new)
    reload()
    after = current_values()
    return sorted(k for k in RESTART_KEYS if before[k] != after[k])


reload()
