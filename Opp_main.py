import customtkinter as ctk
import threading
import time
import queue
import numpy as np
import pyaudio
import torch
from faster_whisper import WhisperModel

#la configuracion de la parte visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TraslSpeakApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TraslSpeak - Transcripcion de voz en tiempo real")
        self.geometry("800x600")

        #El titulo arriba del todo
        self.lbl_titulo = ctk.CTkLabel(self, text="TraslSpeak - Transcripcion de voz en tiempo real", 
                                       font=("Roboto", 20, "bold"))
        self.lbl_titulo.pack(pady=(20,10))

        #el area del texto
        self.frame_central = ctk.CTkFrame(self, corner_radius=15)
        self.frame_central.pack(pady=10, padx=20, fill="both", expand=True)

        #la etiqueta pequeña dentro del marco
        self.lbl_hisotorial = ctk.CTkLabel(self.frame_central, text="Historial de transcripcion:", 
                                           font=("Roboto Medium", 16), text_color="#AAB0B5")
        self.lbl_hisotorial.pack(pady=(10,5), padx=10, anchor="w")

        #la caja de texto
        self.txt_log = ctk.CTkTextbox(self.frame_central, font=("Roboto", 14))
        self.txt_log.pack(pady=(0,10), padx=10, fill="both", expand=True)
        self.txt_log.insert("0.0", "SISTEMA LISTO. PRESIONA INICIAR PARA COMENZAR.\n")

        #la barra de controles, que estara abajo
        self.frame_controles = ctk.CTkFrame(self, height=80, fg_color="transparent")
        self.frame_controles.pack(pady=10, padx=20, fill="x", side="bottom")

        #el estado del sistema a la izquierda
        self.lbl_estado = ctk.CTkLabel(self.frame_controles, text="🔴 ESTADO: DETENIDO", 
                                    font=("Roboto Medium", 14, "bold"), text_color="#FF5555")
        self.lbl_estado.pack(side="left", padx=20)

        #los botones a la derecha
        self.btn_iniciar = ctk.CTkButton(self.frame_controles, text="▶INICIAR",
                                         command=self.incio_hilo_audio,
                                         fg_color="#2CC985",hover_color = "#A32428" ,width=120, height=40,)
        self.btn_iniciar.pack(side="right", padx=10)
        
        self.btn_detener = ctk.CTkButton(self.frame_controles, text="■ DETENER",
                                            command=self.detener_sistema, state="disabled",
                                            fg_color="#D64045", hover_color="#A32428",
                                            width=120, height=40)
        self.btn_detener.pack(side="right", padx=10)

        #los hilos
        self.cola_mensajes = queue.Queue()
        self.ejecutando = False
        self.stream = None
        self.p_audio = None
        self.check_hilos()

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
            if not self.ejecutando:
                self.ejecutando = True

                #actualizamos la interfaz
                self.lbl_estado.configure(text="ESTADO: ACTIVO ✅", text_color="#2CC985")
                self.btn_iniciar.configure(state="desabled")
                self.btn_detener.configure(state="normal")#acticamos el boton de detener

                self.txt_log.delete("1.0", "end") #limpiamos la oantalla al inciar
                self.txt_log.insert("end","INCIANDO SISTEMA DE TRANSCRIPCION...\n")

    
                #lanzamos el back en un hilo por aparte para no congelar la interfaz
                hilo = threading.Thread(target=self.back_audio)
                hilo.daemon = True #se cierra al cerrar la app
                hilo.start() 
    
    def detener_sistema(self):
         "funcion para detener el sistema de audio"
         if self.ejecutando:
             self.cola_mensajes.put("DETENIENDO EL SISTEMA...")
             self.ejecutando = False

             #actualizamos la interfaz
             self.lbl_estado.configure(text="🔴 ESTADO: DETENIDO", text_color="#FF5555")
             self.btn_iniciar.configure(state="normal")
             self.btn_detener.configure(state="disabled") #desabilitamos el boton de detener
            
    def back_audio(self):
            try:
                #cargar modelos
                self.cola_mensajes.put("CARGANDO MODELO...")
    
                #configuramos el audio
                MODEL_SIZE = "tiny"
                COMPUTE_TYPE = "int8"
                SAMPLE_RATE = 16000
                CHUNK_SIZE = 512
                UMBRAL_VOZ = 0.35
                LIMITE_SILENCIO = 40  # cantidad de chunks de silencio para considerar el fin de la grabación
                GANANCIA_AUDIO = 1.5  # para el microfono, ajustar si el audio es muy bajo
    
                #cargamos los VAD
                paquete_vad = torch.hub.load("snakers4/silero-vad", 
                                           "silero_vad", 
                                           force_reload=False, 
                                           trust_repo=True)
                if isinstance(paquete_vad, tuple):
                    vad_model = paquete_vad[0]
                else:
                     vad_model = paquete_vad
    
                #cargar whisper
                Whisper = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
                self.cola_mensajes.put("TODO LISTO. PUEDES HABLAR AHORA.")
    
                #configuramos el microfono
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                input=True,
                                frames_per_buffer=512)
                
                buffer_audio = []
                voz_activa = False
                silencio_cont = 0
    
                #loop principal de captura y procesamiento
                while self.ejecutando:
                    data = stream.read(512, exception_on_overflow=False)

                    #convertir a numeros
                    audio_int16 = np.frombuffer(data, dtype=np.int16)
                    audio_float32 = (audio_int16.astype(np.float32) / 32768.0)* GANANCIA_AUDIO
                    
                    #verificar si hay voz
                    tensor = torch.from_numpy(audio_float32)
    
                    problab_voz = vad_model(tensor, 16000).item()

                    # Esto de aca es para probar como va esto, lo pueden borrar despues si quieren
                    if problab_voz > 0.1: print(f"Nivel: {problab_voz:.2f}")
                    
                    #ligca de grabacion segun VAD
                    if problab_voz > UMBRAL_VOZ:
                        voz_activa = True
                        silencio_cont = 0
                        buffer_audio.append(audio_float32)
                    elif voz_activa:

                        #hubo voz antes, pero ahora silencio
                        buffer_audio.append(audio_float32)
                        silencio_cont += 1

                        if silencio_cont > LIMITE_SILENCIO: #aca detectamos el silencio para luego procesarlo
                            
                            #pequeña marca de proce
                            self.cola_mensajes.put("PROCESANDO⏳...")

                            #unimos y transcribir
                            audio_completo = np.concatenate(buffer_audio)

                            #transcribimos con Whisper
                            segmentos, _ = Whisper.transcribe(audio_completo, beam_size=5, language="es")
                            texto = "".join([s.text for s in segmentos]) #enserio debo de leer mejor 
    
                            #enviamos el texto a la interfaz
                            if texto.strip():
                             self.cola_mensajes.put(f"🗯️: {texto}")
                            buffer_audio = []
                            voz_activa = False
                            silencio_cont = 0
        # limpieza al salir del loop
                self.cola_mensajes.put("SISTEMA DETENIDO.")
                if stream:
                 stream.stop_stream()
                 stream.close()
                if p:
                 p.terminate()
    
            except OSError as oe:
            # si cerramos el stream manualmente, puede que haya problemas, lo vamos a ignorar
             self.cola_mensajes.put("Stream de audio cerrado manualmente.")

            except Exception as e:
             self.cola_mensajes.put(f"Error en el sistema de audio: {str(e)}")
        # reactivamos los botones en caso de error
             self.btn_iniciar.configure(state="normal")
             self.btn_detener.configure(state="disabled")
    
if __name__ == "__main__":
    app = TraslSpeakApp()
    app.mainloop()