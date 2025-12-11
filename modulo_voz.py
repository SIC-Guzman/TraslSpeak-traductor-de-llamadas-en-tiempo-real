import pyttsx3
import threading
import queue
import time

class SintetizadorVoz:
    def __init__(self):
        self.cola_audio = queue.Queue()
        self.activo = True
        
        # Iniciamos un hilo dedicado EXCLUSIVAMENTE a hablar
        # Así no interfiere con el hilo que escucha
        self.hilo = threading.Thread(target=self._proceso_hablar)
        self.hilo.daemon = True
        self.hilo.start()

    def hablar(self, texto):
        if texto:
            self.cola_audio.put(texto)

    def _proceso_hablar(self):
        # Este motor vive solo en este hilo para no molestar a los demás
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 145)
            engine.setProperty('volume', 100.0)
            
            while self.activo:
                try:
                    # Esperamos a que llegue texto (timeout para poder cerrar si es necesario)
                    texto = self.cola_audio.get(timeout=1)
                    
                    # print(f"🔊 Generando voz: {texto}") # Descomentar para depurar
                    engine.say(texto)
                    engine.runAndWait()
                    
                    self.cola_audio.task_done()
                except queue.Empty:
                    pass
                except Exception:
                    # Si falla, a veces ayuda reinicializar
                    try: engine = pyttsx3.init()
                    except: pass
        except:
            pass