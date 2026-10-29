import ctypes
import logging
import queue
import subprocess
import sys
import threading
import winsound
from ctypes import wintypes
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

import config
import tools

logging.basicConfig(
    filename=config.ROOT / "jully.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("jully")
for noisy in ("httpx", "httpcore", "huggingface_hub", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

stop = threading.Event()
paused = threading.Event()
requests = queue.Queue()  # requests from the window: ("text", str) or ("mic", None)
window = None
restart = False
instance_lock = None


def fatal_error(msg):
    log.error(msg)
    ctypes.windll.user32.MessageBoxW(0, msg, "Jully", 0x10)
    sys.exit(1)


def acquire_single_instance():
    """Two Jullys would fight over the microphone: the second one tells the user and exits."""
    global instance_lock
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    instance_lock = kernel32.CreateMutexW(None, False, "Jully.SingleInstance")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(0, "Jully is already running. Look for its icon in the system tray.",
                                         "Jully", 0x40)
        sys.exit(0)


def validate():
    missing = []  # the AI key is not checked here: if it is missing, the settings window opens by itself
    if config.WAKEWORD.endswith((".onnx", ".tflite")) and not Path(config.WAKEWORD).exists():
        missing.append(f"file {config.WAKEWORD}")
    if missing:
        fatal_error("Something is not configured:\n- " + "\n- ".join(missing) + "\n\nFix it in the .env (see the README).")


def loop():
    try:
        _loop()
    except Exception:
        log.exception("the main loop crashed")
        fatal_error("Jully stopped because of an error. See jully.log.")


def _loop():
    import brain
    import speak
    from listen import Ear

    try:
        ear = Ear()
    except Exception as e:
        fatal_error(f"Could not start the microphone/wake word:\n{e}")

    def interrupted():
        return stop.is_set() or paused.is_set() or not requests.empty()

    log.info("Jully ready, waiting for the wake word (%s)", config.WAKEWORD)
    follow_up = False  # right after a reply, listen for a continuation without the wake word
    while not stop.is_set():
        kind, value = None, None

        if paused.is_set():  # paused: only the window (text and microphone) works
            try:
                kind, value = requests.get(timeout=0.2)
            except queue.Empty:
                continue
        elif not requests.empty():
            kind, value = requests.get_nowait()
        elif follow_up:
            kind = "follow_up"
        elif ear.wait_for_wake(interrupted):
            kind = "wake"
        else:
            continue

        follow_up = False
        if kind in ("wake", "mic", "follow_up"):
            if kind == "wake":
                log.info("wake word detected")
                winsound.Beep(880, 120)
            elif kind == "mic":
                ear.pause()  # drop stale audio from the buffer
                ear.resume()
            window.set_status("Listening…")
            audio = ear.record()  # same as after the wake word: waits for you to start and cuts at the silence
            if audio is None:
                window.set_status("")
                if kind != "follow_up":  # silence after a reply is normal; after a wake word it is not
                    window.notify("Didn't hear anything")
                continue
            window.set_status("Transcribing…")
            text = ear.transcribe(audio)
        else:
            text = value

        log.info("request: %s", text)
        if not text:
            window.set_status("")
            window.notify("Didn't catch that")
            continue

        window.add("you", text)
        window.set_status("Thinking…")
        answer = brain.reply(text)
        log.info("answer: %s", answer)
        window.add("jully", answer)

        window.set_status("Speaking…")
        ear.pause()  # do not listen to her own voice
        try:
            speak.say(answer)
        except Exception:
            log.exception("error while speaking")
        ear.resume()
        window.set_status("")
        follow_up = config.FOLLOW_UP and kind != "text"

    ear.close()


def tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(138, 92, 246, 255))
    d.rectangle((26, 16, 38, 40), fill="white")
    d.ellipse((26, 36, 38, 48), fill="white")
    return img


def apply_settings(values):
    """Called by the settings window: write to the .env and return what needs a restart."""
    log.info("settings saved: %s", sorted(values))
    return config.apply(values)


def clear_history():
    import brain
    brain.clear_history()


def request_restart():
    global restart
    restart = True
    stop.set()
    window.close()


def main():
    global window
    acquire_single_instance()
    validate()

    from ui import Window

    no_ai = not config.AI_CONFIGURED
    # "--oculto" is the old name of the flag, kept so existing startup shortcuts still work
    hidden = ("--hidden" in sys.argv or "--oculto" in sys.argv) and not no_ai

    icon = tray_icon()
    window = Window(
        on_send=lambda t: requests.put(("text", t)),
        on_mic=lambda: requests.put(("mic", None)),
        on_save_settings=apply_settings,
        on_restart=request_restart,
        on_clear=clear_history,
        icon=icon,
        hidden=hidden,
    )
    resumed = tools.resume_timers()
    if resumed:
        log.info("%d timer(s) resumed", resumed)
    threading.Thread(target=loop, daemon=True).start()

    def toggle(ic, item):
        paused.clear() if paused.is_set() else paused.set()

    menu = pystray.Menu(
        pystray.MenuItem("Open window", lambda ic, item: window.show(), default=True),
        pystray.MenuItem("Settings", lambda ic, item: window.open_settings()),
        pystray.MenuItem("Pause wake word", toggle, checked=lambda item: paused.is_set()),
        pystray.MenuItem("Quit", lambda ic, item: (stop.set(), window.close())),
    )
    tray = pystray.Icon("Jully", icon, "Jully", menu)
    tray.run_detached()

    if no_ai:
        window.add("notice", "The AI key is missing. Fill it in on the AI tab of the settings.")
        window.open_settings()

    window.run()
    tray.stop()
    if restart:
        ctypes.windll.kernel32.CloseHandle(instance_lock)  # let the new process take the lock
        subprocess.Popen([sys.executable] + [a for a in sys.argv if a not in ("--hidden", "--oculto")],
                         cwd=config.ROOT)


if __name__ == "__main__":
    main()
