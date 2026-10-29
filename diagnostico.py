"""Testa cada microfone e a palavra de ativação. Rode e fale "hey jarvis" várias vezes."""
import time

import numpy as np
from pvrecorder import PvRecorder

import config
import ouvir

DURACAO = 8

wake = ouvir._carregar_wakeword()
for i, nome in enumerate(PvRecorder.get_available_devices()):
    rec = PvRecorder(frame_length=ouvir.FRAME, device_index=i)
    rec.start()
    print(f"\n[{i}] {nome}\n    >>> FALE 'hey jarvis' agora ({DURACAO}s)", flush=True)
    wake.reset()
    t0, nivel, score = time.time(), 0.0, 0.0
    while time.time() - t0 < DURACAO:
        f = np.array(rec.read(), dtype=np.int16)
        nivel = max(nivel, float(np.sqrt(np.mean(f.astype(np.float32) ** 2))))
        score = max(score, max(wake.predict(f).values()))
    rec.delete()
    print(f"    volume máx: {nivel:.0f}  |  pontuação 'hey jarvis': {score:.2f} (ativa acima de {config.WAKEWORD_LIMIAR})")

print("\nUse o índice do microfone com volume alto: MIC_INDEX=<n> no .env")
