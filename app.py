import customtkinter as ctk
from PIL import Image
from api import conversar_com_assistente
import sounddevice as sd
import numpy as np
import wave
import threading
from gtts import gTTS
import tempfile
import os
import pygame
from faster_whisper import WhisperModel
from pydub import AudioSegment


# Inicializa o customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Inicializa modelo Whisper
modelo_whisper = WhisperModel("base", device="cpu", compute_type="int8")


# Fala usando gTTS + pygame com arquivo temporário
def falar_google(texto):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            caminho = temp_audio.name

        tts = gTTS(text=texto, lang='pt')
        tts.save(caminho)

        pygame.mixer.init()
        pygame.mixer.music.load(caminho)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue

        os.remove(caminho)
    except Exception as e:
        print(f"Erro ao falar: {e}")

        
# Função para enviar texto
def enviar_texto():
    texto = entrada.get()
    if texto.strip():
        caixa_resposta.configure(state="normal")
        caixa_resposta.insert("end", f"Você: {texto}\n", "usuario")
        entrada.delete(0, ctk.END)
        caixa_resposta.configure(state="disabled")

        threading.Thread(target=obter_resposta, args=(texto,), daemon=True).start()


# Função para obter resposta
def obter_resposta(mensagem):
    resposta = conversar_com_assistente(mensagem)
    caixa_resposta.after(0, lambda: exibir_resposta(resposta))
    threading.Thread(target=lambda: falar_google(resposta), daemon=True).start()


# Função para exibir resposta
def exibir_resposta(resposta):
    caixa_resposta.configure(state="normal")
    caixa_resposta.insert("end", f"Assistente: {resposta}\n\n", "bot")
    caixa_resposta.see("end")
    caixa_resposta.configure(state="disabled")


# Função para capturar áudio e transcrever com Whisper
def usar_microfone():
    def gravar_audio():
        fs = 16000
        duracao = 5  # segundos
        print("Gravando...")
        audio = sd.rec(int(duracao * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        print("Gravação finalizada.")

        caminho_arquivo = "temp.wav"
        with wave.open(caminho_arquivo, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio.tobytes())

        print("Transcrevendo...")
        segmentos, _ = modelo_whisper.transcribe(caminho_arquivo)
        for segmento in segmentos:
            texto = segmento.text.strip()
            if texto:
                caixa_resposta.after(0, lambda: entrada.insert(0, texto))
                caixa_resposta.after(0, lambda: enviar_texto())
                break

        os.remove(caminho_arquivo)

    threading.Thread(target=gravar_audio, daemon=True).start()


# Cria a janela principal
janela = ctk.CTk()
janela.title("Jully")
janela.geometry("800x600")
janela.minsize(400, 200)
janela.wm_attributes("-topmost", True)

# Caixa de resposta
caixa_resposta = ctk.CTkTextbox(janela, height=200, wrap="word", corner_radius=10, state="disabled")
caixa_resposta.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))

# Frame inferior
frame_inferior = ctk.CTkFrame(janela, corner_radius=20, height=120)  # Define uma altura maior para o frame
frame_inferior.grid(row=1, column=0, sticky="ew", pady=10, padx=20)
janela.grid_rowconfigure(0, weight=1)
janela.grid_columnconfigure(0, weight=1)

# Entrada de texto
entrada = ctk.CTkEntry(frame_inferior, font=('Segoe UI', 14), height=40)
entrada.grid(row=0, column=0, sticky="ew", padx=(0, 10))

# Botão de enviar
botao_enviar = ctk.CTkButton(frame_inferior, font=('Segoe UI', 18, 'bold'), text=">", corner_radius=20, width=40, height=40, command=enviar_texto)
botao_enviar.grid(row=0, column=1, padx=(0, 20))

# Botão do microfone
microfone_img = ctk.CTkImage(light_image=Image.open("microfone.png"), size=(20, 20))  # Ajusta o tamanho da imagem

botao_microfone = ctk.CTkButton(
    frame_inferior,
    image=microfone_img,
    text="",
    width=40,
    height=40,
    corner_radius=20,
    command=usar_microfone
)
botao_microfone.grid(row=0, column=2)

# Inicia a interface
janela.mainloop()
