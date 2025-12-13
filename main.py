import pyaudio
import numpy as np
from faster_whisper import WhisperModel
from gtts import gTTS
import pygame  # Usaremos esto para reproducir el audio sin errores
import time
import os

class TraslPeakCore:
    def __init__(self):
        print("--- INICIANDO TRASLPEAK (Versión Google Voice) ---")
        
        # 1. Configuración del Traductor (Oído)
        print("1. Cargando modelo Whisper...")
        # device="cuda" si tienes tarjeta gráfica NVIDIA, sino "cpu"
        self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        # 2. Configuración del Reproductor de Audio
        pygame.mixer.init()

        # 3. Configuración del Micrófono
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.SILENCE_THRESHOLD = 800
        self.SILENCE_DURATION = 1.0 

        self.p = pyaudio.PyAudio()

    def listen_and_translate(self):
        stream = self.p.open(format=self.FORMAT,
                             channels=self.CHANNELS,
                             rate=self.RATE,
                             input=True,
                             frames_per_buffer=self.CHUNK)

        print("\n>>> LISTO. Habla en ESPAÑOL. (Esperando silencio para traducir)...")
        
        frames = []
        silence_start = None
        is_speaking = False

        while True:
            try:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()

                if volume > self.SILENCE_THRESHOLD:
                    if not is_speaking:
                        print("Escuchando...", end="\r")
                    is_speaking = True
                    silence_start = None 
                else:
                    if is_speaking and silence_start is None:
                        silence_start = time.time()
                    
                    if is_speaking and silence_start and (time.time() - silence_start > self.SILENCE_DURATION):
                        print("\nSilencio detectado. Procesando...")
                        
                        # Pausar micrófono para evitar eco
                        stream.stop_stream()
                        
                        self.save_temp_audio(frames)
                        translated_text = self.process_audio()
                        
                        if translated_text:
                            self.speak_google(translated_text)
                        
                        # Reiniciar ciclo
                        frames = []
                        is_speaking = False
                        silence_start = None
                        stream.start_stream()
                        print("\n>>> Puedes hablar de nuevo...")

            except KeyboardInterrupt:
                break

    def save_temp_audio(self, frames):
        import wave
        wf = wave.open("temp_audio.wav", 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def process_audio(self):
        segments, info = self.model.transcribe("temp_audio.wav", beam_size=5, task="translate")
        full_text = ""
        for segment in segments:
            full_text += segment.text + " "
        
        if full_text.strip():
            print(f"Traducción: {full_text}")
            return full_text
        return None

    def speak_google(self, text):
        try:
            print(f"Hablando (Google): '{text}'")
            
            # Generar el audio con Google TTS
            # lang='en' para inglés. Puedes cambiar a 'fr', 'pt', etc.
            tts = gTTS(text=text, lang='en', slow=False)
            filename = "voice_output.mp3"
            
            # Si el archivo existe de una vuelta anterior, intentar borrarlo
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass
            
            tts.save(filename)
            
            # Reproducir con Pygame
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            # Esperar a que termine de hablar
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # Descargar el archivo de la memoria de pygame para poder borrarlo luego
            pygame.mixer.music.unload()
            
        except Exception as e:
            print(f"Error en el audio: {e}")

if __name__ == "__main__":
    app = TraslPeakCore()
    try:
        app.listen_and_translate()
    except KeyboardInterrupt:
        print("\nApagando TraslPeak...")