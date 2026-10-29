import ast
import base64
import ctypes
import io
import operator
import os
import threading
import webbrowser
from datetime import datetime

import pyperclip
import win32clipboard
from PIL import ImageGrab

import config
import falar
import llm

# ---------- esquemas enviados ao Claude ----------

SCHEMAS = [
    {
        "name": "calcular",
        "description": "Calcula uma expressão matemática (+ - * / ** % //, parênteses). Use ponto como separador decimal.",
        "input_schema": {
            "type": "object",
            "properties": {"expressao": {"type": "string"}},
            "required": ["expressao"],
        },
    },
    {
        "name": "copiar_para_area_de_transferencia",
        "description": "Coloca um texto na área de transferência do usuário.",
        "input_schema": {
            "type": "object",
            "properties": {"texto": {"type": "string"}},
            "required": ["texto"],
        },
    },
    {
        "name": "ler_area_de_transferencia",
        "description": "Lê o texto que está na área de transferência.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "tirar_print",
        "description": "Tira um print de toda a tela, salva em arquivo e copia a imagem para a área de transferência.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "ver_tela",
        "description": "Olha a tela do usuário e responde uma pergunta sobre ela (o que está aberto, ler um texto, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {"pergunta": {"type": "string"}},
            "required": ["pergunta"],
        },
    },
    {
        "name": "abrir",
        "description": f"Abre um site (URL http/https completa) ou um destes itens: {', '.join(config.APPS)}.",
        "input_schema": {
            "type": "object",
            "properties": {"alvo": {"type": "string"}},
            "required": ["alvo"],
        },
    },
    {
        "name": "hora_e_data",
        "description": "Retorna a data e a hora atuais.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "timer",
        "description": "Avisa por voz depois de alguns segundos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segundos": {"type": "integer", "minimum": 1},
                "mensagem": {"type": "string", "description": "O que dizer quando acabar."},
            },
            "required": ["segundos", "mensagem"],
        },
    },
    {
        "name": "anotar",
        "description": "Salva uma nota rápida no arquivo de notas do usuário.",
        "input_schema": {
            "type": "object",
            "properties": {"texto": {"type": "string"}},
            "required": ["texto"],
        },
    },
    {
        "name": "volume",
        "description": "Controla o volume do Windows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "acao": {"type": "string", "enum": ["aumentar", "diminuir", "mudo", "definir"]},
                "nivel": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Só para 'definir'."},
            },
            "required": ["acao"],
        },
    },
    {
        "name": "bloquear_tela",
        "description": "Bloqueia o Windows.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# ---------- implementações ----------

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _avaliar(no):
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return no.value
    if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
        esq, dir_ = _avaliar(no.left), _avaliar(no.right)
        if isinstance(no.op, ast.Pow) and abs(dir_) > 1000:
            raise ValueError("expoente grande demais")
        return _OPS[type(no.op)](esq, dir_)
    if isinstance(no, ast.UnaryOp) and type(no.op) in _OPS:
        return _OPS[type(no.op)](_avaliar(no.operand))
    raise ValueError("expressão inválida")


def calcular(expressao):
    r = _avaliar(ast.parse(expressao.strip(), mode="eval").body)
    if isinstance(r, float):
        r = round(r, 10)
        if r.is_integer():
            r = int(r)
    return str(r)


def copiar_para_area_de_transferencia(texto):
    pyperclip.copy(texto)
    return "Copiado."


def ler_area_de_transferencia():
    texto = pyperclip.paste()
    return texto[:2000] if texto else "(vazia)"


def _copiar_imagem(img):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "BMP")
    dib = buf.getvalue()[14:]  # CF_DIB não leva o cabeçalho de arquivo BMP
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib)
    finally:
        win32clipboard.CloseClipboard()


def tirar_print():
    img = ImageGrab.grab(all_screens=True)
    config.PASTA_PRINTS.mkdir(parents=True, exist_ok=True)
    caminho = config.PASTA_PRINTS / f"print_{datetime.now():%Y%m%d_%H%M%S}.png"
    img.save(caminho)
    _copiar_imagem(img)
    return f"Print salvo em {caminho} e copiado para a área de transferência."


def ver_tela(pergunta):
    img = ImageGrab.grab(all_screens=True).convert("RGB")
    img.thumbnail((1280, 1280))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    dados = base64.b64encode(buf.getvalue()).decode()
    r = llm.cliente.chat.completions.create(
        model=config.LLM_VISION_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": f"{pergunta}\nResponda em português, de forma curta."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{dados}"}},
        ]}],
    )
    return r.choices[0].message.content


def abrir(alvo):
    chave = alvo.strip().lower()
    if chave in config.APPS:
        os.startfile(config.APPS[chave])
        return f"Abrindo {chave}."
    if chave.startswith(("http://", "https://")):
        webbrowser.open(alvo.strip())
        return "Site aberto."
    return f"Não posso abrir isso. Opções: {', '.join(config.APPS)} ou um site http/https."


_DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def hora_e_data():
    a = datetime.now()
    return f"{_DIAS[a.weekday()]}, {a:%d/%m/%Y}, {a:%H:%M}"


def timer(segundos, mensagem):
    t = threading.Timer(segundos, falar.dizer, args=(mensagem,))
    t.daemon = True
    t.start()
    return f"Timer de {segundos} segundos definido."


def anotar(texto):
    config.ARQUIVO_NOTAS.parent.mkdir(parents=True, exist_ok=True)
    with open(config.ARQUIVO_NOTAS, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%d/%m/%Y %H:%M}] {texto}\n")
    return "Nota salva."


def _tecla(vk, vezes=1):
    for _ in range(vezes):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)


def volume(acao, nivel=None):
    MUDO, BAIXO, CIMA = 0xAD, 0xAE, 0xAF  # cada toque muda 2%
    if acao == "mudo":
        _tecla(MUDO)
    elif acao == "aumentar":
        _tecla(CIMA, 5)
    elif acao == "diminuir":
        _tecla(BAIXO, 5)
    elif acao == "definir" and nivel is not None:
        _tecla(BAIXO, 50)
        _tecla(CIMA, round(nivel / 2))
    else:
        return "Informe o nível para definir."
    return "Volume ajustado."


def bloquear_tela():
    ctypes.windll.user32.LockWorkStation()
    return "Tela bloqueada."


_FUNCOES = {s["name"]: globals()[s["name"]] for s in SCHEMAS}


def executar(nome, argumentos):
    try:
        return _FUNCOES[nome](**argumentos)
    except Exception as e:
        return f"Erro: {e}"
