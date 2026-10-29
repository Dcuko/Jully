import queue
import tkinter as tk
from datetime import datetime

from theme import (AMBER, BORDER, BUBBLE_JULLY, FIELD, FONT, BG, GREEN, MUTED, PANEL, PURPLE, RED,
                   TEXT, FlatButton, apply_style)

PLACEHOLDER = "Type a request…"

# status prefix -> (dot color, text shown)
_STATES = {
    "Listening": (RED, "Listening…"),
    "Transcribing": (AMBER, "Transcribing…"),
    "Thinking": (AMBER, "Thinking…"),
    "Speaking": (GREEN, "Speaking…"),
}


class Window:
    """Chat window. The public methods are safe to call from other threads."""

    def __init__(self, on_send, on_mic, on_save_settings, on_restart, on_clear, icon=None):
        self._on_send = on_send
        self._on_mic = on_mic
        self._on_save_settings = on_save_settings
        self._on_restart = on_restart
        self._on_clear = on_clear
        self._events = queue.Queue()
        self._settings = None

        self.root = tk.Tk()
        self.root.title("Jully")
        self.root.geometry("440x620")
        self.root.minsize(340, 360)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Escape>", lambda e: self.hide())
        apply_style(self.root)
        if icon is not None:
            from PIL import ImageTk
            self._icon = ImageTk.PhotoImage(icon)  # keep the reference
            self.root.iconphoto(True, self._icon)

        self._build_header()
        self._build_input()
        self._build_chat()
        self.set_status("")
        self.root.after(50, self._process)

    # ---- layout ----

    def _build_header(self):
        header = tk.Frame(self.root, bg=PANEL, padx=14, pady=10)
        header.pack(side="top", fill="x")

        self.dot = tk.Canvas(header, width=10, height=10, bg=PANEL, highlightthickness=0)
        self._dot_shape = self.dot.create_oval(1, 1, 9, 9, fill=MUTED, outline="")
        self.dot.pack(side="left", padx=(0, 8))
        tk.Label(header, text="Jully", bg=PANEL, fg=TEXT, font=(FONT, 13, "bold")).pack(side="left")
        self.status = tk.Label(header, bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.status.pack(side="left", padx=(10, 0))

        for text, command in (("⚙", self.open_settings), ("🗑", self._clear)):
            FlatButton(header, text, command, color=PANEL, hover=FIELD, fg=TEXT, font=("Segoe UI Emoji", 12),
                       padx=8, pady=2).pack(side="right")

    def _build_input(self):
        bar = tk.Frame(self.root, bg=PANEL, padx=10, pady=10)
        bar.pack(side="bottom", fill="x")

        field = tk.Frame(bar, bg=FIELD, highlightthickness=1, highlightbackground=BORDER, highlightcolor=PURPLE)
        field.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry = tk.Entry(field, bg=FIELD, fg=MUTED, insertbackground=TEXT, bd=0,
                              highlightthickness=0, font=(FONT, 11))
        self.entry.pack(fill="x", ipady=8, padx=10)
        self._placeholder = True
        self.entry.insert(0, PLACEHOLDER)
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<Return>", lambda e: self._send())

        self.mic_button = FlatButton(bar, "🎤", self._on_mic, font=("Segoe UI Emoji", 12), padx=10, pady=6)
        self.mic_button.pack(side="right")
        FlatButton(bar, "➤", self._send, font=(FONT, 12), padx=12, pady=6).pack(side="right", padx=(0, 6))

    def _build_chat(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(side="top", fill="both", expand=True)
        self.chat = tk.Text(
            frame, wrap="word", state="disabled", bg=BG, fg=TEXT, bd=0, highlightthickness=0,
            padx=14, pady=12, font=(FONT, 11), cursor="arrow", selectbackground=PURPLE)
        scroll = tk.Scrollbar(frame, command=self.chat.yview, bg=BG, troughcolor=BG, bd=0, width=8)
        self.chat.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.chat.pack(side="left", fill="both", expand=True)

        tag = self.chat.tag_configure
        tag("label_you", foreground=MUTED, justify="right", font=(FONT, 8), rmargin=8, spacing1=6)
        tag("label_jully", foreground=PURPLE, justify="left", font=(FONT, 8), lmargin1=8, spacing1=6)
        tag("you", background=PURPLE, foreground="white", justify="right",
            lmargin1=70, lmargin2=70, rmargin=8, spacing1=2, spacing3=6)
        tag("jully", background=BUBBLE_JULLY, foreground=TEXT, justify="left",
            lmargin1=8, lmargin2=8, rmargin=70, spacing1=2, spacing3=6)
        tag("notice", foreground=MUTED, justify="center", font=(FONT, 9), spacing1=6, spacing3=6,
            lmargin1=20, lmargin2=20, rmargin=20)
        self._insert("notice", "Say the wake word or type below.")

    # ---- thread-safe ----

    def add(self, role, text):
        self._events.put(("msg", role, text))

    def set_status(self, text):
        self._events.put(("status", text))

    def show(self):
        self._events.put(("show",))

    def open_settings(self):
        self._events.put(("settings",))

    def close(self):
        self._events.put(("close",))

    # ---- UI thread only ----

    def hide(self):
        self.root.withdraw()

    def _focus_in(self, _):
        if self._placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=TEXT)
            self._placeholder = False

    def _focus_out(self, _):
        if not self.entry.get():
            self.entry.insert(0, PLACEHOLDER)
            self.entry.configure(fg=MUTED)
            self._placeholder = True

    def _send(self):
        text = "" if self._placeholder else self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self._on_send(text)

    def _clear(self):
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._on_clear()
        self._insert("notice", "Conversation cleared.")

    def _set_status(self, text):
        color, label = MUTED, text or "Ready"
        for prefix, (c, l) in _STATES.items():
            if text.startswith(prefix):
                color, label = c, l
        self.dot.itemconfigure(self._dot_shape, fill=color)
        self.status.configure(text=label)
        self.mic_button.set_color(RED if color == RED else PURPLE, "#c93a3f" if color == RED else None)

    def _open_settings(self):
        from settings_ui import SettingsWindow
        if self._settings is not None and self._settings.top.winfo_exists():
            self._settings.top.lift()
            return
        self.root.deiconify()
        self._settings = SettingsWindow(self.root, self._on_save_settings, self._on_restart)

    def _process(self):
        try:
            while True:
                ev = self._events.get_nowait()
                if ev[0] == "msg":
                    self._insert(ev[1], ev[2])
                elif ev[0] == "status":
                    self._set_status(ev[1])
                elif ev[0] == "show":
                    self.root.deiconify()
                    self.root.lift()
                    self.entry.focus_set()
                elif ev[0] == "settings":
                    self._open_settings()
                elif ev[0] == "close":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(50, self._process)

    def _insert(self, role, text):
        self.chat.configure(state="normal")
        if role == "notice":
            self.chat.insert("end", text + "\n", "notice")
        else:
            name = "You" if role == "you" else "Jully"
            self.chat.insert("end", f"{name} · {datetime.now():%H:%M}\n", f"label_{role}")
            self.chat.insert("end", f" {text} \n", role)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def run(self, hidden=False):
        if hidden:
            self.root.withdraw()
        self.root.mainloop()
