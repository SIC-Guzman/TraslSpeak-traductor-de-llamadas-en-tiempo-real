import threading
import numpy as np
import pyaudio
import torch
from faster_whisper import WhisperModel

class MotorIA:
    def __init__(self, cola_mensajes):
        self.cola_mensajes = cola_mensajes
        self.ejecutando = False
        self.stream = None
        self.p_audio = None
        self.idioma_detectar = 'es'  # Idioma predeterminado (El español) para detección

    def configurar_idioma(self, idioma_code):
        "cambiamos el idioma que whisper espera detectar, sea español o ingles"
        self.idioma_detectar = idioma_code

    def iniciar_escuchar(self):
        "Lanzar el proceso en un hilo aparte"
        if not self.ejecutando:
            self.ejecutando = True
            hilo = threading.Thread(target = self._bucle_audio_logic)
            hilo.daemon = True  # se cierra al cerrar la app
            hilo.start()

    def detener_sistema(self):
        "funcion para detener el sistema de audio"
        self.ejecutando = False
    
    def _bucle_audio_logic(self):
        try:
            #cargamos los modelos
            self.cola_mensajes.put(f"CARGANDO MODELO ({self.idioma_detectar})...")

            #el vad
            paquete_vad = torch.hub.load("snakers4/silero-vad", 
                                       "silero_vad", 
                                       force_reload=False, 
                                       trust_repo=True)
            if isinstance(paquete_vad, tuple): vad_model = paquete_vad[0]
            else: vad_model = paquete_vad

            #cargar whisper
            whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            self.cola_mensajes.put("TODO LISTO. PUEDES HABLAR AHORA.\n")
               

            #configuracion del audio
            self.p_audio = pyaudio.PyAudio()

            self.stream = self.p_audio.open(format=pyaudio.paInt16,
                                            channels=1,
                                            rate=16000,
                                            input=True,
                                            frames_per_buffer=512)
            
            #los parametros
            Umbral_Voz = 0.35
            Limite_Silencio = 30  # cantidad de chunks de silencio para considerar el fin de la grabación
            Ganancia_Audio = 1.5  # para el microfono, ajustar si el audio es muy bajo

            buffer_audio = []
            voz_activa = False
            silencio_cont = 0

            #el bucle principal
            while self.ejecutando:
                try:
                    data = self.stream.read(512, exception_on_overflow=False)
                    audio_int16 = np.frombuffer(data, np.int16)

                    #la ganancia
                    audio_float32 = (audio_int16.astype(np.float32) / 32768.0) * Ganancia_Audio
                    audio_float32 = np.clip(audio_float32, -1.0, 1.0)

                    tensor = torch.from_numpy(audio_float32)
                    prob_voz = vad_model(tensor, 16000).item()

                    if prob_voz > Umbral_Voz:
                        voz_activa = True
                        silencio_cont = 0
                        buffer_audio.append(audio_float32)
                    elif voz_activa:
                     buffer_audio.append(audio_float32)
                     silencio_cont += 1

                     if silencio_cont > Limite_Silencio:
                         #procesar el audio
                         self.cola_mensajes.put("⏳....")
                         audio_completo = np.concatenate(buffer_audio)

                         segmentos, _ = whisper.transcribe(audio_completo, language=self.idioma_detectar, beam_size=5)
                         texto = "".join([s.text for s in segmentos])

                         if texto.strip():
                             #le ponemos una banda de para saber el idioma
                             bandera = "🇪🇸" if self.idioma_detectar == 'es' else "🇺🇸"
                             self.cola_mensajes.put(f"{bandera} {texto}")

                         buffer_audio = []
                         voz_activa = False
                         silencio_cont = 0

                except OSError:
                 break #salimos si el stream se cerro
        
            #limpieza al salir del loop
            self.cola_mensajes.put("SISTEMA DETENIDO.")
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.p_audio:
                self.p_audio.terminate()

        except Exception as e:
         self.cola_mensajes.put(f"ERROR: {str(e)}")