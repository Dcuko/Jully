from openai import OpenAI

import config

# Qualquer API compatível com OpenAI serve (Groq, Gemini, OpenRouter, Ollama...)
cliente = OpenAI(api_key=config.LLM_API_KEY or "sem-chave", base_url=config.LLM_BASE_URL)
