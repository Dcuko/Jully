"""Jully launcher (built into Jully.exe).

First run: finds Python, creates the .venv and installs requirements.txt, showing the progress.
Every run after that: just starts Jully, without checking or installing anything.
Run with --reinstall to install the requirements again (e.g. after updating Jully).
"""
import ctypes
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "Scripts" / "python.exe"
VENV_PYTHONW = VENV / "Scripts" / "pythonw.exe"
MARKER = VENV / "jully_installed"
LOG_FILE = ROOT / "install.log"
MIN_VERSION = (3, 11)  # the pinned requirements need it
PYTHON_URL = "https://www.python.org/downloads/windows/"

NO_WINDOW = subprocess.CREATE_NO_WINDOW
_MODULES = ["openai", "dotenv", "openwakeword", "pvrecorder", "faster_whisper", "edge_tts", "pyperclip",
            "PIL", "win32clipboard", "pystray", "numpy", "miniaudio"]
_CHECK = ("import importlib.util as u, sys; "
          f"sys.exit(any(u.find_spec(m) is None for m in {_MODULES!r}))")


def clean_env():
    """Environment for child processes. A PyInstaller exe points TCL_LIBRARY and friends at its temporary
    folder, which would break the tkinter of the Jully it starts (and of the venv we create)."""
    drop = ("TCL_LIBRARY", "TK_LIBRARY", "PYTHONHOME", "PYTHONPATH")
    return {k: v for k, v in os.environ.items() if k not in drop and not k.startswith(("_PYI", "_MEI"))}


def run(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, creationflags=NO_WINDOW,
                          env=clean_env())


def find_python(runner=run):
    """Return the command of a Python >= MIN_VERSION, or None."""
    for cmd in (["py", "-3.13"], ["py", "-3.12"], ["py", "-3.11"], ["py", "-3"], ["python"], ["python3"]):
        try:
            r = runner(cmd + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"])
            version = tuple(map(int, r.stdout.split()))
        except (OSError, ValueError):
            continue
        if r.returncode == 0 and version >= MIN_VERSION:
            return cmd
    return None


def is_installed(runner=run):
    """True if the requirements are installed. The marker makes later runs instant."""
    if MARKER.exists():
        return True
    if VENV_PYTHONW.exists() and runner([VENV_PYTHON, "-c", _CHECK]).returncode == 0:
        MARKER.write_text("ok", encoding="utf-8")  # an install made by hand also counts
        return True
    return False


def start_jully(args):
    subprocess.Popen([str(VENV_PYTHONW), str(ROOT / "main.py"), *args], cwd=ROOT, env=clean_env(),
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


def already_running():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW(None, False, "Jully.Launcher")  # released when this process ends
    return ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS


def message(text, icon=0x40):
    ctypes.windll.user32.MessageBoxW(0, text, "Jully", icon)


class Installer:
    """Progress window; the work runs in a thread and talks to the window through a queue."""

    BG, PANEL, TEXT, MUTED, PURPLE = "#16161e", "#1f2030", "#e6e6ef", "#8b8ba3", "#8a5cf6"

    def __init__(self, args):
        self.args = args
        self.long_path_error = False
        self.events = queue.Queue()
        self.root = tk.Tk()
        self.root.title("Jully setup")
        self.root.geometry("560x380")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        tk.Label(self.root, text="Setting up Jully", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(18, 0))
        tk.Label(self.root, text="This only happens once and can take a few minutes.", bg=self.BG,
                 fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        self.status = tk.Label(self.root, text="Starting…", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 10),
                               anchor="w")
        self.status.pack(fill="x", padx=20, pady=(14, 4))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("J.Horizontal.TProgressbar", troughcolor=self.PANEL, background=self.PURPLE,
                        bordercolor=self.PANEL, lightcolor=self.PURPLE, darkcolor=self.PURPLE)
        self.bar = ttk.Progressbar(self.root, mode="indeterminate", style="J.Horizontal.TProgressbar")
        self.bar.pack(fill="x", padx=20)
        self.bar.start(12)
        self.log = tk.Text(self.root, height=10, bg=self.PANEL, fg=self.MUTED, bd=0, highlightthickness=0,
                           font=("Consolas", 8), state="disabled", wrap="none")
        self.log.pack(fill="both", expand=True, padx=20, pady=14)

        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(100, self._poll)
        threading.Thread(target=self._work, daemon=True).start()

    def _close(self):
        self.root.destroy()

    # ---- worker thread ----

    def _say(self, status):
        self.events.put(("status", status))

    def _line(self, text):
        self.events.put(("log", text))

    def _stream(self, cmd):
        """Run a command, forwarding its output to the window and the log file. Returns the exit code."""
        self._line("> " + " ".join(str(c) for c in cmd))
        proc = subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", cwd=ROOT, creationflags=NO_WINDOW, env=clean_env())
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                self.long_path_error |= "Long Path" in line
                self._line(line)
                if line.startswith(("Collecting", "Downloading", "Installing", "Successfully")):
                    self._say(line[:70])
        return proc.wait()

    def _fail(self, text):
        self.events.put(("fail", text))

    def _work(self):
        try:
            if not (ROOT / "requirements.txt").exists() or not (ROOT / "main.py").exists():
                return self._fail("requirements.txt and main.py must be in the same folder as Jully.exe.")
            if not VENV_PYTHON.exists():
                self._say("Looking for Python…")
                python = find_python()
                if python is None:
                    self.events.put(("python_missing",))
                    return
                self._say("Creating the virtual environment…")
                if self._stream(python + ["-m", "venv", str(VENV)]) != 0:
                    return self._fail("Could not create the virtual environment.")
            self._say("Installing the requirements…")
            code = self._stream([VENV_PYTHON, "-m", "pip", "install", "--disable-pip-version-check",
                                 "-r", ROOT / "requirements.txt"])
            if code != 0 and self.long_path_error:
                return self._fail("The folder path is too long for Windows. Move the Jully folder somewhere "
                                  "shorter, like C:\\Jully, and run Jully.exe again.")
            if code != 0:
                return self._fail("Installing the requirements failed. Check your internet connection and "
                                  "try again. Details are in install.log.")
            MARKER.write_text("ok", encoding="utf-8")
            self._say("Done! Starting Jully…")
            start_jully(self.args)
            self.events.put(("done",))
        except Exception as e:
            self._fail(f"Unexpected error: {e}")

    # ---- UI thread ----

    def _poll(self):
        try:
            while True:
                kind, *rest = self.events.get_nowait()
                if kind == "status":
                    self.status.configure(text=rest[0])
                elif kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", rest[0] + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                    with LOG_FILE.open("a", encoding="utf-8") as f:
                        f.write(rest[0] + "\n")
                elif kind == "python_missing":
                    self.bar.stop()
                    self.status.configure(text=f"Python {MIN_VERSION[0]}.{MIN_VERSION[1]} or newer is required.",
                                          fg="#e5484d")
                    message(f"Jully needs Python {MIN_VERSION[0]}.{MIN_VERSION[1]} or newer.\n\n"
                            "The download page will open now. During the installation, tick "
                            "\"Add python.exe to PATH\", then run Jully.exe again.", 0x30)
                    webbrowser.open(PYTHON_URL)
                    return self._close()
                elif kind == "fail":
                    self.bar.stop()
                    self.status.configure(text=rest[0], fg="#e5484d", wraplength=520, justify="left")
                    tk.Button(self.root, text="Close", command=self._close).pack(pady=(0, 12))
                elif kind == "done":
                    return self._close()
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


def main():
    args = sys.argv[1:]
    reinstall = "--reinstall" in args
    args = [a for a in args if a != "--reinstall"]
    if already_running():
        return
    if reinstall:
        MARKER.unlink(missing_ok=True)
        LOG_FILE.unlink(missing_ok=True)
    elif is_installed():
        return start_jully(args)
    Installer(args).root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a windowed exe has no console, so an error would vanish silently
        import traceback
        LOG_FILE.write_text(traceback.format_exc(), encoding="utf-8")
        message(f"Jully could not start. Details were saved in:\n{LOG_FILE}", 0x10)
