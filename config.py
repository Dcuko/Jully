import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).parent
load_dotenv(RAIZ / ".env")

# IA: padrão Groq (plano grátis). Qualquer API compatível com OpenAI funciona.
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")
LLM_VISION_MODEL = os.environ.get("LLM_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
VOZ = os.environ.get("VOZ", "pt-BR-FranciscaNeural")
VELOCIDADE_VOZ = os.environ.get("VELOCIDADE_VOZ", "+10%")

# Palavra de ativação (openWakeWord): nome de um modelo pronto ("hey_jarvis")
# ou caminho para um .onnx treinado por você (ex.: models/hey_jully.onnx).
_wake = os.environ.get("WAKEWORD", "hey_jarvis")
WAKEWORD = str(RAIZ / _wake) if _wake.endswith((".onnx", ".tflite")) else _wake
MIC_INDEX = int(os.environ.get("MIC_INDEX", "-1"))  # -1 = padrão do Windows
MIC_GANHO = int(os.environ.get("MIC_GANHO", "3"))  # amplifica microfones fracos
WAKEWORD_LIMIAR = float(os.environ.get("WAKEWORD_LIMIAR", "0.35"))

# Gravação após o "Hey Jully"
VOZ_LIMIAR_MIN = float(os.environ.get("VOZ_LIMIAR_MIN", "200"))  # volume mínimo que conta como fala
SILENCIO_FIM_S = 0.8     # silêncio que encerra o pedido
ESPERA_FALA_S = 3.0       # desiste se ninguém falar
MAX_PEDIDO_S = 12.0
REPLICA = os.environ.get("REPLICA", "1") == "1"  # após a resposta, continua ouvindo sem a palavra de ativação

# Memória curta da conversa
HISTORICO_MAX_MSGS = 12
HISTORICO_VALIDADE_S = 300

# Só estes nomes podem ser abertos por voz (além de sites http/https)
HOME = Path.home()
APPS = {
    "calculadora": "calc.exe",
    "bloco de notas": "notepad.exe",
    "explorador": "explorer.exe",
    "paint": "mspaint.exe",
    "configurações": "ms-settings:",
    "downloads": str(HOME / "Downloads"),
    "documentos": str(HOME / "Documents"),
    "imagens": str(HOME / "Pictures"),
    "area de trabalho": str(HOME / "Desktop"),
}

PASTA_PRINTS = HOME / "Pictures" / "Capturas Jully"
ARQUIVO_NOTAS = HOME / "Documents" / "Notas Jully" / "notas.txt"
