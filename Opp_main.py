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
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class TraslSpeakApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TraslSpeak")
        self.geometry("800x600")
        self.configure(fg_color = "#D9F2FF")


        #El titulo arriba del todo
        self.lbl_titulo = ctk.CTkLabel(self, text="TraslSpeak", 
                                       font=("Segoe UI Bold", 24), text_color="#006699")
        self.lbl_titulo.pack(pady=(25,15))
      
        #el area del texto
        self.frame_central = ctk.CTkFrame(self, 
                                          corner_radius=15,
                                          fg_color="#FFFFFF",
                                          border_color= "#8ED6FF",
                                          border_width= 3)
        self.frame_central.pack(pady=10, padx=30, fill="both", expand=True)

        #la caja de texto
        self.txt_log = ctk.CTkTextbox(self.frame_central, font=("Segoe UI", 14),
                                      corner_radius= 15,
                                      fg_color="#F0F8FF",
                                      border_color= "#BCE0FD",
                                      border_width=2,
                                      text_color="#333333")
        self.txt_log.pack(pady=20, padx=20, fill="both", expand=True)
        self.txt_log.insert("0.0", "Bienvenido. Seleccione un idioma y presione Iniciar\n")

        #la barra de controles, que estara abajo
        self.frame_controles = ctk.CTkFrame(self, height=90, fg_color="transparent")
        self.frame_controles.pack(pady=20, padx=30, fill="x", side="bottom")

        #para elegir el idioma
        self.combo_idioma = ctk.CTkComboBox(self.frame_controles,font=("Segoe UI", 12),
                                                values=["Español", "Inglés"],
                                                state = "readonly",
                                                width=140, height =35,
                                                corner_radius =15,
                                                border_color ="#00A8E8",
                                                button_color="#00A8E8",
                                                button_hover_color="#0086BA",
                                                dropdown_fg_color="#FFFFFF",
                                                text_color="#333333")
        self.combo_idioma.set("Español") #valor por defecto
        self.combo_idioma.pack(side="left", padx=10)

        #los botones a la derecha
        self.btn_iniciar = ctk.CTkButton(self.frame_controles, text="▶ INICIAR",
                                         command=self.incio_hilo_audio, font=("Segoe UI Bold", 14),
                                         fg_color="#00C2E0",hover_color = "#33D6F2",
                                         width=130, height=45, border_color="#008FB3", corner_radius =15 )
        self.btn_iniciar.pack(side="right", padx=10)
        
        self.btn_detener = ctk.CTkButton(self.frame_controles, text="■ DETENER",
                                            command=self.detener_sistema, state="disabled",
                                            font=("Segoe UI Bold", 14),
                                            fg_color="#FF5E78", hover_color="#FF8599",
                                            border_color="#CC334D",
                                            corner_radius =20,
                                            width=130, height=45)
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
            self.btn_iniciar.configure(state="disabled", fg_color="#A0E0E0", border_color="#80B0B0")
            self.combo_idioma.configure(state="disabled") #desabilitamos la eleccion de idioma
            self.btn_detener.configure(state="normal", fg_color="#FF5E78", border_color="#CC334D") #habilitamos el boton de detener
            self.txt_log.insert("end", "SISTEMA INICIADO. PUEDES HABLAR AHORA.\n")

    def detener_sistema(self):
             self.motor.detener_sistema()

             #actualizamos la interfaz
             self.combo_idioma.configure(state = "normal")
             self.btn_iniciar.configure(state="normal", fg_color="#00C2E0", border_color="#008FB3")
             self.btn_detener.configure(state="disabled", fg_color="#FFB0BD", border_color="#CC808E") #desabilitamos el boton de detener
             self.txt_log.insert("end","\n--- Sistema detenido ---\n")
             self.txt_log.see("end")
            
if __name__ == "__main__":
    app = TraslSpeakApp()
    app.mainloop()