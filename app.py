import customtkinter as ctk
import threading
import pyaudio
import numpy as np
from faster_whisper import WhisperModel
import os
import time
import datetime
import asyncio
import edge_tts 
from deep_translator import GoogleTranslator
import sounddevice as sd
import soundfile as sf
import platform 
from tkinter import messagebox 

# --- CONFIGURACIÓN DE AUDIO (ASIGNA TUS IDS AQUÍ) ---
CABLE_INPUT_ID = 4      # VB-Cable Input (Lo que Zoom escucha)
CABLE_OUTPUT_ID = 2     # VB-Cable Output (Lo que sale de Zoom)
REAL_MIC_ID = None      # Tu micrófono físico
REAL_SPEAKER_ID = None  # TUS AUDÍFONOS REALES (PARA QUE TÚ ESCUCHES)

NEURAL_VOICES = {
    "es": "es-MX-DaliaNeural",      
    "en": "en-US-ChristopherNeural" 
}

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class HandsFreeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.CABLE_INPUT_ID = CABLE_INPUT_ID
        self.CABLE_OUTPUT_ID = CABLE_OUTPUT_ID
        self.REAL_MIC_ID = REAL_MIC_ID
        self.REAL_SPEAKER_ID = REAL_SPEAKER_ID

        self.is_running = False
        self.is_injecting_audio = False 
        self.is_muted = False 
        self.es_to_en = True 
        self.chat_history = [] 

        self.user_volume = 0
        self.other_volume = 0

        # --- INTERFAZ ---
        self.title("TraslSpeak ProMAX V13 - Final Edition") 
        self.geometry("1100x850")
        self.configure(fg_color="#D9F2FF") 

        self.label_title = ctk.CTkLabel(self, text="🗣️ TraslSpeak ProMAX", 
                                         font=("Arial Bold", 28), text_color="#006699")
        self.label_title.pack(pady=(20, 10))
        
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # PANEL USUARIO
        self.frame_user = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="white", border_color="#00A8E8", border_width=3)
        self.frame_user.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.lbl_user_lang = ctk.CTkLabel(self.frame_user, text="👤 TÚ", font=("Arial Bold", 18), text_color="#006699")
        self.lbl_user_lang.pack(pady=(10, 5))
        self.vol_meter_user = ctk.CTkProgressBar(self.frame_user, width=250, height=8, progress_color="#00AA00")
        self.vol_meter_user.set(0); self.vol_meter_user.pack(pady=5)
        self.status_usuer = ctk.CTkLabel(self.frame_user, text="INACTIVO" , text_color="gray")
        self.status_usuer.pack(pady=5)
        self.txt_user = ctk.CTkTextbox(self.frame_user, font=("Segoe UI", 13), fg_color="#F0F8FF", corner_radius=15, wrap="word")
        self.txt_user.pack(fill="both", expand=True, padx=15, pady=15)
        self.txt_user.configure(state="disabled")

        # PANEL RECEPTOR
        self.frame_other = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="white", border_color="#00C2E0", border_width=3)
        self.frame_other.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.lbl_other_lang = ctk.CTkLabel(self.frame_other, text="🤖 RECEPTOR", font=("Arial Bold", 18), text_color="#008FB3")
        self.lbl_other_lang.pack(pady=(10, 5))
        self.vol_meter_other = ctk.CTkProgressBar(self.frame_other, width=250, height=8, progress_color="#00AAFF")
        self.vol_meter_other.set(0); self.vol_meter_other.pack(pady=5)
        self.status_other = ctk.CTkLabel(self.frame_other, text="ESPERANDO...", text_color="gray")
        self.status_other.pack(pady=5)
        self.txt_other = ctk.CTkTextbox(self.frame_other, font=("Segoe UI", 13), fg_color="#F0FFFF", corner_radius=15, wrap="word")
        self.txt_other.pack(fill="both", expand=True, padx=15, pady=15)
        self.txt_other.configure(state="disabled")

        # CONTROLES
        self.frame_controles = ctk.CTkFrame(self, height=80, fg_color="transparent")
        self.frame_controles.pack(fill="x", pady=20, padx=20, side="bottom")

        self.btn_switch_lang = ctk.CTkButton(self.frame_controles, text="🔄 Idioma", command=self.switch_languages, fg_color="#0099CC", height=40)
        self.btn_switch_lang.pack(side="left", padx=5)

        self.btn_mute = ctk.CTkButton(self.frame_controles, text="🎤 MUTE", command=self.toggle_mute, fg_color="#10B981", height=40)
        self.btn_mute.pack(side="left", padx=5)

        self.btn_report = ctk.CTkButton(self.frame_controles, text="📄 REPORTE", command=self.save_html_report, fg_color="#555555", height=40)
        self.btn_report.pack(side="left", padx=5)

        self.btn_accion = ctk.CTkButton(self.frame_controles, text="START", command=self.toggle_system, fg_color="#00C2E0", height=50, font=("Arial Bold", 18))
        self.btn_accion.pack(side="left", fill="x", expand=True, padx=10) 

        threading.Thread(target=self.load_model).start()
        self.update_vumeters_gui()

    # --- LÓGICA ---
    def update_vumeters_gui(self):
        if self.is_running:
            self.vol_meter_user.set(min((0 if self.is_muted else self.user_volume) / 4000, 1.0))
            self.vol_meter_other.set(min(self.other_volume / 4000, 1.0))
        self.after(50, self.update_vumeters_gui)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.btn_mute.configure(text="🔇 MUTED" if self.is_muted else "🎤 MUTE", fg_color="#EF4444" if self.is_muted else "#10B981")

    def switch_languages(self):
        if self.is_running: return
        self.es_to_en = not self.es_to_en
        u_name = "ESPAÑOL" if self.es_to_en else "INGLÉS"
        o_name = "INGLÉS" if self.es_to_en else "ESPAÑOL"
        self.lbl_user_lang.configure(text=f"👤 TÚ ({u_name})")
        self.lbl_other_lang.configure(text=f"🤖 RECEPTOR ({o_name})")

    def save_html_report(self):
        if not self.chat_history: 
             messagebox.showwarning("Vacío", "No hay historial para guardar.")
             return
        filename = f"Reporte_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html = f"<html><head><meta charset='utf-8'><style>body{{font-family:sans-serif;background:#f0f2f5;padding:20px;}}.msg{{margin:10px;padding:15px;border-radius:10px;}}.user{{background:#e3f2fd;border-left:5px solid #00A8E8;}}.other{{background:#f1f8e9;border-left:5px solid #00C2E0;}}</style></head><body><h2>📄 Reporte de Traducción</h2>"
        for m in self.chat_history:
            cl = "user" if m['side'] == "USER" else "other"
            html += f"<div class='msg {cl}'><b>{m['time']} - {m['side']}:</b><br>{m['orig']}<br><i>{m['trad']}</i></div>"
        html += "</body></html>"
        with open(filename, "w", encoding="utf-8") as f: f.write(html)
        os.startfile(filename)

    def load_model(self):
        self.model = WhisperModel("base", device="cpu", compute_type="int8")
        self.p = pyaudio.PyAudio()
        self.btn_accion.configure(state="normal", text="▶ START")

    def toggle_system(self):
        if not self.is_running:
            self.chat_history = []
            for box in [self.txt_user, self.txt_other]:
                box.configure(state="normal"); box.delete("1.0", "end"); box.configure(state="disabled")
            self.is_running = True
            self.btn_accion.configure(text="⏹ STOP", fg_color="#FF5E78")
            threading.Thread(target=self.thread_user_listener, daemon=True).start()
            threading.Thread(target=self.thread_zoom_listener, daemon=True).start()
        else:
            self.is_running = False
            self.btn_accion.configure(text="▶ START", fg_color="#00C2E0")
            self.save_html_report()

    # --- HILOS ---
    def thread_user_listener(self):
        CHUNK = 1024; RATE = 16000
        src, dest = ("es", "en") if self.es_to_en else ("en", "es")
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, input_device_index=self.REAL_MIC_ID, frames_per_buffer=CHUNK)
        frames = []; silence_start = None; is_speaking = False
        while self.is_running:
            if self.is_injecting_audio or self.is_muted: time.sleep(0.1); continue
            data = stream.read(CHUNK, exception_on_overflow=False)
            self.user_volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
            if self.user_volume > 500:
                is_speaking = True; silence_start = None; frames.append(data)
            elif is_speaking:
                frames.append(data)
                if silence_start is None: silence_start = time.time()
                if (time.time() - silence_start > 0.8): 
                    self.save_audio(frames, "temp_me.wav"); frames = []; is_speaking = False
                    text = self.transcribe_audio(src, "temp_me.wav")
                    if text:
                        trans = self.translate_text(text, src, dest)
                        self.display_msg("USER", text, trans, src, dest)
                        self.speak_dual(trans, dest) 
        stream.stop_stream(); stream.close()

    def thread_zoom_listener(self):
        CHUNK = 1024; RATE = 16000
        src, dest = ("en", "es") if self.es_to_en else ("es", "en")
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, input_device_index=self.CABLE_OUTPUT_ID, frames_per_buffer=CHUNK)
        frames = []; silence_start = None; is_speaking = False
        while self.is_running:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if self.is_injecting_audio: self.other_volume = 0; frames = []; is_speaking = False; continue
            self.other_volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
            if self.other_volume > 300: 
                is_speaking = True; silence_start = None; frames.append(data)
            elif is_speaking:
                frames.append(data)
                if silence_start is None: silence_start = time.time()
                if (time.time() - silence_start > 0.8):
                    self.save_audio(frames, "temp_zoom.wav"); frames = []; is_speaking = False
                    text = self.transcribe_audio(src, "temp_zoom.wav")
                    if text:
                        trans = self.translate_text(text, src, dest)
                        self.display_msg("OTHER", text, trans, src, dest)
                        self.speak_neural(trans, dest, self.REAL_SPEAKER_ID, "v_speaker.mp3")
        stream.stop_stream(); stream.close()

    # --- AUDIO DUAL ---
    def speak_dual(self, text, lang):
        self.is_injecting_audio = True
        voice = NEURAL_VOICES.get(lang, "en-US-ChristopherNeural")
        filename = "dual.mp3"
        try:
            asyncio.run(self._generate_audio(text, voice, filename))
            data, fs = sf.read(filename, dtype='float32')
            sd.play(data, fs, device=self.CABLE_INPUT_ID) # Amigo
            sd.play(data, fs, device=self.REAL_SPEAKER_ID) # Tú
            sd.wait()
        except: pass
        self.is_injecting_audio = False

    def speak_neural(self, text, lang, device_id, filename):
        self.is_injecting_audio = True
        voice = NEURAL_VOICES.get(lang, "en-US-ChristopherNeural")
        try:
            asyncio.run(self._generate_audio(text, voice, filename))
            data, fs = sf.read(filename, dtype='float32')
            sd.play(data, fs, device=device_id); sd.wait()
        except: pass
        self.is_injecting_audio = False 

    async def _generate_audio(self, text, voice, filename):
        communicate = edge_tts.Communicate(text, voice, rate="+5%"); await communicate.save(filename)

    def transcribe_audio(self, lang, file):
        try:
            segments, _ = self.model.transcribe(file, language=lang)
            return "".join([s.text for s in segments]).strip()
        except: return ""

    def translate_text(self, text, src, dest):
        try: return GoogleTranslator(source=src, target=dest).translate(text)
        except: return text

    def save_audio(self, frames, filename):
        import wave
        wf = wave.open(filename, 'wb'); wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
        wf.writeframes(b''.join(frames)); wf.close()

    def display_msg(self, side, orig, trad, src, dest):
        box = self.txt_user if side == "USER" else self.txt_other
        box.configure(state="normal")
        box.insert("end", f"[{src.upper()}]: {orig}\n", "bold")
        box.insert("end", f"➔ [{dest.upper()}]: {trad}\n\n", "italic")
        box.see("end"); box.configure(state="disabled")
        self.chat_history.append({'side': side, 'orig': orig, 'trad': trad, 'time': datetime.datetime.now().strftime('%H:%M:%S')})

    def update_label(self, label, text, color):
        self.after(0, lambda: label.configure(text=text, text_color=color))

if __name__ == "__main__":
    app = HandsFreeApp()
    app.mainloop()