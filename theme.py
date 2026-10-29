"""Colors and widgets shared by the main window and the settings window."""
import tkinter as tk
from tkinter import ttk

# Palette built around the logo orange (assets/logo.svg)
BG = "#17130f"
PANEL = "#201b17"
FIELD = "#2a241f"
BORDER = "#3d352e"
TEXT = "#f3ede6"
MUTED = "#a0968c"
ACCENT = "#e66d28"
ACCENT_DARK = "#c95a1a"
ON_ACCENT = "#1b130e"  # text on the accent color (white would be too faint on this orange)
BUBBLE_JULLY = "#2c2621"
RED = "#e5484d"
AMBER = "#f5a524"
GREEN = "#3fb68b"

FONT = "Segoe UI"


class FlatButton(tk.Label):
    """Flat button with a hover effect (the native Windows tk.Button ignores colors)."""

    def __init__(self, parent, text, command, color=ACCENT, hover=ACCENT_DARK, fg=ON_ACCENT,
                 font=(FONT, 10, "bold"), padx=14, pady=6):
        super().__init__(parent, text=text, bg=color, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
        self._color, self._hover, self._command, self._fg, self._enabled = color, hover, command, fg, True
        self.bind("<Enter>", lambda e: self._enabled and super(FlatButton, self).configure(bg=self._hover))
        self.bind("<Leave>", lambda e: super(FlatButton, self).configure(bg=self._color))
        self.bind("<ButtonRelease-1>", self._clicked)

    def _clicked(self, event):
        if self._enabled and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self._command()

    def set_color(self, color, hover=None, fg=None):
        self._color, self._hover = color, hover or color
        if fg is not None:
            self._fg = fg
        super().configure(bg=color, fg=self._fg if self._enabled else MUTED)

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
              bordercolor=[("focus", ACCENT)])
    style.configure("Horizontal.TScale", background=PANEL, troughcolor=FIELD, bordercolor=PANEL,
                    lightcolor=ACCENT, darkcolor=ACCENT)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", ON_ACCENT)
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))
