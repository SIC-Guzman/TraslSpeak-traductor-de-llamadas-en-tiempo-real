import customtkinter as ctk
import threading
import time
import queue
import numpy as np
import pyaudio
import torch
from motor_ia import MotorIA 
from modulo_traduccion import Traductor  
from transformers import MarianMTModel, MarianTokenizer

# --- LIBRERÍAS PARA FORZAR EL VOLUMEN (Anti-Bloqueo de Windows) ---
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, ISimpleAudioVolume
import os

# --- FUNCIÓN MAGICA: Sube el volumen a la fuerza ---
def forzar_volumen_al_maximo():
    """Busca este programa en Windows y sube su volumen al 100%"""
    try:
        sessions = AudioUtilities.GetAllSessions()
        pid_actual = os.getpid() # Identificamos nuestro propio programa
        
        for session in sessions:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.pid == pid_actual:
                print(f"🔊 HACK DE VOLUMEN: Forzando al 100% (PID: {pid_actual})")
                volume.SetMasterVolume(1.0, None) # 1.0 = 100%
                session.SimpleAudioVolume.SetMute(0, None) # Quitar Mute
    except Exception as e:
        print(f"⚠️ No se pudo forzar volumen (Quizás falta instalar pycaw): {e}")

# Configuración de la parte visual
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class TraslSpeakApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TraslSpeak")
        self.geometry("850x700") 
        self.configure(fg_color = "#D9F2FF")

        # El título arriba del todo
        self.lbl_titulo = ctk.CTkLabel(self, text="TraslSpeak", 
                                       font=("Segoe UI Bold", 24), text_color="#006699")
        self.lbl_titulo.pack(pady=(20, 10))

        # --- ÁREA DE CONFIGURACIÓN DE AUDIO ---
        self.frame_config = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_config.pack(pady=(0, 10), padx=30, fill="x")

        # 1. Selector de Micrófono
        self.lbl_mic = ctk.CTkLabel(self.frame_config, text="🎤 Entrada:", font=("Segoe UI Bold", 14), text_color="#006699")
        self.lbl_mic.pack(side="left", padx=(5, 5))
        
        self.combo_mic = ctk.CTkComboBox(self.frame_config, font=("Segoe UI", 12),
                                         width=250, height=30,
                                         state="readonly",
                                         corner_radius=15,
                                         border_color="#00A8E8",
                                         button_color="#00A8E8",
                                         button_hover_color="#0086BA",
                                         dropdown_fg_color="#FFFFFF",
                                         text_color="#333333")
        self.combo_mic.pack(side="left", padx=5)

        # 2. Indicador de Salida (Cable)
        self.lbl_salida_status = ctk.CTkLabel(self.frame_config, text="Buscando Cable... 🔍", 
                                              font=("Segoe UI Bold", 13), text_color="#FF8C00") 
        self.lbl_salida_status.pack(side="right", padx=5)
        
        self.lbl_salida_titulo = ctk.CTkLabel(self.frame_config, text="Salida Virtual:", 
                                              font=("Segoe UI", 13), text_color="#333333")
        self.lbl_salida_titulo.pack(side="right", padx=0)
        # -------------------------------------------------------------------

        # El área del texto (Log)
        self.frame_central = ctk.CTkFrame(self, 
                                          corner_radius=15,
                                          fg_color="#FFFFFF",
                                          border_color= "#8ED6FF",
                                          border_width= 3)
        self.frame_central.pack(pady=10, padx=30, fill="both", expand=True)

        # La caja de texto
        self.txt_log = ctk.CTkTextbox(self.frame_central, font=("Segoe UI", 14),
                                      corner_radius= 15,
                                      fg_color="#F0F8FF",
                                      border_color= "#BCE0FD",
                                      border_width=2,
                                      text_color="#333333")
        self.txt_log.pack(pady=20, padx=20, fill="both", expand=True)
        self.txt_log.insert("0.0", "Bienvenido. Seleccione su micrófono, idioma y presione Iniciar.\n")

        # La barra de controles
        self.frame_controles = ctk.CTkFrame(self, height=90, fg_color="transparent")
        self.frame_controles.pack(pady=20, padx=30, fill="x", side="bottom")

        # Para elegir el idioma
        self.lbl_idioma = ctk.CTkLabel(self.frame_controles, text="Idioma:", font=("Segoe UI", 12), text_color="#333333")
        self.lbl_idioma.pack(side="left", padx=(5,5))

        self.combo_idioma = ctk.CTkComboBox(self.frame_controles, font=("Segoe UI", 12),
                                            values=["Español", "Inglés"],
                                            state="readonly",
                                            width=140, height=35,
                                            corner_radius=15,
                                            border_color="#00A8E8",
                                            button_color="#00A8E8",
                                            button_hover_color="#0086BA",
                                            dropdown_fg_color="#FFFFFF",
                                            text_color="#333333")
        self.combo_idioma.set("Español") 
        self.combo_idioma.pack(side="left", padx=5)

        # Botones a la derecha
        self.btn_iniciar = ctk.CTkButton(self.frame_controles, text="▶ INICIAR",
                                         command=self.incio_hilo_audio, font=("Segoe UI Bold", 14),
                                         fg_color="#00C2E0", hover_color="#33D6F2",
                                         width=130, height=45, border_color="#008FB3", corner_radius=15)
        self.btn_iniciar.pack(side="right", padx=10)
        
        self.btn_detener = ctk.CTkButton(self.frame_controles, text="■ DETENER",
                                         command=self.detener_sistema, state="disabled",
                                         font=("Segoe UI Bold", 14),
                                         fg_color="#FF5E78", hover_color="#FF8599",
                                         border_color="#CC334D",
                                         corner_radius=20,
                                         width=130, height=45)
        self.btn_detener.pack(side="right", padx=10)

        # Hilos
        self.cola_mensajes = queue.Queue()
        self.check_hilos()

        # Instancia del motor de IA
        self.motor = MotorIA(self.cola_mensajes)
        
        # --- CARGAR DISPOSITIVOS AL INICIAR ---
        self.cargar_dispositivos()

    def cargar_dispositivos(self):
        # 1. Llenar lista de micrófonos
        micros = self.motor.obtener_microfonos()
        self.lista_micros_indices = [] # ID oculto
        nombres_micros = [] # Nombre bonito
        
        for idx, nombre in micros:
            self.lista_micros_indices.append(idx)
            nombre_corto = (nombre[:40] + '..') if len(nombre) > 40 else nombre
            nombres_micros.append(nombre_corto)
            
        if nombres_micros:
            self.combo_mic.configure(values=nombres_micros)
            self.combo_mic.set(nombres_micros[0])
        else:
            self.combo_mic.set("No se detectaron micros")

        # 2. Verificar si el Cable está instalado
        if self.motor.verificar_cable_virtual():
            self.lbl_salida_status.configure(text="VB-CABLE Detectado ✅", text_color="#009900") 
        else:
            self.lbl_salida_status.configure(text="No detectado ❌", text_color="#FF0000") 

    def check_hilos(self):
        try:
            while True:
                mensaje = self.cola_mensajes.get_nowait()
                self.txt_log.insert("end", mensaje + "\n")
                self.txt_log.see("end")
        except queue.Empty:
            pass
        self.after(100, self.check_hilos)
    
    def incio_hilo_audio(self):
        # --- AQUÍ APLICAMOS EL HACK OTRA VEZ AL INICIAR ---
        try:
            forzar_volumen_al_maximo()
        except: pass

        seleccion = self.combo_idioma.get()
        idioma_codigo = "en" if "Inglés" in seleccion else "es"
        self.motor.configurar_idioma(idioma_codigo)

        indice_seleccionado = None
        try:
            texto_combo = self.combo_mic.get()
            lista_nombres = self.combo_mic.cget("values")
            posicion_en_lista = lista_nombres.index(texto_combo)
            indice_seleccionado = self.lista_micros_indices[posicion_en_lista]
        except:
            self.cola_mensajes.put("⚠️ Usando micrófono por defecto.")

        self.motor.iniciar_escuchar(indice_seleccionado)

        self.btn_iniciar.configure(state="disabled", fg_color="#A0E0E0", border_color="#80B0B0")
        self.combo_idioma.configure(state="disabled")
        self.combo_mic.configure(state="disabled") 
        self.btn_detener.configure(state="normal", fg_color="#FF5E78", border_color="#CC334D")
        self.txt_log.insert("end", "SISTEMA INICIADO. PUEDES HABLAR AHORA.\n")

    def detener_sistema(self):
        self.motor.detener_sistema()
        self.combo_idioma.configure(state="normal")
        self.combo_mic.configure(state="normal") 
        self.btn_iniciar.configure(state="normal", fg_color="#00C2E0", border_color="#008FB3")
        self.btn_detener.configure(state="disabled", fg_color="#FFB0BD", border_color="#CC808E")
        self.txt_log.insert("end","\n--- Sistema detenido ---\n")
        self.txt_log.see("end")
            
if __name__ == "__main__":
    # --- EJECUTAR EL HACK DE VOLUMEN AL ABRIR ---
    try:
        forzar_volumen_al_maximo()
    except Exception as e:
        print(f"Error forzando volumen: {e}")
        print("NOTA: Si falla, ejecuta 'pip install pycaw comtypes'")

    app = TraslSpeakApp()
    app.mainloop()