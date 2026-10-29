"""A tiny, semi-transparent pill in the top-left corner that shows what Jully is doing, even when her window is closed.

It never takes the focus and the mouse goes straight through it, so it cannot get in the way.
"""
import ctypes
import tkinter as tk

from theme import BORDER, FONT, MUTED, PANEL, TEXT

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020  # clicks go through
WS_EX_TOOLWINDOW = 0x00000080  # no taskbar button
WS_EX_NOACTIVATE = 0x08000000  # never takes the focus

MARGIN = 10  # px from the top-left corner of the screen
OPACITY = 0.7


class Overlay:
    def __init__(self, root):
        self.top = tk.Toplevel(root)
        self.top.withdraw()
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", OPACITY)
        self.top.configure(bg=BORDER)

        body = tk.Frame(self.top, bg=PANEL, padx=9, pady=4)
        body.pack(padx=1, pady=1)
        row = tk.Frame(body, bg=PANEL)
        row.pack()
        self.dot = tk.Canvas(row, width=8, height=8, bg=PANEL, highlightthickness=0)
        self._shape = self.dot.create_oval(0, 0, 8, 8, fill=MUTED, outline="")
        self.dot.pack(side="left", padx=(0, 6))
        self.label = tk.Label(row, bg=PANEL, fg=TEXT, font=(FONT, 8, "bold"))
        self.label.pack(side="left")
        self.detail = tk.Label(body, bg=PANEL, fg=MUTED, font=(FONT, 7), wraplength=220, justify="left")

        self._hide_job = None
        self._make_unobtrusive()

    def _make_unobtrusive(self):
        self.top.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.top.winfo_id()) or self.top.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)

    def show(self, label, color, detail="", hide_after_ms=None):
        if self._hide_job is not None:
            self.top.after_cancel(self._hide_job)
            self._hide_job = None
        self.dot.itemconfigure(self._shape, fill=color)
        self.label.configure(text=label)
        if detail:
            self.detail.configure(text=detail)
            self.detail.pack(anchor="w", pady=(2, 0))
        else:
            self.detail.pack_forget()
        self.top.update_idletasks()
        self.top.geometry(f"+{MARGIN}+{MARGIN}")
        self.top.deiconify()
        self.top.attributes("-topmost", True)
        if hide_after_ms:
            self._hide_job = self.top.after(hide_after_ms, self.hide)

    def hide(self):
        self._hide_job = None
        self.top.withdraw()
