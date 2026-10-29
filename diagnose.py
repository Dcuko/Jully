"""Tests each microphone and the wake word. Run it and say "hey jarvis" several times."""
import time

import numpy as np
from pvrecorder import PvRecorder

import config
import listen

DURATION = 8

wake = listen.load_wakeword()
for i, name in enumerate(PvRecorder.get_available_devices()):
    rec = PvRecorder(frame_length=listen.FRAME, device_index=i)
    rec.start()
    print(f"\n[{i}] {name}\n    >>> SAY 'hey jarvis' now ({DURATION}s)", flush=True)
    wake.reset()
    t0, level, score = time.time(), 0.0, 0.0
    while time.time() - t0 < DURATION:
        f = np.array(rec.read(), dtype=np.int16)
        level = max(level, float(np.sqrt(np.mean(f.astype(np.float32) ** 2))))
        score = max(score, max(wake.predict(f).values()))
    rec.delete()
    print(f"    peak volume: {level:.0f}  |  'hey jarvis' score: {score:.2f} (triggers above {config.WAKEWORD_THRESHOLD})")

print("\nUse the index of the microphone with high volume: MIC_INDEX=<n> in the .env (or in the settings)")
