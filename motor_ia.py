import threading
import pyaudio
import numpy as np
import torch
from faster_whisper import WhisperModel
# Tus módulos
from modulo_traduccion import Traductor
from modulo_voz import SintetizadorVoz

# --- IMPORTS PARA FORZAR VOLUMEN ---
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, ISimpleAudioVolume
import os

# --- FUNCIÓN PARA SUBIR VOLUMEN AL 100% ---
def forzar_volumen_al_maximo():
    """Busca este programa en el mezclador de Windows y lo sube al 100%"""
    try:
        sessions = AudioUtilities.GetAllSessions()
        pid_actual = os.getpid() # El ID de este proceso de Python
        
        for session in sessions:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.pid == pid_actual:
                # Descomentar el print si quieres ver cuándo ocurre
                # print(f"🔊 FORZANDO VOLUMEN AL 100% (PID: {pid_actual})")
                volume.SetMasterVolume(1.0, None) # 1.0 es el 100%
                session.SimpleAudioVolume.SetMute(0, None) 
    except Exception as e:
        print(f"No se pudo forzar el volumen: {e}")

class MotorIA:
    def __init__(self, cola_mensajes):
        self.cola_mensajes = cola_mensajes
        self.ejecutando = False
        self.idioma_detectar = 'es' 
        self.traductor = None 
        self.indice_microfono = None 
        
        # Módulo 5 (Voz)
        self.sintetizador = SintetizadorVoz()

    def obtener_microfonos(self):
        p = pyaudio.PyAudio()
        info = []
        nombres_vistos = set() 
        palabras_prohibidas = ["mapper", "asignador", "controlador primario", "primary", "mezcla", "stereo mix", "line in"]

        try:
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                nombre = dev['name']
                try: nombre = nombre.encode('cp1252').decode('utf-8')
                except: pass
                
                if dev['maxInputChannels'] > 0:
                    es_valido = True
                    for prohibida in palabras_prohibidas:
                        if prohibida in nombre.lower(): es_valido = False; break
                    
                    if es_valido and nombre not in nombres_vistos:
                        info.append((i, nombre))
                        nombres_vistos.add(nombre)
        except: pass
        p.terminate()
        return info

    def verificar_cable_virtual(self):
        p = pyaudio.PyAudio()
        detectado = False
        try:
            for i in range(p.get_device_count()):
                if "CABLE" in p.get_device_info_by_index(i)['name']: detectado = True; break
        except: pass
        p.terminate()
        return detectado

    def configurar_idioma(self, idioma_code):
        self.idioma_detectar = idioma_code
        origen = idioma_code
        destino = "en" if idioma_code == "es" else "es"
        try:
            self.traductor = Traductor(origen=origen, destino=destino)
        except Exception as e:
            self.cola_mensajes.put(f"❌ Error Módulo 3 (Traducción): {e}")

    def iniciar_escuchar(self, indice_mic=None):
        if not self.ejecutando:
            self.indice_microfono = indice_mic 
            self.ejecutando = True
            
            # --- TRUCO: Forzamos el volumen justo al iniciar ---
            forzar_volumen_al_maximo()
            
            hilo = threading.Thread(target = self._bucle_audio_logic)
            hilo.daemon = True 
            hilo.start()

    def detener_sistema(self):
        self.ejecutando = False
    
    def _bucle_audio_logic(self):
        try:
            if self.traductor is None: self.configurar_idioma('es')

            # --- CARGA DE MODELOS ---
            vad_model = None
            whisper = None

            # 1. Intentar cargar VAD
            try:
                # self.cola_mensajes.put("⚙️ Cargando Detector de Voz (VAD)...")
                paquete_vad = torch.hub.load("snakers4/silero-vad", "silero_vad", force_reload=False, trust_repo=True)
                vad_model = paquete_vad[0] if isinstance(paquete_vad, tuple) else paquete_vad
            except Exception as e:
                self.cola_mensajes.put(f"❌ ERROR VAD: {str(e)}")
                self.ejecutando = False
                return

            # 2. Intentar cargar Whisper
            try:
                # self.cola_mensajes.put("⚙️ Cargando Whisper (Oído)...")
                whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            except Exception as e:
                self.cola_mensajes.put(f"❌ Error Whisper: {str(e)}")
                self.ejecutando = False
                return

            self.cola_mensajes.put("✅ SISTEMA EN LÍNEA.")

            p = pyaudio.PyAudio()
            # Búfer en 512 para evitar errores de Silero
            kwargs = {'format': pyaudio.paInt16, 'channels': 1, 'rate': 16000, 'input': True, 'frames_per_buffer': 512}
            
            if self.indice_microfono is not None: 
                kwargs['input_device_index'] = self.indice_microfono
            
            stream = p.open(**kwargs)
            
            buffer_audio = []
            voz_activa = False
            silencio_cont = 0
            
            while self.ejecutando:
                try:
                    data = stream.read(512, exception_on_overflow=False)
                    audio_int16 = np.frombuffer(data, np.int16)
                    audio_float32 = (audio_int16.astype(np.float32) / 32768.0)
                    
                    # Detección de voz
                    prob_voz = vad_model(torch.from_numpy(audio_float32), 16000).item()

                    if prob_voz > 0.35:
                        voz_activa = True; silencio_cont = 0
                        buffer_audio.append(audio_float32)
                    elif voz_activa:
                        buffer_audio.append(audio_float32); silencio_cont += 1

                        if silencio_cont > 30: 
                            self.cola_mensajes.put("⏳...")
                            audio_completo = np.concatenate(buffer_audio)
                            
                            # Transcribir
                            segmentos, _ = whisper.transcribe(audio_completo, language=self.idioma_detectar, beam_size=5)
                            texto = "".join([s.text for s in segmentos]).strip()

                            if texto:
                                bandera = "🇪🇸" if self.idioma_detectar == 'es' else "🇺🇸"
                                self.cola_mensajes.put(f"{bandera} Ellos: {texto}")

                                if self.traductor:
                                    trad = self.traductor.traducir(texto)
                                    bandera_dest = "🇺🇸" if self.idioma_detectar == 'es' else "🇪🇸"
                                    self.cola_mensajes.put(f"{bandera_dest} Traducción: {trad}")
                                    self.cola_mensajes.put("---")
                                    
                                    # Forzamos volumen otra vez antes de hablar por si Windows lo bajó
                                    forzar_volumen_al_maximo()
                                    self.sintetizador.hablar(trad)

                            buffer_audio = []; voz_activa = False; silencio_cont = 0
                except OSError: break 
            
            stream.stop_stream(); stream.close(); p.terminate()

        except Exception as e:
            self.cola_mensajes.put(f"ERROR GENERAL: {str(e)}")
            self.ejecutando = False