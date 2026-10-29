"""Texts Jully speaks by herself (everything else comes from the model, in the configured language)."""
import config

_TEXTS = {
    "en": {
        "need_api_key": "The AI key is missing. Open the settings.",
        "llm_error": "I couldn't reach the AI right now.",
        "too_many_steps": "I got tangled up with that request.",
        "late_reminder": "Late reminder: {message}",
        "voice_sample": "Hi, I'm Jully.",
    },
    "pt": {
        "need_api_key": "Falta configurar a chave da IA. Abra as configurações.",
        "llm_error": "Não consegui falar com a IA agora.",
        "too_many_steps": "Me enrolei com esse pedido.",
        "late_reminder": "Lembrete atrasado: {message}",
        "voice_sample": "Oi, eu sou a Jully.",
    },
}


def t(key, **kwargs):
    return _TEXTS[config.LANGUAGE][key].format(**kwargs)
