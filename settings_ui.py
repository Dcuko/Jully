"""Settings window: edits the .env without opening the file."""
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import config
import llm
import speak
from theme import BORDER, FIELD, FONT, BG, GREEN, MUTED, PANEL, PURPLE, RED, TEXT, FlatButton

# name -> (API address, text model, vision model); None keeps what is already in the fields
PROVIDERS = {
    "Groq (free)": ("https://api.groq.com/openai/v1", "llama-3.1-8b-instant",
                    "meta-llama/llama-4-scout-17b-16e-instruct"),
    "OpenRouter": ("https://openrouter.ai/api/v1", None, None),
    "Google Gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", None, None),
    "Ollama (local)": ("http://localhost:11434/v1", None, None),
    "Other": (None, None, None),
}
SUGGESTED_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]
VISION_MODELS = ["meta-llama/llama-4-scout-17b-16e-instruct"]
LANGUAGE_NAMES = {"en": "English", "pt": "Português (Brasil)"}
VOICES = ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural",
          "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural",
          "pt-PT-RaquelNeural", "pt-PT-DuarteNeural"]
WHISPER = ["tiny", "base", "small", "medium"]
WINDOWS_DEFAULT = "Windows default"
CAPTURE_SCOPES = {"screen": "Whole screen (all monitors)", "window": "Active window only"}
TABS = ["AI", "Voice", "Wake word", "General"]


def _provider_of(url):
    for name, (u, _, _) in PROVIDERS.items():
        if u and u.rstrip("/") == url.rstrip("/"):
            return name
    return "Other"


def _microphones():
    try:
        from pvrecorder import PvRecorder
        return PvRecorder.get_available_devices()
    except Exception:
        return []


class SettingsWindow:
    def __init__(self, parent, on_save, on_restart):
        self._on_save = on_save
        self._on_restart = on_restart
        self._queue = queue.Queue()  # results of threaded tasks (test AI, hear voice)
        self._microphones = _microphones()
        self.vars = {}

        self.top = top = tk.Toplevel(parent)
        top.title("Jully settings")
        top.geometry("540x660")
        top.minsize(480, 580)
        top.configure(bg=BG)
        top.transient(parent)

        self._build_footer()
        self._build_tabs()
        self._load(config.current_values())
        self.top.after(100, self._process)
        top.focus_set()

    # ---- layout ----

    def _build_footer(self):
        footer = tk.Frame(self.top, bg=PANEL, padx=14, pady=12)
        footer.pack(side="bottom", fill="x")
        self.notice = tk.Label(footer, bg=PANEL, fg=RED, font=(FONT, 9), anchor="w",
                               wraplength=300, justify="left")
        self.notice.pack(side="left", fill="x", expand=True)
        FlatButton(footer, "Save", self._save).pack(side="right")
        FlatButton(footer, "Cancel", self.top.destroy, color=FIELD, hover=BORDER, fg=TEXT).pack(side="right", padx=(0, 8))

    def _build_tabs(self):
        bar = tk.Frame(self.top, bg=BG, padx=14, pady=10)
        bar.pack(side="top", fill="x")
        self._body = tk.Frame(self.top, bg=BG, padx=14)
        self._body.pack(side="top", fill="both", expand=True)

        self._tab_buttons, self._pages = {}, {}
        for name in TABS:
            b = FlatButton(bar, name, lambda n=name: self._show_tab(n), font=(FONT, 10, "bold"), padx=14, pady=5)
            b.pack(side="left", padx=(0, 6))
            self._tab_buttons[name] = b
            self._pages[name] = tk.Frame(self._body, bg=PANEL, padx=16, pady=14)

        self._page_ai(self._pages["AI"])
        self._page_voice(self._pages["Voice"])
        self._page_wake(self._pages["Wake word"])
        self._page_general(self._pages["General"])
        self._show_tab("AI")

    def _show_tab(self, name):
        for n, page in self._pages.items():
            page.pack_forget()
            self._tab_buttons[n].set_color(PURPLE if n == name else FIELD, PURPLE if n == name else BORDER)
        self._pages[name].pack(fill="both", expand=True, pady=(0, 6))

    # ---- field helpers ----

    def _label(self, parent, text, hint=None):
        tk.Label(parent, text=text, bg=PANEL, fg=TEXT, font=(FONT, 10, "bold"), anchor="w").pack(fill="x", pady=(8, 0))
        if hint:
            tk.Label(parent, text=hint, bg=PANEL, fg=MUTED, font=(FONT, 8), anchor="w",
                     wraplength=440, justify="left").pack(fill="x")

    def _entry(self, parent, key, secret=False):
        var = self.vars[key] = tk.StringVar()
        frame = tk.Frame(parent, bg=FIELD, highlightthickness=1, highlightbackground=BORDER, highlightcolor=PURPLE)
        frame.pack(fill="x", pady=(3, 0))
        e = tk.Entry(frame, textvariable=var, bg=FIELD, fg=TEXT, insertbackground=TEXT, bd=0,
                     highlightthickness=0, font=(FONT, 10), show="•" if secret else "")
        e.pack(side="left", fill="x", expand=True, ipady=6, padx=8)
        if secret:
            def toggle():
                e.configure(show="" if e.cget("show") else "•")
            FlatButton(frame, "👁", toggle, color=FIELD, hover=BORDER, fg=MUTED, font=("Segoe UI Emoji", 10),
                       padx=8, pady=2).pack(side="right")
        return e

    def _combo(self, parent, key, values, editable=True):
        var = self.vars[key] = tk.StringVar()
        c = ttk.Combobox(parent, textvariable=var, values=values, state="normal" if editable else "readonly",
                         font=(FONT, 10))
        c.pack(fill="x", pady=(3, 0))
        return c

    def _slider(self, parent, key, low, high, step, fmt):
        var = self.vars[key] = tk.DoubleVar()
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=(3, 0))
        value = tk.Label(row, bg=PANEL, fg=MUTED, font=(FONT, 9), width=8, anchor="e")

        def changed(v):
            v = round(float(v) / step) * step
            var.set(v)
            value.configure(text=fmt(v))

        ttk.Scale(row, from_=low, to=high, variable=var, command=changed).pack(side="left", fill="x", expand=True)
        value.pack(side="right")
        var.trace_add("write", lambda *_: value.configure(text=fmt(var.get())))
        return var

    def _button(self, parent, text, command):
        b = FlatButton(parent, text, command, color=FIELD, hover=BORDER, fg=TEXT, font=(FONT, 9, "bold"),
                       padx=10, pady=5)
        b.pack(anchor="w", pady=(8, 0))
        return b

    # ---- pages ----

    def _page_ai(self, p):
        self._label(p, "Provider", "Any OpenAI-compatible API works. Picking one fills in the address.")
        c = self._combo(p, "_provider", list(PROVIDERS), editable=False)
        c.bind("<<ComboboxSelected>>", lambda e: self._pick_provider())

        self._label(p, "API key", "Stays only in your .env. Local Ollama needs no key.")
        self._entry(p, "LLM_API_KEY", secret=True)
        link = tk.Label(p, text="Get a free key from Groq", bg=PANEL, fg=PURPLE, cursor="hand2",
                        font=(FONT, 9, "underline"), anchor="w")
        link.pack(fill="x", pady=(2, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))

        self._label(p, "API address")
        self._entry(p, "LLM_BASE_URL")
        self._label(p, "Text model")
        self._combo(p, "LLM_MODEL", SUGGESTED_MODELS)
        self._label(p, "Vision model", "Used for \"what's on my screen?\".")
        self._combo(p, "LLM_VISION_MODEL", VISION_MODELS)

        row = tk.Frame(p, bg=PANEL)
        row.pack(fill="x")
        self._test_button = FlatButton(row, "Test connection", self._test_ai, color=FIELD, hover=BORDER, fg=TEXT,
                                       font=(FONT, 9, "bold"), padx=10, pady=5)
        self._test_button.pack(side="left", pady=(10, 0))
        self._ai_result = tk.Label(row, bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w",
                                   wraplength=300, justify="left")
        self._ai_result.pack(side="left", padx=10, pady=(10, 0))

    def _page_voice(self, p):
        self._label(p, "Language", "What you speak and what Jully answers in. Also picks a default voice.")
        c = self._combo(p, "_language", list(LANGUAGE_NAMES.values()), editable=False)
        c.bind("<<ComboboxSelected>>", lambda e: self._pick_language())
        self._label(p, "Jully's voice", "Edge neural voices. You can type another name (edge-tts --list-voices).")
        self._combo(p, "VOICE", VOICES)
        self._label(p, "Speech rate")
        self._slider(p, "_rate", -50, 50, 5, lambda v: f"{v:+.0f}%")
        self._voice_button = self._button(p, "Hear a sample", self._test_voice)

        self._label(p, "Speech recognition model (Whisper)",
                    "Larger ones understand better but are slower and download the first time they are used.")
        self._combo(p, "WHISPER_MODEL", WHISPER)
        self._label(p, "Whisper device", "cuda only works with an NVIDIA card; if it fails, the CPU is used.")
        self._combo(p, "WHISPER_DEVICE", ["cpu", "cuda"], editable=False)

    def _page_wake(self, p):
        self._label(p, "Wake word",
                    "hey_jarvis (ready-made) or the path to a trained model, e.g. models/hey_jully.onnx. "
                    "Needs a restart.")
        self._entry(p, "WAKEWORD")
        self._label(p, "Sensitivity", "Further left triggers more easily (and misfires more).")
        self._slider(p, "WAKEWORD_THRESHOLD", 0.1, 0.9, 0.05, lambda v: f"{v:.2f}")

        self._label(p, "Microphone", "Needs a restart. Run diagnose.py if Jully can't hear you.")
        self._combo(p, "MIC_INDEX", [WINDOWS_DEFAULT] + [f"{i}: {n}" for i, n in enumerate(self._microphones)],
                    editable=False)
        self._label(p, "Microphone gain", "Amplifies weak microphones.")
        self._slider(p, "MIC_GAIN", 1, 10, 1, lambda v: f"{v:.0f}×")
        self._label(p, "Minimum volume that counts as speech", "Raise it if background noise keeps the recording going.")
        self._slider(p, "MIN_SPEECH_LEVEL", 50, 1000, 10, lambda v: f"{v:.0f}")

    def _page_general(self, p):
        for key, text in (("FOLLOW_UP", "Keep listening after a reply (no need to repeat the wake word)"),
                          ("OVERLAY", "Show a small status pill when Jully is listening or working "
                                      "(so you know when to speak even with the window closed)")):
            var = self.vars[key] = tk.BooleanVar()
            tk.Checkbutton(p, text=text, variable=var, bg=PANEL, fg=TEXT, selectcolor=FIELD,
                           activebackground=PANEL, activeforeground=TEXT, font=(FONT, 10), anchor="w",
                           wraplength=440, justify="left").pack(fill="x", pady=(2, 0))

        self._label(p, "What \"look at screen\" sends to the AI", "The capture goes to the provider chosen in the AI tab.")
        self._combo(p, "SCREEN_CAPTURE", list(CAPTURE_SCOPES.values()), editable=False)
        self._label(p, "Default weather city", "Used when you ask about the weather without naming a city.")
        self._entry(p, "CITY")
        self._label(p, "Websites Jully may open",
                    "Comma-separated domains (youtube.com also allows its subdomains). Use * to allow all.")
        self._entry(p, "ALLOWED_SITES")
        self._button(p, "Open .env file", lambda: os.startfile(config.ENV_FILE)
                     if config.ENV_FILE.exists() else None)

    # ---- values ----

    def _load(self, v):
        self.vars["_provider"].set(_provider_of(v["LLM_BASE_URL"]))
        self.vars["_language"].set(LANGUAGE_NAMES[v["LANGUAGE"]])
        self.vars["_rate"].set(int(v["VOICE_RATE"].rstrip("%")))
        for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_VISION_MODEL", "VOICE", "WHISPER_MODEL",
                    "WHISPER_DEVICE", "WAKEWORD", "CITY", "ALLOWED_SITES"):
            self.vars[key].set(v[key])
        for key in ("WAKEWORD_THRESHOLD", "MIC_GAIN", "MIN_SPEECH_LEVEL"):
            self.vars[key].set(float(v[key]))
        self.vars["FOLLOW_UP"].set(v["FOLLOW_UP"] == "1")
        self.vars["OVERLAY"].set(v["OVERLAY"] == "1")
        self.vars["SCREEN_CAPTURE"].set(CAPTURE_SCOPES.get(v["SCREEN_CAPTURE"], CAPTURE_SCOPES["screen"]))
        index = int(v["MIC_INDEX"])
        names = self._microphones
        self.vars["MIC_INDEX"].set(f"{index}: {names[index]}" if 0 <= index < len(names) else WINDOWS_DEFAULT)

    def _collect(self):
        """Read the fields and return {.env key: text}. Raises ValueError with a message for the user."""
        g = lambda k: self.vars[k].get()  # noqa: E731
        url = g("LLM_BASE_URL").strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("The API address must start with http:// or https://")
        if not g("LLM_MODEL").strip():
            raise ValueError("Enter the text model.")
        wake = g("WAKEWORD").strip() or "hey_jarvis"
        if wake.endswith((".onnx", ".tflite")) and not (config.ROOT / wake).exists():
            raise ValueError(f"The wake word file does not exist: {wake}")
        mic = g("MIC_INDEX")
        scope = next((k for k, t in CAPTURE_SCOPES.items() if t == g("SCREEN_CAPTURE")), "screen")
        language = next((k for k, n in LANGUAGE_NAMES.items() if n == g("_language")), "en")
        return {
            "LLM_API_KEY": g("LLM_API_KEY").strip(),
            "LLM_BASE_URL": url,
            "LLM_MODEL": g("LLM_MODEL").strip(),
            "LLM_VISION_MODEL": g("LLM_VISION_MODEL").strip(),
            "LANGUAGE": language,
            "VOICE": g("VOICE").strip(),
            "VOICE_RATE": f"{g('_rate'):+.0f}%",
            "WHISPER_MODEL": g("WHISPER_MODEL").strip(),
            "WHISPER_DEVICE": g("WHISPER_DEVICE"),
            "WAKEWORD": wake,
            "WAKEWORD_THRESHOLD": f"{g('WAKEWORD_THRESHOLD'):.2f}",
            "MIC_INDEX": "-1" if mic == WINDOWS_DEFAULT else mic.split(":")[0],
            "MIC_GAIN": f"{g('MIC_GAIN'):.0f}",
            "MIN_SPEECH_LEVEL": f"{g('MIN_SPEECH_LEVEL'):.0f}",
            "FOLLOW_UP": "1" if g("FOLLOW_UP") else "0",
            "OVERLAY": "1" if g("OVERLAY") else "0",
            "SCREEN_CAPTURE": scope,
            "CITY": g("CITY").strip(),
            "ALLOWED_SITES": ", ".join(s.strip() for s in g("ALLOWED_SITES").split(",") if s.strip()),
        }

    def _save(self):
        try:
            values = self._collect()
            restart = self._on_save(values)
        except ValueError as e:
            self.notice.configure(text=str(e))
            return
        except OSError as e:
            self.notice.configure(text=f"Could not write the .env: {e}")
            return
        self.top.destroy()
        if restart:
            names = {"WAKEWORD": "the wake word", "MIC_INDEX": "the microphone"}
            if messagebox.askyesno(
                    "Restart Jully?",
                    f"Settings saved. To apply {' and '.join(names[k] for k in restart)}, "
                    "Jully needs to restart. Restart now?"):
                self._on_restart()

    # ---- actions ----

    def _pick_provider(self):
        url, model, vision = PROVIDERS[self.vars["_provider"].get()]
        if url:
            self.vars["LLM_BASE_URL"].set(url)
        if model:
            self.vars["LLM_MODEL"].set(model)
        if vision:
            self.vars["LLM_VISION_MODEL"].set(vision)

    def _pick_language(self):
        code = next(k for k, n in LANGUAGE_NAMES.items() if n == self.vars["_language"].get())
        self.vars["VOICE"].set(config.DEFAULT_VOICES[code])

    def _in_thread(self, task, on_done):
        def run():
            self._queue.put((on_done, task()))
        threading.Thread(target=run, daemon=True).start()

    def _test_ai(self):
        self._test_button.enable(False)
        self._ai_result.configure(text="Testing…", fg=MUTED)
        key, url, model = (self.vars[k].get().strip() for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"))

        def done(result):
            ok, message = result
            self._test_button.enable(True)
            self._ai_result.configure(text=message, fg=GREEN if ok else RED)

        self._in_thread(lambda: llm.test(key, url, model), done)

    def _test_voice(self):
        self._voice_button.enable(False)
        voice = self.vars["VOICE"].get().strip() or None
        rate = f"{self.vars['_rate'].get():+.0f}%"
        language = next((k for k, n in LANGUAGE_NAMES.items() if n == self.vars["_language"].get()), "en")

        def play():
            try:
                sample = {"en": "Hi, I'm Jully.", "pt": "Oi, eu sou a Jully."}[language]
                speak.say(sample, voice=voice, rate=rate)
                return None
            except Exception as e:
                return f"Could not speak: {e}"

        def done(error):
            self._voice_button.enable(True)
            self.notice.configure(text=error or "")

        self._in_thread(play, done)

    def _process(self):
        if not self.top.winfo_exists():
            return
        try:
            while True:
                on_done, result = self._queue.get_nowait()
                on_done(result)
        except queue.Empty:
            pass
        self.top.after(100, self._process)
