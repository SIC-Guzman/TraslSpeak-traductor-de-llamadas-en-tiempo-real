import customtkinter as ctk
import threading
import pyaudio
import numpy as np
from faster_whisper import WhisperModel
from gtts import gTTS
import os
import time
from deep_translator import GoogleTranslator
import sounddevice as sd
import soundfile as sf
import platform 

# --- CONFIGURACIÓN DE IDs DIRECTA PARA WINDOWS ---
CABLE_INPUT_ID = 4      # VB-Cable Input (App habla a Zoom)
CABLE_OUTPUT_ID = 2     # VB-Cable Output (App escucha a Zoom)
REAL_MIC_ID = None      
REAL_SPEAKER_ID = None  
# ----------------------------------------------------

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class HandsFreeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.is_running = False
        self.is_injecting_audio = False 

        # --- NUEVA VARIABLE DE ESTADO DE IDIOMA ---
        # True: Dirección principal es ES -> EN (Tú hablas español)
        # False: Dirección principal es EN -> ES (Tú hablas inglés)
        self.es_to_en = True 
        # ------------------------------------------

        # Asignación de IDs de Windows
        self.CABLE_INPUT_ID = CABLE_INPUT_ID
        self.CABLE_OUTPUT_ID = CABLE_OUTPUT_ID
        self.REAL_MIC_ID = REAL_MIC_ID
        self.REAL_SPEAKER_ID = REAL_SPEAKER_ID
        self.cable_status = (self.CABLE_INPUT_ID is not None and self.CABLE_OUTPUT_ID is not None)

        # --- Interfaz de dos paneles ---
        self.title("TraslSpeak - Manos Libres") 
        self.geometry("1000x700")
        self.configure(fg_color="#D9F2FF") 
        self.resizable(True, True)

        self.label_title = ctk.CTkLabel(self, text=f"TraslSpeak", 
                                         font=("Segoe UI Bold", 26), text_color="#006699")
        self.label_title.pack(pady=(20, 10))

        # Estructura principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # PANEL IZQUIERDO (TÚ)
        self.frame_user = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="white", border_color="#00A8E8", border_width=3)
        self.frame_user.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.lbl_user_lang = ctk.CTkLabel(self.frame_user, text="👤 TU VOZ (ESPAÑOL)", font=("Segoe UI Bold", 16), text_color="#006699")
        self.lbl_user_lang.pack(pady=10)
        self.status_usuer = ctk.CTkLabel(self.frame_user, text="ESPERANDO.........." , text_color="gray")
        self.status_usuer.pack(pady=5)
        self.txt_user = ctk.CTkTextbox(self.frame_user, font=("Segoe UI", 13), fg_color="#F0F8FF", corner_radius=15, wrap="word")
        self.txt_user.pack(fill="both", expand=True, padx=15, pady=15)
        self.txt_user.configure(state="disabled")

        # PANEL DERECHO (ELLOS)
        self.frame_other = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="white", border_color="#00C2E0", border_width=3)
        self.frame_other.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.lbl_other_lang = ctk.CTkLabel(self.frame_other, text="🤖 RECEPTOR (INGLÉS)", font=("Segoe UI Bold", 16), text_color="#008FB3")
        self.lbl_other_lang.pack(pady=10)
        self.status_other = ctk.CTkLabel(self.frame_other, text="ESPERANDO.................", text_color="gray")
        self.status_other.pack(pady=5)
        self.txt_other = ctk.CTkTextbox(self.frame_other, font=("Segoe UI", 13), fg_color="#F0FFFF", corner_radius=15, wrap="word")
        self.txt_other.pack(fill="both", expand=True, padx=15, pady=15)
        self.txt_other.configure(state="disabled")

        # BARRA DE CONTROL
        self.frame_controles = ctk.CTkFrame(self, height=80, fg_color="transparent")
        self.frame_controles.pack(fill="x", pady=20, padx=20, side="bottom")

        # --- BOTÓN DE CONMUTACIÓN DE IDIOMAS ---
        self.btn_switch_lang = ctk.CTkButton(self.frame_controles, text="🔄 CONMUTAR IDIOMAS", command=self.switch_languages, 
                                             fg_color="#0099CC", hover_color="#00BFFF", height=30, font=("Segoe UI Bold", 14))
        self.btn_switch_lang.pack(side="left", padx=10, fill="y")
        
        # Botón principal START/STOP
        self.btn_accion = ctk.CTkButton(self.frame_controles, text="CARGANDO CEREBROS IA...", command=self.toggle_system, 
                                         fg_color="gray", state="disabled", height=50, font=("Segoe UI Bold", 18))
        self.btn_accion.pack(side="left", fill="x", expand=True, padx=10) # Ajustado para dejar espacio al botón de cambio
        
        # Etiqueta de estado de la conexión
        self.cable_status_label = ctk.CTkLabel(self.frame_controles, text="Configurando IDs...", font=("Segoe UI", 12))
        self.cable_status_label.pack(side="right", padx=10, fill="y")

        # Iniciar carga en hilo aparte
        threading.Thread(target=self.load_model).start()
    
    # ----------------------------------------------------
    # --- NUEVA LÓGICA DE CONMUTACIÓN DE IDIOMAS ---
    # ----------------------------------------------------

    def switch_languages(self):
        """Invierte la dirección de traducción y actualiza las etiquetas."""
        if self.is_running:
            self.log_to_gui("USER", "🛑 Detén el sistema antes de cambiar los idiomas.")
            return

        self.es_to_en = not self.es_to_en
        
        if self.es_to_en:
            user_lang = "ESPAÑOL"
            other_lang = "INGLÉS"
        else:
            user_lang = "INGLÉS"
            other_lang = "ESPAÑOL"
            
        self.lbl_user_lang.configure(text=f"👤 TU VOZ ({user_lang})")
        self.lbl_other_lang.configure(text=f"🤖 RECEPTOR ({other_lang})")
        
        self.log_to_gui("USER", f"✅ Idiomas cambiados: TÚ hablas {user_lang}.")
        self.log_to_gui("OTHER", f"✅ Receptor espera {other_lang}.")
        
    def get_user_lang_codes(self):
        """Retorna (origen, destino) para el Hilo 1 (Tú)."""
        return ("es", "en") if self.es_to_en else ("en", "es")

    def get_other_lang_codes(self):
        """Retorna (origen, destino) para el Hilo 2 (Ellos)."""
        return ("en", "es") if self.es_to_en else ("es", "en")


    # ----------------------------------------------------
    # --- FUNCIONES DE CONTROL Y HILOS (ACTUALIZADAS) ---
    # ----------------------------------------------------

    def clear_logs(self):
        """Limpia el contenido de los TextBoxes de usuario y receptor."""
        for box in [self.txt_user, self.txt_other]:
            box.configure(state="normal")
            box.delete("1.0", "end")
            box.configure(state="disabled")

    def load_model(self):
        try:
            if not self.cable_status:
                 self.log_to_gui("USER", "ERROR: CABLES VIRTUALES NO ENCONTRADOS.")
                 self.btn_accion.configure(state="disabled", fg_color="red")
                 self.cable_status_label.configure(text=f"ERROR: Revisa IDs {CABLE_INPUT_ID}/{CABLE_OUTPUT_ID}.", text_color="red")
                 return

            self.model = WhisperModel("small", device="cpu", compute_type="int8")
            self.p = pyaudio.PyAudio()
            
            self.log_to_gui("USER", "SISTEMA LISTO. Dale a START.")
            self.log_to_gui("OTHER", "SISTEMA LISTO.")
            self.btn_accion.configure(state="normal", fg_color="#00C2E0", text="▶ START", hover_color="#33D6F2")
            self.cable_status_label.configure(text=f"Conexión Lista.", text_color="green")
            
        except Exception as e:
            self.log_to_gui("USER", f"Error cargando: {e}")

    def toggle_system(self):
        if not self.is_running:
            self.clear_logs() 
            self.is_running = True
            self.btn_accion.configure(text="⏹ STOP", fg_color="#FF5E78", hover_color="#FF8599")
            
            # INICIAMOS LOS DOS HILOS
            threading.Thread(target=self.thread_user_listener, daemon=True).start()
            threading.Thread(target=self.thread_zoom_listener, daemon=True).start()
        else:
            self.is_running = False
            self.btn_accion.configure(text="▶ START", fg_color="#00C2E0")
            self.update_label(self.status_usuer, "Inactivo", "gray")
            self.update_label(self.status_other, "Inactivo", "gray")

    # --- HILO 1: TE ESCUCHA A TI (ACTUALIZADO) ---
    def thread_user_listener(self):
        CHUNK = 1024; FORMAT = pyaudio.paInt16; CHANNELS = 1; RATE = 16000
        
        # Obtener códigos de idioma al inicio del hilo
        user_src, user_dest = self.get_user_lang_codes()
        
        try:
            stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, 
                                 input_device_index=self.REAL_MIC_ID, frames_per_buffer=CHUNK)
        except: return
        
        frames = []; silence_start = None; is_speaking = False
        while self.is_running:
            try:
                if self.is_injecting_audio: time.sleep(0.1); continue
                data = stream.read(CHUNK, exception_on_overflow=False)
                volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                if volume > 500:
                    if not is_speaking: self.update_label(self.status_usuer, f"ESCUCHANDO {user_src.upper()}...", "#00AA00")
                    is_speaking = True; silence_start = None; frames.append(data)
                elif is_speaking:
                    frames.append(data)
                    if silence_start is None: silence_start = time.time()
                    if (time.time() - silence_start > 1.0): 
                        self.update_label(self.status_usuer, "TRADUCIENDO...", "#FFA500")
                        self.save_audio(frames, "temp_me.wav"); frames = []; is_speaking = False
                        text = self.transcribe_audio(user_src, "temp_me.wav")
                        if text:
                            trans = self.translate_text(text, user_src, user_dest) # Usa códigos dinámicos
                            self.display_msg("USER", text, trans, user_src, user_dest) # Pasa códigos
                            self.speak_to_cable(trans, user_dest) 
                        self.update_label(self.status_usuer, "ESPERANDO...", "gray")
            except: break
        stream.stop_stream(); stream.close()

    # --- HILO 2: ESCUCHA A ZOOM (ACTUALIZADO) ---
    def thread_zoom_listener(self):
        CHUNK = 1024; FORMAT = pyaudio.paInt16; CHANNELS = 1; RATE = 16000
        
        # Obtener códigos de idioma al inicio del hilo
        other_src, other_dest = self.get_other_lang_codes()
        
        try:
            stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, 
                                 input_device_index=self.CABLE_OUTPUT_ID, frames_per_buffer=CHUNK)
        except Exception as e: self.log_to_gui("OTHER", f"Error Cable: {e}"); return
        frames = []; silence_start = None; is_speaking = False
        while self.is_running:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                if self.is_injecting_audio: frames = []; is_speaking = False; continue
                volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                if volume > 300: 
                    if not is_speaking: self.update_label(self.status_other, f" RECIBIENDO {other_src.upper()}...", "#0000AA")
                    is_speaking = True; silence_start = None; frames.append(data)
                elif is_speaking:
                    frames.append(data)
                    if silence_start is None: silence_start = time.time()
                    if (time.time() - silence_start > 1.0):
                        self.update_label(self.status_other, "TRADUCIENDO...", "#FFA500")
                        self.save_audio(frames, "temp_zoom.wav"); frames = []; is_speaking = False
                        text = self.transcribe_audio(other_src, "temp_zoom.wav")
                        if text:
                            trans = self.translate_text(text, other_src, other_dest) # Usa códigos dinámicos
                            self.display_msg("OTHER", text, trans, other_src, other_dest) # Pasa códigos
                            self.speak_to_speakers(trans, other_dest)
                        self.update_label(self.status_other, "ESPERANDO...", "gray")
            except: break
        stream.stop_stream(); stream.close()

    # --- FUNCIONES AUXILIARES (Actualizada display_msg) ---
    def speak_to_cable(self, text, lang):
        self.is_injecting_audio = True
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save("out_cable.mp3")
            data, fs = sf.read("out_cable.mp3", dtype='float32')
            sd.play(data, fs, device=self.CABLE_INPUT_ID)
            sd.wait()
        except Exception as e: self.log_to_gui("USER", f"Error de voz a Zoom: {e}")
        time.sleep(0.5) 
        self.is_injecting_audio = False 

    def speak_to_speakers(self, text, lang):
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save("out_speaker.mp3")
            data, fs = sf.read("out_speaker.mp3", dtype='float32')
            sd.play(data, fs, device=self.REAL_SPEAKER_ID)
            sd.wait()
        except Exception as e: self.log_to_gui("OTHER", f"Error de voz interna: {e}")

    def transcribe_audio(self, lang_code, file="temp_audio.wav"):
        try:
            segments, _ = self.model.transcribe(file, beam_size=5, language=lang_code)
            return "".join([s.text for s in segments]).strip()
        except: return ""

    def translate_text(self, text, src, dest):
        try: return GoogleTranslator(source=src, target=dest).translate(text)
        except: return text

    def save_audio(self, frames, filename="temp_audio.wav"):
        import wave
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
        wf.writeframes(b''.join(frames)); wf.close()

    def display_msg(self, side, original, translated, src_code, dest_code): # Función actualizada
        target_box = self.txt_user if side == "USER" else self.txt_other
        target_box.configure(state="normal")
        
        # Etiquetas dinámicas
        if side == "USER":
            original_tag = f"[TÚ ({src_code.upper()})]: "
            translated_tag = f"[ELLOS ({dest_code.upper()})]: "
        else: 
            original_tag = f"[ELLOS ({src_code.upper()})]: "
            translated_tag = f"[TÚ ({dest_code.upper()})]: "

        target_box.insert("end", original_tag, "tag_original")
        target_box.insert("end", original + "\n", "text_original")
        
        target_box.insert("end", translated_tag, "tag_translated")
        target_box.insert("end", translated + "\n\n", "text_translated")
        
        target_box.see("end")
        target_box.configure(state="disabled")

    def log_to_gui(self, side, text):
        target_box = self.txt_user if side == "USER" else self.txt_other
        target_box.configure(state="normal")
        target_box.insert("end", f">>> {text}\n", "log_system")
        target_box.see("end")
        target_box.configure(state="disabled")

    def update_label(self, label, text, color):
        try: label.configure(text=text, text_color=color)
        except: pass

if __name__ == "__main__":
    app = HandsFreeApp()
    app.mainloop()