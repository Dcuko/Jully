import logging
import threading
import time

import numpy as np
import openwakeword
from faster_whisper import WhisperModel
from openwakeword.model import Model
from pvrecorder import PvRecorder

import config

log = logging.getLogger("jully")

TAXA = 16000
FRAME = 1280  # 80 ms, tamanho esperado pelo openWakeWord


def _carregar_wakeword():
    modelo = config.WAKEWORD
    try:
        return Model(wakeword_models=[modelo], inference_framework="onnx")
    except Exception:
        openwakeword.utils.download_models()  # primeira execução: baixa os modelos
        return Model(wakeword_models=[modelo], inference_framework="onnx")


class Ouvido:
    def __init__(self):
        self.wake = _carregar_wakeword()
        self.recorder = PvRecorder(frame_length=FRAME, device_index=config.MIC_INDEX)
        self.recorder.start()

        # O Whisper carrega em segundo plano; só é usado quando há um pedido.
        self._whisper = None
        self._whisper_pronto = threading.Event()
        threading.Thread(target=self._carregar_whisper, daemon=True).start()

    def _carregar_whisper(self):
        self._whisper = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        self._whisper_pronto.set()

    def _ler(self):
        """Lê um quadro do microfone com ganho digital (microfones fracos)."""
        frame = np.array(self.recorder.read(), dtype=np.int32) * config.MIC_GANHO
        return np.clip(frame, -32768, 32767).astype(np.int16)

    def esperar_wake(self, deve_parar):
        """Bloqueia até ouvir a palavra de ativação. Retorna False se deve_parar() ficar verdadeiro."""
        self.wake.reset()
        while not deve_parar():
            frame = self._ler()
            melhor = max(self.wake.predict(frame).values())
            if melhor >= 0.15:
                log.info("wake score %.2f (limiar %.2f)", melhor, config.WAKEWORD_LIMIAR)
            if melhor >= config.WAKEWORD_LIMIAR:
                return True
        return False

    def gravar(self, espera=None):
        """Grava até o silêncio. Retorna float32 mono 16 kHz, ou None se ninguém falou em `espera` s."""
        espera = espera or config.ESPERA_FALA_S
        fps = TAXA / FRAME
        quadros, ruido = [], []
        falou = False
        silencio = 0
        inicio = None  # o relógio só começa quando o microfone já está entregando áudio

        while True:
            frame = self._ler()
            if inicio is None:
                inicio = time.monotonic()
            quadros.append(frame)
            rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))

            if len(ruido) < 3:  # ~240 ms para medir o ruído de fundo
                ruido.append(rms)
                continue
            limiar = max(config.VOZ_LIMIAR_MIN, min(ruido) * 3)  # mínimo: ignora voz que já tenha começado

            decorrido = time.monotonic() - inicio
            if rms > limiar:
                falou, silencio = True, 0
            elif falou:
                silencio += 1
                if silencio / fps >= config.SILENCIO_FIM_S:
                    break
            if not falou and decorrido > espera:
                return None
            if decorrido > config.MAX_PEDIDO_S:
                break

        if not falou:
            return None
        return np.concatenate(quadros).astype(np.float32) / 32768.0

    def transcrever(self, audio):
        self._whisper_pronto.wait()
        segmentos, _ = self._whisper.transcribe(
            audio,
            language="pt",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segmentos).strip()

    def pausar(self):
        self.recorder.stop()

    def retomar(self):
        self.recorder.start()

    def fechar(self):
        self.recorder.delete()
