import asyncio
import logging
import os
import tempfile
import threading
import time

import edge_tts
import miniaudio

import config

log = logging.getLogger("jully")
_lock = threading.Lock()


def _play(path):
    """Play the mp3 straight to the default output (miniaudio); blocks until it ends."""
    done = threading.Event()
    stream = miniaudio.stream_with_callbacks(
        miniaudio.stream_file(
            path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100),
        end_callback=done.set,
    )
    next(stream)  # prime the generator
    device = miniaudio.PlaybackDevice(
        output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100)
    try:
        device.start(stream)
        done.wait(timeout=60)
        time.sleep(0.4)  # let the end of the audio leave the buffer
    finally:
        device.close()


def say(text, voice=None, rate=None):
    """Generate the speech with edge-tts and play it; blocks until done. Voice and rate default to the settings."""
    if not text:
        return
    with _lock:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            comm = edge_tts.Communicate(text, voice or config.VOICE, rate=rate or config.VOICE_RATE)
            t0 = time.monotonic()
            asyncio.run(comm.save(path))
            t1 = time.monotonic()
            _play(path)
            log.info("voice: generated in %.1fs, played for %.1fs (%d bytes)", t1 - t0,
                     time.monotonic() - t1, os.path.getsize(path))
        finally:
            os.remove(path)
