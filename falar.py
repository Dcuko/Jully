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
_trava = threading.Lock()


def _tocar(caminho):
    """Toca o mp3 direto na saída padrão (miniaudio); bloqueia até terminar."""
    fim = threading.Event()
    fluxo = miniaudio.stream_with_callbacks(
        miniaudio.stream_file(
            caminho, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100),
        end_callback=fim.set,
    )
    next(fluxo)  # prepara o gerador
    dispositivo = miniaudio.PlaybackDevice(
        output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100)
    try:
        dispositivo.start(fluxo)
        fim.wait(timeout=60)
        time.sleep(0.4)  # deixa o final do áudio sair do buffer
    finally:
        dispositivo.close()


def dizer(texto):
    """Gera a voz com edge-tts e toca; bloqueia até terminar."""
    if not texto:
        return
    with _trava:
        fd, caminho = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            comm = edge_tts.Communicate(texto, config.VOZ, rate=config.VELOCIDADE_VOZ)
            t0 = time.monotonic()
            asyncio.run(comm.save(caminho))
            t1 = time.monotonic()
            _tocar(caminho)
            log.info("voz: gerou em %.1fs, tocou por %.1fs (%d bytes)", t1 - t0,
                     time.monotonic() - t1, os.path.getsize(caminho))
        finally:
            os.remove(caminho)
