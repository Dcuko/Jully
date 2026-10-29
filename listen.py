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

RATE = 16000
FRAME = 1280  # 80 ms, the size openWakeWord expects


def load_wakeword():
    name = config.WAKEWORD
    try:
        return Model(wakeword_models=[name], inference_framework="onnx")
    except Exception:
        openwakeword.utils.download_models()  # first run: download the models
        return Model(wakeword_models=[name], inference_framework="onnx")


class Ear:
    def __init__(self):
        self.wake = load_wakeword()
        self.recorder = PvRecorder(frame_length=FRAME, device_index=config.MIC_INDEX)
        self.recorder.start()

        # Whisper loads in the background; it is only used when there is a request.
        self._whisper = None
        self._whisper_config = None
        self._whisper_ready = threading.Event()
        threading.Thread(target=self._load_whisper, daemon=True).start()

    def _load_whisper(self):
        """Load (or reload) Whisper with the model and device from the settings."""
        model, device = config.WHISPER_MODEL, config.WHISPER_DEVICE
        loaded = None
        for dev in dict.fromkeys([device, "cpu"]):  # if the GPU fails, try the CPU
            try:
                loaded = WhisperModel(model, device=dev, compute_type="int8" if dev == "cpu" else "float16")
                break
            except Exception:
                log.exception("could not load whisper '%s' on %s", model, dev)
        if loaded is not None:  # on failure, keep the previous model
            self._whisper = loaded
        self._whisper_config = (model, device)
        self._whisper_ready.set()

    def _read(self):
        """Read one frame from the microphone with digital gain (weak microphones)."""
        frame = np.array(self.recorder.read(), dtype=np.int32) * config.MIC_GAIN
        return np.clip(frame, -32768, 32767).astype(np.int16)

    def wait_for_wake(self, should_stop):
        """Block until the wake word is heard. Returns False if should_stop() becomes true."""
        self.wake.reset()
        while not should_stop():
            frame = self._read()
            best = max(self.wake.predict(frame).values())
            if best >= 0.15:
                log.info("wake score %.2f (threshold %.2f)", best, config.WAKEWORD_THRESHOLD)
            if best >= config.WAKEWORD_THRESHOLD:
                return True
        return False

    def record(self, wait=None):
        """Record until silence. Returns mono float32 16 kHz, or None if nobody spoke within `wait` s."""
        wait = wait or config.SPEECH_WAIT_S
        fps = RATE / FRAME
        frames, noise = [], []
        spoke = False
        silence = 0
        start = None  # the clock only starts once the microphone is delivering audio

        while True:
            frame = self._read()
            if start is None:
                start = time.monotonic()
            frames.append(frame)
            rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))

            if len(noise) < 3:  # ~240 ms to measure the background noise
                noise.append(rms)
                continue
            threshold = max(config.MIN_SPEECH_LEVEL, min(noise) * 3)  # the minimum ignores speech that already began

            elapsed = time.monotonic() - start
            if rms > threshold:
                spoke, silence = True, 0
            elif spoke:
                silence += 1
                if silence / fps >= config.END_SILENCE_S:
                    break
            if not spoke and elapsed > wait:
                return None
            if elapsed > config.MAX_REQUEST_S:
                break

        if not spoke:
            return None
        return np.concatenate(frames).astype(np.float32) / 32768.0

    def transcribe(self, audio):
        self._whisper_ready.wait()
        if self._whisper_config != (config.WHISPER_MODEL, config.WHISPER_DEVICE):  # changed in the settings
            self._load_whisper()
        if self._whisper is None:
            log.error("whisper unavailable, check WHISPER_MODEL in the settings")
            return ""
        segments, _ = self._whisper.transcribe(
            audio,
            language=config.LANGUAGE,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()

    def pause(self):
        self.recorder.stop()

    def resume(self):
        self.recorder.start()

    def close(self):
        self.recorder.delete()
