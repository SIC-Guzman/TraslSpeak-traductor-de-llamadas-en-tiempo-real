import customtkinter as ctk
import threading
import time
import queue
import numpy as np
import pyaudio
import torch
from motor_ia import MotorIA # un llamado a la clase que maneja el audio y la IA, para que el codigo sea mas limpio
from modulo_traduccion import Traductor  
from transformers import MarianMTModel, MarianTokenizer

#la configuracion de la parte visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TraslSpeakApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TraslSpeak ")
        self.geometry("800x600")

        #El titulo arriba del todo
        self.lbl_titulo = ctk.CTkLabel(self, text="TraslSpeak", 
                                       font=("Roboto", 20, "bold"))
        self.lbl_titulo.pack(pady=(20,10))
      
        #el area del texto
        self.frame_central = ctk.CTkFrame(self, corner_radius=15)
        self.frame_central.pack(pady=10, padx=20, fill="both", expand=True)

        #la caja de texto
        self.txt_log = ctk.CTkTextbox(self.frame_central, font=("Roboto", 14))
        self.txt_log.pack(pady=(0,10), padx=10, fill="both", expand=True)
        self.txt_log.insert("0.0", "Seleccione un idioma e incia\n")

        #la barra de controles, que estara abajo
        self.frame_controles = ctk.CTkFrame(self, height=80, fg_color="transparent")
        self.frame_controles.pack(pady=10, padx=20, fill="x", side="bottom")

        #para elegir el idioma
        self.combo_idioma = ctk.CTkComboBox(self.frame_controles,
                                                values=["Español", "Inglés"],
                                                state = "readonly",
                                                width=100)
        self.combo_idioma.set("Español") #valor por defecto
        self.combo_idioma.pack(side="left", padx=5)

        #los botones a la derecha
        self.btn_iniciar = ctk.CTkButton(self.frame_controles, text="▶ INICIAR",
                                         command=self.incio_hilo_audio,
                                         fg_color="#2CC985",hover_color = "#A32428" 
                                         ,width=120, height=40,)
        self.btn_iniciar.pack(side="right", padx=10)
        
        self.btn_detener = ctk.CTkButton(self.frame_controles, text="■ DETENER",
                                            command=self.detener_sistema, state="disabled",
                                            fg_color="#D64045", hover_color="#A32428",
                                            width=120, height=40)
        self.btn_detener.pack(side="right", padx=10)

        #los hilos
        self.cola_mensajes = queue.Queue()

        #inciamos el revisor de mensajes visuales
        self.check_hilos()

        #la instancia del motor de ia
        self.motor = MotorIA(self.cola_mensajes)

        #definimos los hilos
    def check_hilos(self):
            "Revisa si hay mensajes en las colas y actualiza la interfaz"
            try:
                while True:
                    mensaje = self.cola_mensajes.get_nowait()
                    #si llega un mensaje lo ponemos en el area de texto
                    self.txt_log.insert("end", mensaje + "\n")
                    self.txt_log.see("end") #para que baje automaticamente
            except queue.Empty:
                pass
            #se vuelve a llamar a si mismo despues de 100 ms
            self.after(100, self.check_hilos)
    
    def incio_hilo_audio(self):
            # leersmo que idioma se ha seleccionado
            seleccion = self.combo_idioma.get()
            idioma_codigo = "en" if "Inglés" in seleccion else "es"

            #configuramos el motor de IA
            self.motor.configurar_idioma(idioma_codigo)

            #lo arrancamos
            self.motor.iniciar_escuchar()

            #actualizamos la interfaz
            self.btn_iniciar.configure(state="disabled")
            self.combo_idioma.configure(state="disabled") #desabilitamos la eleccion de idioma
            self.btn_detener.configure(state="normal") #habilitamos el boton de detener
            self.txt_log.insert("end", "SISTEMA INICIADO. PUEDES HABLAR AHORA.\n")

    def detener_sistema(self):
             self.motor.detener_sistema()

             #actualizamos la interfaz
             self.combo_idioma.configure(state = "normal")
             self.btn_iniciar.configure(state="normal")
             self.btn_detener.configure(state="disabled") #desabilitamos el boton de detener
            
if __name__ == "__main__":
    app = TraslSpeakApp()
    app.mainloop()