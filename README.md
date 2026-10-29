# Jully

🌎 English · [Português (Brasil)](README.pt-BR.md)

A background voice assistant for Windows. Say the wake word and speak your request.

```
openWakeWord (light listening) → beep → record until silence → faster-whisper → LLM (Groq) + tools → edge-tts
```

faster-whisper only transcribes after the wake word; the rest of the time only openWakeWord runs.
Jully understands and answers in **English or Portuguese** (setting `LANGUAGE`).

## Quick start (Jully.exe)

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) (tick **Add python.exe to PATH**).
2. Double-click **`Jully.exe`** (keep it in this folder). The first time it creates the virtual environment and
   installs the requirements, showing the progress; this takes a few minutes.
3. Fill in your AI key in the settings window that opens (see [AI key](#1-ai-key-groq-free-no-credit-card)).

From then on, `Jully.exe` just opens Jully right away: it never installs or checks anything again.
To install the requirements again (e.g. after updating Jully), run `Jully.exe --reinstall`.
Only one Jully runs at a time; opening it twice shows a notice instead.

The exe is not in the repository. Build it yourself (it is a small launcher, about 11 MB):

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python build_exe.py
```

## Manual installation

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

### 1. AI key (Groq, free, no credit card)
1. Go to https://console.groq.com and sign in (Google or e-mail).
2. Open **API Keys → Create API Key**, name it (e.g. `jully`) and copy the key (`gsk_...`). It is shown only once.
3. Paste it in the **AI** tab of the settings window, or in `LLM_API_KEY=` in the `.env`.

The free plan has per-minute and per-day request limits, more than enough for personal use.
To use another provider (Gemini, OpenRouter, local Ollama), change the address, model and key in the **AI** tab
(or `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` in the `.env`). Local Ollama needs no key.

### 2. Wake word
By default it uses the ready-made **"Hey Jarvis"** model (`WAKEWORD=hey_jarvis`), downloaded on the first run.
If it triggers by accident or does not hear you, adjust **Sensitivity** in the Wake word tab
(`WAKEWORD_THRESHOLD` in the `.env`, 0.35 by default; raise it to trigger less, lower it to trigger more).

To use "Hey Jully" instead, train a model with the automatic training notebook from openWakeWord
(https://github.com/dscripka/openWakeWord, section *Training New Models*), put the `.onnx` in `models/`
and set `WAKEWORD=models/hey_jully.onnx` in the `.env`.

## Usage

```powershell
.venv\Scripts\python main.py        # with a console, for testing
.venv\Scripts\pythonw main.py       # no window
.\install_startup.ps1               # start with Windows
```

System tray icon: **Open window**, **Settings**, **Pause wake word** and **Quit**. Logs go to `jully.log`.

## Settings

The gear icon in the window opens the settings, which write straight to your `.env` (comments and order are preserved):

- **AI:** provider, API key, address, text and vision models, and a button to test the connection.
- **Voice:** language, voice, speech rate (with a button to hear a sample) and the Whisper model/device.
- **Wake word:** wake word, sensitivity, microphone, gain and minimum speech volume.
- **General:** keep listening after a reply, a small status pill, what "look at screen" captures, default weather city and allowed websites.

Almost everything applies immediately. Changing the wake word or the microphone needs a restart (the window offers to restart).
If the AI key is missing, the settings open by themselves on startup.

## Status pill

When Jully is listening or working, a tiny pill appears in the top-left corner of the screen: **Listening…** (speak now),
**Transcribing…**, **Thinking…** (with what she understood) and **Speaking…**. It never takes the focus, the mouse
goes through it, and it stays hidden while the Jully window is in front. A short notice appears if she did not hear
or understand anything. Turn it off in the General tab (`OVERLAY=0`).

Speech recognition uses Whisper `small` by default, a good balance for English and Portuguese. Change it in the Voice tab
(`WHISPER_MODEL`): `tiny` and `base` are faster but less accurate, `medium` is more accurate but slower.

## Examples

- "Hey Jarvis, what is 23 times 5? Put it on my clipboard."
- "..., take a screenshot."
- "..., what's on my screen?"
- "..., open YouTube." / "open the calculator"
- "..., remind me in 10 minutes to take the laundry out."
- "..., take a note: buy milk."
- "..., volume to 30." / "lock the screen"
- "..., pause the music." / "next track"
- "..., what's the weather in London?"
- "..., remind me tomorrow at 9am to call the bank."

Apps and folders that can be opened by voice are in `config.py` (`APPS`). Websites only open if their domain is in the allowed
sites list (settings). There is no free-form terminal tool, on purpose.

Timers and reminders are saved in `timers.json` and still fire if Jully is closed and opened again.

## Privacy

- What you say is transcribed on your PC (Whisper). Only the **text** of the request goes to the AI provider.
- "What's on my screen?" sends a **screenshot** (all monitors, or only the active window, depending on the setting) to the AI provider.
- Weather queries Open-Meteo (no key) with the city name.

## Development

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

| File | What it does |
| --- | --- |
| `main.py` | Entry point: tray icon, window and the main loop |
| `listen.py` / `speak.py` | Microphone, wake word and Whisper / text-to-speech |
| `brain.py` / `llm.py` | Conversation with the model and tool calling |
| `tools.py` | The things Jully can do (clipboard, screen, timers, weather...) |
| `config.py` / `envfile.py` / `i18n.py` | Settings, `.env` reading/writing, spoken texts |
| `ui.py` / `settings_ui.py` / `theme.py` | Chat window, settings window, shared look |

## Upgrading from the Portuguese-only version

Old setting names (`VOZ`, `REPLICA`, `CIDADE`...) are renamed in your `.env` automatically on the first run, and
`LANGUAGE=pt` is added so Jully keeps speaking Portuguese. Screenshots now go to `Pictures\Jully Screenshots` and notes to
`Documents\Jully Notes\notes.txt`; move your old files from `Capturas Jully` and `Notas Jully` if you want to keep them together.
