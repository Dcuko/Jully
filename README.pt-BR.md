# Jully

🌎 [English](README.md) · Português (Brasil)

Assistente de voz em segundo plano para Windows. Diga a palavra de ativação e fale o pedido.

```
openWakeWord (escuta leve) → bipe → grava até o silêncio → faster-whisper → LLM (Groq) + ferramentas → edge-tts
```

O faster-whisper só transcreve depois da palavra de ativação; no resto do tempo só o openWakeWord roda.
A Jully entende e responde em **português ou inglês** (configuração `LANGUAGE`).

## Início rápido (Jully.exe)

1. Instale o [Python 3.11 ou mais novo](https://www.python.org/downloads/windows/) (marque **Add python.exe to PATH**).
2. Dê dois cliques em **`Jully.exe`** (deixe-o nesta pasta). Na primeira vez ele cria o ambiente virtual e
   instala os requirements, mostrando o progresso; leva alguns minutos.
3. Preencha a chave da IA na janela de configurações que abrir (veja [Chave da IA](#1-chave-da-ia-groq-grátis-sem-cartão)).

Depois disso, o `Jully.exe` só abre a Jully na hora: nunca mais instala nem verifica nada.
Para instalar os requirements de novo (por exemplo, depois de atualizar a Jully), rode `Jully.exe --reinstall`.
Só uma Jully roda por vez; abrir duas vezes mostra um aviso.

O exe não fica no repositório. Gere o seu (é só um launcher pequeno, uns 11 MB):

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python build_exe.py
```

## Instalação manual

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Para usar em português, coloque `LANGUAGE=pt` no `.env` (ou escolha **Português (Brasil)** na aba Voz das configurações).

### 1. Chave da IA (Groq, grátis, sem cartão)
1. Entre em https://console.groq.com e faça login (Google ou e-mail).
2. Vá em **API Keys → Create API Key**, dê um nome (ex.: `jully`) e copie a chave (`gsk_...`). Ela só aparece uma vez.
3. Cole na aba **IA** da janela de configurações, ou em `LLM_API_KEY=` no `.env`.

O plano grátis tem limite de pedidos por minuto/dia, mais que suficiente para uso pessoal.
Para usar outro provedor (Gemini, OpenRouter, Ollama local), troque o endereço, o modelo e a chave na aba **IA**
(ou `LLM_BASE_URL`, `LLM_MODEL` e `LLM_API_KEY` no `.env`). O Ollama local não precisa de chave.

### 2. Palavra de ativação
Por padrão usa o modelo pronto **"Hey Jarvis"** (`WAKEWORD=hey_jarvis`), baixado sozinho na primeira execução.
Se ele ativar à toa ou não ouvir você, ajuste a **Sensibilidade** na aba Ativação
(`WAKEWORD_THRESHOLD` no `.env`, 0.35 por padrão; suba para ativar menos, desça para ativar mais).

Para trocar por "Hey Jully", treine um modelo com o notebook de treino automático do openWakeWord
(https://github.com/dscripka/openWakeWord, seção *Training New Models*), coloque o `.onnx` em `models/`
e use `WAKEWORD=models/hey_jully.onnx` no `.env`.

## Uso

```powershell
.venv\Scripts\python main.py        # com console, para testar
.venv\Scripts\pythonw main.py       # sem janela
.\install_startup.ps1               # abrir junto com o Windows
```

Ícone na bandeja do sistema: **Open window** (abrir janela), **Settings** (configurações), **Pause wake word** (pausar a palavra de ativação) e **Quit** (sair). Logs em `jully.log`.

## Configurações

O ícone de engrenagem da janela abre as configurações, que gravam direto no seu `.env` (comentários e ordem são preservados):

- **IA:** provedor, chave da API, endereço, modelos de texto e de visão, e um botão para testar a conexão.
- **Voz:** idioma, voz, velocidade (com botão para ouvir um exemplo) e modelo/processador do Whisper.
- **Ativação:** palavra de ativação, sensibilidade, microfone, ganho e volume mínimo de fala.
- **Geral:** continuar ouvindo após responder, a pílula de status, o que "ver tela" captura, cidade padrão do clima e sites permitidos.

Quase tudo vale na hora. Trocar a palavra de ativação ou o microfone pede reiniciar (a janela oferece reiniciar). Se faltar a chave da IA, as configurações abrem sozinhas ao iniciar.

A interface está em inglês; só a voz e as respostas da Jully seguem o idioma escolhido.

## Pílula de status

Quando a Jully está ouvindo ou trabalhando, uma pílula minúscula aparece no canto superior esquerdo da tela: **Listening…** (pode falar),
**Transcribing…**, **Thinking…** (com o que ela entendeu) e **Speaking…**. Ela nunca rouba o foco, o mouse passa direto
por ela, e some enquanto a janela da Jully está na frente. Um aviso curto aparece se ela não ouviu ou não entendeu nada.
Desligue na aba Geral (`OVERLAY=0`).

O reconhecimento de voz usa o Whisper `small` por padrão, um bom equilíbrio para inglês e português. Troque na aba Voz
(`WHISPER_MODEL`): `tiny` e `base` são mais rápidos e menos precisos, `medium` é mais preciso e mais lento.

## Exemplos

- "Hey Jarvis, quanto é 23 vezes 5? Coloca na minha área de transferência."
- "..., tira um print da tela."
- "..., o que tem na minha tela?"
- "..., abre o YouTube." / "abre a calculadora"
- "..., me avisa em 10 minutos para tirar a roupa da máquina."
- "..., anota que preciso comprar leite."
- "..., volume em 30." / "bloqueia a tela"
- "..., pausa a música." / "próxima faixa"
- "..., como está o tempo em Curitiba?"
- "..., me lembra amanhã às 9h de ligar para o banco."

Apps e pastas que podem ser abertos por voz ficam em `config.py` (`APPS`). Sites só abrem se o domínio estiver na lista de sites permitidos (configurações). Não há ferramenta de comando livre no terminal, de propósito.

Timers e lembretes ficam salvos em `timers.json` e continuam valendo se a Jully for fechada e aberta de novo.

## Privacidade

- O que você fala é transcrito no seu PC (Whisper). Só o **texto** do pedido vai para o provedor de IA.
- "O que tem na minha tela?" envia um **print** (de todos os monitores, ou só da janela ativa, conforme a configuração) para o provedor de IA.
- O clima consulta o Open-Meteo (sem chave) com o nome da cidade.

## Desenvolvimento

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

| Arquivo | O que faz |
| --- | --- |
| `main.py` | Ponto de entrada: ícone da bandeja, janela e o laço principal |
| `listen.py` / `speak.py` | Microfone, palavra de ativação e Whisper / síntese de voz |
| `brain.py` / `llm.py` | Conversa com o modelo e chamada de ferramentas |
| `tools.py` | O que a Jully sabe fazer (área de transferência, tela, timers, clima...) |
| `config.py` / `envfile.py` / `i18n.py` | Configurações, leitura/gravação do `.env`, textos falados |
| `ui.py` / `settings_ui.py` / `theme.py` | Janela de chat, janela de configurações, visual compartilhado |

## Atualizando da versão só em português

Os nomes antigos das configurações (`VOZ`, `REPLICA`, `CIDADE`...) são renomeados no seu `.env` automaticamente na primeira execução, e
`LANGUAGE=pt` é adicionado para a Jully continuar falando português. Os prints agora vão para `Imagens\Jully Screenshots` e as notas para
`Documentos\Jully Notes\notes.txt`; mova os arquivos antigos de `Capturas Jully` e `Notas Jully` se quiser tudo junto.
