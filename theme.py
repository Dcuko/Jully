"""Colors and widgets shared by the main window and the settings window."""
import tkinter as tk
from tkinter import ttk

BG = "#16161e"
PANEL = "#1f2030"
FIELD = "#272a3d"
BORDER = "#34364d"
TEXT = "#e6e6ef"
MUTED = "#8b8ba3"
PURPLE = "#8a5cf6"
PURPLE_DARK = "#7448e0"
BUBBLE_JULLY = "#2a2b3d"
RED = "#e5484d"
AMBER = "#f5a524"
GREEN = "#3fb68b"

FONT = "Segoe UI"


class FlatButton(tk.Label):
    """Flat button with a hover effect (the native Windows tk.Button ignores colors)."""

    def __init__(self, parent, text, command, color=PURPLE, hover=PURPLE_DARK, fg="white",
                 font=(FONT, 10, "bold"), padx=14, pady=6):
        super().__init__(parent, text=text, bg=color, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
        self._color, self._hover, self._command, self._fg, self._enabled = color, hover, command, fg, True
        self.bind("<Enter>", lambda e: self._enabled and super(FlatButton, self).configure(bg=self._hover))
        self.bind("<Leave>", lambda e: super(FlatButton, self).configure(bg=self._color))
        self.bind("<ButtonRelease-1>", self._clicked)

    def _clicked(self, event):
        if self._enabled and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self._command()

    def set_color(self, color, hover=None):
        self._color, self._hover = color, hover or color
        super().configure(bg=color)

    def enable(self, enabled):
        self._enabled = enabled
        super().configure(cursor="hand2" if enabled else "arrow", fg=self._fg if enabled else MUTED)


def apply_style(root):
    """Give the ttk widgets (combobox and slider) the dark look."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, arrowcolor=MUTED,
                    selectbackground=FIELD, selectforeground=TEXT, padding=5)
    style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)],
              selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)],
              bordercolor=[("focus", PURPLE)])
    style.configure("Horizontal.TScale", background=PANEL, troughcolor=FIELD, bordercolor=PANEL,
                    lightcolor=PURPLE, darkcolor=PURPLE)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", PURPLE)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))
