import ast
import base64
import ctypes
import io
import json
import logging
import operator
import os
import threading
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser
from datetime import datetime

import pyperclip
import win32clipboard
import win32gui
from PIL import ImageGrab

import config
import i18n
import llm
import speak

log = logging.getLogger("jully")

# ---------- tool schemas ----------

SCHEMAS = [
    {
        "name": "calculate",
        "description": "Evaluate a math expression (+ - * / ** % //, parentheses). Use a dot as the decimal separator.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "copy_to_clipboard",
        "description": "Put a text on the user's clipboard.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "read_clipboard",
        "description": "Read the text currently on the clipboard.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot of the whole screen, save it to a file and copy the image to the clipboard.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "look_at_screen",
        "description": "Look at the user's screen and answer a question about it (what is open, read a text, etc.).",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "open_target",
        "description": f"Open an app, folder or website: one of {', '.join(config.APPS)}, or a full http/https URL.",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
    },
    {
        "name": "date_and_time",
        "description": "Return the current date and time.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "timer",
        "description": "Announce a message by voice after a number of seconds.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer", "minimum": 1},
                "message": {"type": "string", "description": "What to say when the time is up."},
            },
            "required": ["seconds", "message"],
        },
    },
    {
        "name": "reminder",
        "description": "Announce a message by voice at a specific date and time (e.g. 'tomorrow at 9am'). "
                       "Use the current date and time to work it out.",
        "parameters": {
            "type": "object",
            "properties": {
                "when": {"type": "string", "description": "Local date and time as YYYY-MM-DDTHH:MM."},
                "message": {"type": "string", "description": "What to say at that time."},
            },
            "required": ["when", "message"],
        },
    },
    {
        "name": "take_note",
        "description": "Save a quick note to the user's notes file.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "volume",
        "description": "Control the Windows volume.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["up", "down", "mute", "set"]},
                "level": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Only for 'set'."},
            },
            "required": ["action"],
        },
    },
    {
        "name": "media",
        "description": "Control the music or video playing on the computer.",
        "parameters": {
            "type": "object",
            "properties": {"action": {"type": "string", "enum": ["play_pause", "next", "previous"]}},
            "required": ["action"],
        },
    },
    {
        "name": "weather",
        "description": "Tell today's weather and temperature for a city (uses the configured city if none is given).",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
        },
    },
    {
        "name": "lock_screen",
        "description": "Lock Windows.",
        "parameters": {"type": "object", "properties": {}},
    },
]


def schemas():
    """Current schemas: the list of sites in `open_target` changes with the settings."""
    result = []
    for s in SCHEMAS:
        if s["name"] == "open_target":
            sites = "any site" if "*" in config.ALLOWED_SITES else ", ".join(config.ALLOWED_SITES) or "no site"
            s = {**s, "description": f"Open one of: {', '.join(config.APPS)}; or a website (full https URL) "
                                     f"from these domains: {sites}."}
        result.append(s)
    return result


# ---------- implementations ----------

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _evaluate(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.operand))
    raise ValueError("invalid expression")


def calculate(expression):
    result = _evaluate(ast.parse(expression.strip(), mode="eval").body)
    if isinstance(result, float):
        result = round(result, 10)
        if result.is_integer():
            result = int(result)
    return str(result)


def copy_to_clipboard(text):
    pyperclip.copy(text)
    return "Copied."


def read_clipboard():
    text = pyperclip.paste()
    return text[:2000] if text else "(empty)"


def _copy_image(img):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "BMP")
    dib = buf.getvalue()[14:]  # CF_DIB does not take the BMP file header
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib)
    finally:
        win32clipboard.CloseClipboard()


def take_screenshot():
    img = ImageGrab.grab(all_screens=True)
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.SCREENSHOTS_DIR / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
    img.save(path)
    _copy_image(img)
    return f"Screenshot saved to {path} and copied to the clipboard."


def _capture():
    """Capture all monitors or only the active window, depending on SCREEN_CAPTURE."""
    if config.SCREEN_CAPTURE == "window":
        left, top, right, bottom = win32gui.GetWindowRect(win32gui.GetForegroundWindow())
        if right > left and bottom > top:
            return ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    return ImageGrab.grab(all_screens=True)


def look_at_screen(question):
    img = _capture().convert("RGB")
    img.thumbnail((1280, 1280))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    data = base64.b64encode(buf.getvalue()).decode()
    r = llm.client().chat.completions.create(
        model=config.LLM_VISION_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": [
            {"type": "text",
             "text": f"{question}\nAnswer briefly in {config.LANGUAGES[config.LANGUAGE]}."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}},
        ]}],
    )
    return r.choices[0].message.content


def site_allowed(url, allowed=None):
    """True if the address is http/https and its domain is in the list (or the list has '*')."""
    allowed = config.ALLOWED_SITES if allowed is None else allowed
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if "*" in allowed:
        return True
    host = parts.hostname.lower().removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in allowed)


def open_target(target):
    key = target.strip().lower()
    if key in config.APPS:
        os.startfile(config.APPS[key])
        return f"Opening {key}."
    if key.startswith(("http://", "https://")):
        if not site_allowed(target.strip()):
            return "That site is not in the allowed sites list. It can be allowed in the settings."
        webbrowser.open(target.strip())
        return "Site opened."
    return f"I can't open that. Options: {', '.join(config.APPS)} or an allowed website."


def date_and_time():
    return f"{datetime.now():%A, %Y-%m-%d, %H:%M}"


# Timers and reminders are kept on disk so they survive a restart.
_timers_lock = threading.Lock()


def _read_timers():
    try:
        return json.loads(config.TIMERS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _write_timers(items):
    config.TIMERS_FILE.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def _fire(timer_id, message, late=False):
    with _timers_lock:
        _write_timers([t for t in _read_timers() if t["id"] != timer_id])
    try:
        speak.say(i18n.t("late_reminder", message=message) if late else message)
    except Exception:
        log.exception("failed to speak the reminder")


def _start(timer_id, when, message):
    delay = when - time.time()
    t = threading.Timer(max(delay, 0), _fire, args=(timer_id, message, delay < -5))
    t.daemon = True
    t.start()


def _schedule(when, message):
    timer_id = uuid.uuid4().hex
    with _timers_lock:
        _write_timers(_read_timers() + [{"id": timer_id, "when": when, "message": message}])
    _start(timer_id, when, message)


def resume_timers():
    """Reschedule the timers that were pending when Jully was closed."""
    with _timers_lock:
        pending = _read_timers()
    for t in pending:
        _start(t["id"], t["when"], t["message"])
    return len(pending)


def timer(seconds, message):
    _schedule(time.time() + seconds, message)
    return f"Timer set for {seconds} seconds."


def reminder(when, message):
    target = datetime.fromisoformat(when)
    if target.tzinfo:
        target = target.astimezone().replace(tzinfo=None)
    if target <= datetime.now():
        return "That time has already passed."
    _schedule(target.timestamp(), message)
    return f"Reminder set for {target:%Y-%m-%d at %H:%M}."


def take_note(text):
    config.NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {text}\n")
    return "Note saved."


def _press(vk, times=1):
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)


def volume(action, level=None):
    MUTE, DOWN, UP = 0xAD, 0xAE, 0xAF  # each press changes 2%
    if action == "mute":
        _press(MUTE)
    elif action == "up":
        _press(UP, 5)
    elif action == "down":
        _press(DOWN, 5)
    elif action == "set" and level is not None:
        _press(DOWN, 50)
        _press(UP, round(level / 2))
    else:
        return "Give a level to set."
    return "Volume adjusted."


def media(action):
    keys = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1}
    if action not in keys:
        return "Invalid action."
    _press(keys[action])
    return "Done."


_WEATHER = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    80: "light showers", 81: "showers", 82: "heavy showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


def _get_json(url, **params):
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=8) as r:
        return json.load(r)


def weather(city=""):
    city = (city or config.CITY).strip()
    if not city:
        return "Tell me the city or set a default city in the settings."
    found = _get_json("https://geocoding-api.open-meteo.com/v1/search",
                      name=city, count=1, language=config.LANGUAGE).get("results")
    if not found:
        return f"I couldn't find the city {city}."
    place = found[0]
    d = _get_json("https://api.open-meteo.com/v1/forecast",
                  latitude=place["latitude"], longitude=place["longitude"], timezone="auto", forecast_days=1,
                  current="temperature_2m,apparent_temperature,weather_code",
                  daily="temperature_2m_max,temperature_2m_min,precipitation_probability_max")
    now, day = d["current"], d["daily"]
    return (f"{place['name']}: {_WEATHER.get(now['weather_code'], 'unknown conditions')}, "
            f"{now['temperature_2m']:.0f} degrees Celsius (feels like {now['apparent_temperature']:.0f}). "
            f"Today from {day['temperature_2m_min'][0]:.0f} to {day['temperature_2m_max'][0]:.0f} degrees, "
            f"{day['precipitation_probability_max'][0] or 0}% chance of rain.")


def lock_screen():
    ctypes.windll.user32.LockWorkStation()
    return "Screen locked."


_FUNCTIONS = {s["name"]: globals()[s["name"]] for s in SCHEMAS}


def execute(name, arguments):
    try:
        return _FUNCTIONS[name](**arguments)
    except Exception as e:
        return f"Error: {e}"
