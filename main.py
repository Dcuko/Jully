import ctypes
import logging
import queue
import sys
import threading
import winsound
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

import config

logging.basicConfig(
    filename=config.RAIZ / "jully.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("jully")
for ruidoso in ("httpx", "httpcore", "huggingface_hub", "urllib3"):
    logging.getLogger(ruidoso).setLevel(logging.WARNING)

parar = threading.Event()
pausado = threading.Event()
fila = queue.Queue()  # pedidos vindos da janela: ("texto", str) ou ("mic", None)
janela = None


def erro_fatal(msg):
    log.error(msg)
    ctypes.windll.user32.MessageBoxW(0, msg, "Jully", 0x10)
    sys.exit(1)


def validar():
    faltando = []
    if not config.LLM_API_KEY:
        faltando.append("LLM_API_KEY no .env")
    if config.WAKEWORD.endswith((".onnx", ".tflite")) and not Path(config.WAKEWORD).exists():
        faltando.append(f"arquivo {config.WAKEWORD}")
    if faltando:
        erro_fatal("Falta configurar:\n- " + "\n- ".join(faltando) + "\n\nVeja o README.")


def laco():
    try:
        _laco()
    except Exception:
        log.exception("o laço principal caiu")
        erro_fatal("A Jully parou por um erro. Veja jully.log.")


def _laco():
    import cerebro
    import falar
    from ouvir import Ouvido

    try:
        ouvido = Ouvido()
    except Exception as e:
        erro_fatal(f"Não consegui iniciar o microfone/wake word:\n{e}")

    def interromper():
        return parar.is_set() or pausado.is_set() or not fila.empty()

    log.info("Jully pronta, aguardando a palavra de ativação (%s)", config.WAKEWORD)
    replica = False  # logo após uma resposta, escuta a continuação sem palavra de ativação
    while not parar.is_set():
        tipo, valor = None, None

        if pausado.is_set():  # pausada: só a janela (texto e microfone) funciona
            try:
                tipo, valor = fila.get(timeout=0.2)
            except queue.Empty:
                continue
        elif not fila.empty():
            tipo, valor = fila.get_nowait()
        elif replica:
            tipo = "replica"
        elif ouvido.esperar_wake(interromper):
            tipo = "wake"
        else:
            continue

        replica = False
        if tipo in ("wake", "mic", "replica"):
            if tipo == "wake":
                log.info("palavra de ativação detectada")
                winsound.Beep(880, 120)
            elif tipo == "mic":
                ouvido.pausar()  # descarta áudio velho do buffer
                ouvido.retomar()
            janela.definir_status("Ouvindo…")
            audio = ouvido.gravar()  # igual após o "hey jarvis": espera você começar e só corta no silêncio
            if audio is None:
                janela.definir_status("")
                continue
            janela.definir_status("Transcrevendo…")
            texto = ouvido.transcrever(audio)
        else:
            texto = valor

        log.info("pedido: %s", texto)
        if not texto:
            janela.definir_status("")
            continue

        janela.adicionar("voce", texto)
        janela.definir_status("Pensando…")
        resposta = cerebro.responder(texto)
        log.info("resposta: %s", resposta)
        janela.adicionar("jully", resposta)

        janela.definir_status("Falando…")
        ouvido.pausar()  # não escutar a própria voz
        try:
            falar.dizer(resposta)
        except Exception:
            log.exception("erro ao falar")
        ouvido.retomar()
        janela.definir_status("")
        replica = config.REPLICA and tipo != "texto"

    ouvido.fechar()


def icone():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(138, 92, 246, 255))
    d.rectangle((26, 16, 38, 40), fill="white")
    d.ellipse((26, 36, 38, 48), fill="white")
    return img


def main():
    global janela
    validar()

    from ui import Janela

    janela = Janela(
        ao_enviar=lambda t: fila.put(("texto", t)),
        ao_mic=lambda: fila.put(("mic", None)),
    )
    threading.Thread(target=laco, daemon=True).start()

    def alternar(ic, item):
        pausado.clear() if pausado.is_set() else pausado.set()

    def abrir(ic, item):
        janela.mostrar()

    def sair(ic, item):
        parar.set()
        janela.fechar()

    menu = pystray.Menu(
        pystray.MenuItem("Abrir janela", abrir, default=True),
        pystray.MenuItem("Pausar palavra de ativação", alternar, checked=lambda item: pausado.is_set()),
        pystray.MenuItem("Sair", sair),
    )
    bandeja = pystray.Icon("Jully", icone(), "Jully", menu)
    bandeja.run_detached()

    janela.executar(oculta="--oculto" in sys.argv)
    bandeja.stop()


if __name__ == "__main__":
    main()
