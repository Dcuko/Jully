import queue
import tkinter as tk

FUNDO = "#16161e"
PAINEL = "#1f2030"
TEXTO = "#e6e6ef"
SUAVE = "#8b8ba3"
ROXO = "#8a5cf6"
BALAO_JULLY = "#2a2b3d"
VERMELHO = "#e5484d"


class Janela:
    """Janela de chat. Os métodos públicos são seguros para chamar de outras threads."""

    def __init__(self, ao_enviar, ao_mic):
        self._ao_enviar = ao_enviar
        self._ao_mic = ao_mic
        self._eventos = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Jully")
        self.root.geometry("420x560")
        self.root.minsize(320, 300)
        self.root.configure(bg=FUNDO)
        self.root.protocol("WM_DELETE_WINDOW", self.esconder)

        self.chat = tk.Text(
            self.root, wrap="word", state="disabled", bg=FUNDO, fg=TEXTO, bd=0,
            highlightthickness=0, padx=14, pady=12, font=("Segoe UI", 11), cursor="arrow",
        )
        self.chat.tag_configure("rotulo_voce", foreground=SUAVE, justify="right", font=("Segoe UI", 8), rmargin=8)
        self.chat.tag_configure("rotulo_jully", foreground=ROXO, justify="left", font=("Segoe UI", 8), lmargin1=8)
        self.chat.tag_configure("voce", background=ROXO, foreground="white", justify="right",
                                lmargin1=70, lmargin2=70, rmargin=8, spacing1=2, spacing3=10)
        self.chat.tag_configure("jully", background=BALAO_JULLY, foreground=TEXTO, justify="left",
                                lmargin1=8, lmargin2=8, rmargin=70, spacing1=2, spacing3=10)

        self.status_var = tk.StringVar()
        self.status = tk.Label(self.root, textvariable=self.status_var, bg=FUNDO, fg=SUAVE,
                               font=("Segoe UI", 9), anchor="w", padx=14)

        barra = tk.Frame(self.root, bg=PAINEL, padx=8, pady=8)
        self.entrada = tk.Entry(barra, bg=FUNDO, fg=TEXTO, insertbackground=TEXTO, bd=0,
                                highlightthickness=0, font=("Segoe UI", 11))
        self.entrada.bind("<Return>", lambda e: self._enviar())
        self.botao_mic = tk.Button(barra, text="🎤", command=self._ao_mic, bg=ROXO, fg="white",
                                   activebackground=ROXO, bd=0, width=3, font=("Segoe UI Emoji", 11),
                                   cursor="hand2")
        botao_enviar = tk.Button(barra, text="➤", command=self._enviar, bg=ROXO, fg="white",
                                 activebackground=ROXO, bd=0, width=3, font=("Segoe UI", 11),
                                 cursor="hand2")

        barra.pack(side="bottom", fill="x")
        self.status.pack(side="bottom", fill="x")
        self.chat.pack(side="top", fill="both", expand=True)
        self.entrada.pack(side="left", fill="x", expand=True, ipady=7, padx=(4, 8))
        self.botao_mic.pack(side="right", padx=(6, 0))
        botao_enviar.pack(side="right")

        self.entrada.focus_set()
        self.root.after(50, self._processar)

    # ---- seguros entre threads ----

    def adicionar(self, papel, texto):
        self._eventos.put(("msg", papel, texto))

    def definir_status(self, texto):
        self._eventos.put(("status", texto))

    def mostrar(self):
        self._eventos.put(("mostrar",))

    def fechar(self):
        self._eventos.put(("fechar",))

    # ---- só na thread da interface ----

    def esconder(self):
        self.root.withdraw()

    def _enviar(self):
        texto = self.entrada.get().strip()
        if texto:
            self.entrada.delete(0, "end")
            self._ao_enviar(texto)

    def _processar(self):
        try:
            while True:
                ev = self._eventos.get_nowait()
                if ev[0] == "msg":
                    self._inserir(ev[1], ev[2])
                elif ev[0] == "status":
                    self.status_var.set(ev[1])
                    self.botao_mic.configure(bg=VERMELHO if ev[1].startswith("Ouvindo") else ROXO)
                elif ev[0] == "mostrar":
                    self.root.deiconify()
                    self.root.lift()
                    self.entrada.focus_set()
                elif ev[0] == "fechar":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(50, self._processar)

    def _inserir(self, papel, texto):
        nome = "Você" if papel == "voce" else "Jully"
        self.chat.configure(state="normal")
        self.chat.insert("end", nome + "\n", f"rotulo_{papel}")
        self.chat.insert("end", f" {texto} \n", papel)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def executar(self, oculta=False):
        if oculta:
            self.root.withdraw()
        self.root.mainloop()
