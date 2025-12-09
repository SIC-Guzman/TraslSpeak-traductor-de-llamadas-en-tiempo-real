import threading
import pyaudio
import numpy as np
import torch
from faster_whisper import WhisperModel
from modulo_traduccion import Traductor

class MotorIA:
    def __init__(self, cola_mensajes):
        self.cola_mensajes = cola_mensajes
        self.ejecutando = False
        self.stream = None
        self.p_audio = None
        self.idioma_detectar = 'es' 
        self.traductor = None 

    def configurar_idioma(self, idioma_code):
        self.idioma_detectar = idioma_code
        origen = idioma_code
        destino = "en" if idioma_code == "es" else "es"
        
        # Mensaje opcional, si también quieren quitar este, borra la linea de abajo
        self.cola_mensajes.put(f"⚙️ Configurando traducción: {origen.upper()} ➡️ {destino.upper()}...")
        
        try:
            self.traductor = Traductor(origen=origen, destino=destino)
        except Exception as e:
            self.cola_mensajes.put(f"❌ Error cargando MarianMT: {e}")

    def iniciar_escuchar(self):
        if not self.ejecutando:
            self.ejecutando = True
            hilo = threading.Thread(target = self._bucle_audio_logic)
            hilo.daemon = True 
            hilo.start()

    def detener_sistema(self):
        self.ejecutando = False
    
    def _bucle_audio_logic(self):
        try:
            if self.traductor is None:
                self.configurar_idioma('es')

            # --- SECCIÓN EDITADA: Ya no mostramos el mensaje de carga ---
            # (El sistema sigue cargando, pero en silencio para el usuario)

            # Cargar VAD
            paquete_vad = torch.hub.load("snakers4/silero-vad", "silero_vad", force_reload=False, trust_repo=True)
            if isinstance(paquete_vad, tuple): vad_model = paquete_vad[0]
            else: vad_model = paquete_vad

            # Cargar Whisper
            whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            
            # Solo mostramos cuando ya está listo
            self.cola_mensajes.put("✅ TODO LISTO. PUEDES HABLAR AHORA.\n")

            # Audio
            self.p_audio = pyaudio.PyAudio()
            self.stream = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
            
            buffer_audio = []
            voz_activa = False
            silencio_cont = 0
            Umbral_Voz = 0.35
            Limite_Silencio = 30 

            while self.ejecutando:
                try:
                    data = self.stream.read(512, exception_on_overflow=False)
                    audio_int16 = np.frombuffer(data, np.int16)
                    audio_float32 = (audio_int16.astype(np.float32) / 32768.0) * 1.5 
                    
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
                            self.cola_mensajes.put("⏳ Procesando...")
                            audio_completo = np.concatenate(buffer_audio)

                            # 1. TRANSCRIBIR
                            segmentos, _ = whisper.transcribe(audio_completo, language=self.idioma_detectar, beam_size=5)
                            texto_origen = "".join([s.text for s in segmentos]).strip()

                            if texto_origen:
                                bandera_origen = "🇪🇸" if self.idioma_detectar == 'es' else "🇺🇸"
                                self.cola_mensajes.put(f"{bandera_origen} Escuchado: {texto_origen}")

                                # 2. TRADUCIR
                                if self.traductor:
                                    texto_traducido = self.traductor.traducir(texto_origen)
                                    bandera_destino = "🇺🇸" if self.idioma_detectar == 'es' else "🇪🇸"
                                    self.cola_mensajes.put(f"{bandera_destino} Traducido: {texto_traducido}")
                                    self.cola_mensajes.put("----------------")
                            
                            buffer_audio = []
                            voz_activa = False
                            silencio_cont = 0

                except OSError:
                    break 
        
            if self.stream: self.stream.stop_stream(); self.stream.close()
            if self.p_audio: self.p_audio.terminate()

        except Exception as e:
            self.cola_mensajes.put(f"ERROR: {str(e)}")