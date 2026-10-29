# Jully

Assistente de voz em segundo plano para Windows. Diga a palavra de ativação e fale o pedido.

```
openWakeWord (escuta leve) → bipe → grava até o silêncio → faster-whisper → LLM (Groq) + ferramentas → edge-tts
```

O faster-whisper só transcreve depois da palavra de ativação; no resto do tempo só o openWakeWord roda.

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

### 1. Chave da IA (Groq, grátis, sem cartão)
1. Entre em https://console.groq.com e faça login (Google ou e-mail).
2. Vá em **API Keys → Create API Key**, dê um nome (ex.: `jully`) e copie a chave (`gsk_...`). Ela só aparece uma vez.
3. Cole em `LLM_API_KEY=` no `.env`.

O plano grátis tem limite de pedidos por minuto/dia, mais que suficiente para uso pessoal.
Para usar outro provedor (Gemini, OpenRouter, Ollama local), troque `LLM_BASE_URL`, `LLM_MODEL` e `LLM_API_KEY` no `.env`.

### 2. Palavra de ativação
Por padrão usa o modelo pronto **"Hey Jarvis"** (`WAKEWORD=hey_jarvis`), baixado sozinho na primeira execução.
Se ele ativar à toa ou não ouvir você, ajuste `WAKEWORD_LIMIAR` no `.env` (0.5 padrão; suba para ativar menos, desça para ativar mais).

Para trocar por "Hey Jully", treine um modelo com o notebook de treino automático do openWakeWord
(https://github.com/dscripka/openWakeWord, seção *Training New Models*), coloque o `.onnx` em `models/`
e use `WAKEWORD=models/hey_jully.onnx` no `.env`.

## Uso

```powershell
.venv\Scripts\python main.py        # com console, para testar
.venv\Scripts\pythonw main.py       # sem janela
.\instalar_inicio.ps1               # abrir junto com o Windows
```

Ícone na bandeja do sistema: **Pausar** e **Sair**. Logs em `jully.log`.

## Exemplos

- "Hey Jarvis, quanto é 23 vezes 5? Coloca na minha área de transferência."
- "..., tira um print da tela."
- "..., o que tem na minha tela?"
- "..., abre o YouTube." / "abre a calculadora"
- "..., me avisa em 10 minutos para tirar a roupa da máquina."
- "..., anota que preciso comprar leite."
- "..., volume em 30." / "bloqueia a tela"

Apps e pastas que podem ser abertos por voz ficam em `config.py` (`APPS`). Não há ferramenta de comando livre no terminal, de propósito.
