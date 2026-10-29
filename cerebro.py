import json
import logging
import re
import time

import config
import ferramentas
from llm import cliente

log = logging.getLogger("jully")

SISTEMA = (
    "Você é a Jully, uma assistente de voz que roda no PC do usuário. "
    "Sua resposta será FALADA em voz alta: responda em português do Brasil, em no máximo "
    "uma ou duas frases curtas, sem markdown, listas, emojis ou links. "
    "Para agir no computador, use as ferramentas; depois de usá-las, confirme em poucas palavras. "
    "Nunca diga que fez algo sem ter chamado a ferramenta correspondente. "
    "Se o pedido for impossível com as ferramentas, diga isso de forma simples. "
    "Escreva sempre números em algarismos (70, 13,20, 3 mil), nunca por extenso; "
    "a voz sabe lê-los. "
    "Seja direta como a Siri: vá direto à resposta, sem introdução, sem explicar o raciocínio e sem "
    "oferecer ajuda extra no final. Exemplos: "
    "'quanto é 20 mais 50' -> '70'; "
    "'o que é fotossíntese' -> 'É como as plantas transformam luz do sol em energia.'; "
    "'copia 115' -> 'Pronto, copiei.'"
)

TOOLS = [
    {"type": "function", "function": {
        "name": s["name"], "description": s["description"], "parameters": s["input_schema"]}}
    for s in ferramentas.SCHEMAS
]

# gpt-oss "pensa" antes de responder; esforço baixo = resposta bem mais rápida
_EXTRA = {"extra_body": {"reasoning_effort": "low"}} if config.LLM_MODEL.startswith("openai/gpt-oss") else {}

_historico = []
_ultimo_uso = 0.0


def _aparar():
    """Mantém só as últimas mensagens, começando sempre em uma pergunta do usuário."""
    while len(_historico) > config.HISTORICO_MAX_MSGS:
        _historico.pop(0)
        while _historico and _historico[0]["role"] != "user":
            _historico.pop(0)


def _encurtar(texto, max_frases=2, max_chars=220):
    """Rede de segurança: tira frases repetidas e fala só o começo."""
    # quebra após . ! ? mesmo sem espaço ("Quarenta.Quarenta."), mas não em "3.5"
    frases = re.split(r"(?<=[.!?])\s*(?=[^\W\d_])", texto.strip())
    unicas = []
    for f in frases:
        f = f.strip()
        if f and (not unicas or f.lower() != unicas[-1].lower()):
            unicas.append(f)
    curto = " ".join(unicas[:max_frases])
    if len(curto) > max_chars:
        curto = curto[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "."
    return curto


def responder(pergunta):
    global _ultimo_uso
    if time.monotonic() - _ultimo_uso > config.HISTORICO_VALIDADE_S:
        _historico.clear()
    _ultimo_uso = time.monotonic()

    _historico.append({"role": "user", "content": pergunta})
    try:
        for _ in range(5):
            r = cliente.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "system", "content": SISTEMA}] + _historico,
                tools=TOOLS,
                max_tokens=600,  # modelos que "pensam" gastam parte disso antes de responder
                temperature=0.4,
                **_EXTRA,
            )
            m = r.choices[0].message
            entrada = {"role": "assistant", "content": "" if m.tool_calls else (m.content or "")}
            if m.tool_calls:
                entrada["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in m.tool_calls
                ]
            _historico.append(entrada)

            if not m.tool_calls:
                _aparar()
                return _encurtar(m.content or "")

            for tc in m.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                log.info("ferramenta %s %s", tc.function.name, args)
                _historico.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(ferramentas.executar(tc.function.name, args)),
                })
        return "Me enrolei com esse pedido."
    except Exception:
        log.exception("erro ao falar com o modelo")
        _historico.clear()
        return "Não consegui falar com a IA agora."
