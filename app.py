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
from tkinter import messagebox 

# --- CONFIGURACIÓN DE AUDIO ---
CABLE_INPUT_ID = 4      
CABLE_OUTPUT_ID = 2     
REAL_MIC_ID = 1         
REAL_SPEAKER_ID = 5     

LANG_MAP = {
    "Español": {"code": "es", "voices": {"Femenino": "es-MX-DaliaNeural", "Masculino": "es-MX-JorgeNeural"}},
    "Inglés": {"code": "en", "voices": {"Femenino": "en-US-EmmaNeural", "Masculino": "en-US-ChristopherNeural"}},
    "Francés": {"code": "fr", "voices": {"Femenino": "fr-FR-EloiseNeural", "Masculino": "fr-FR-RemyNeural"}},
    "Alemán": {"code": "de", "voices": {"Femenino": "de-DE-KatjaNeural", "Masculino": "de-DE-KillianNeural"}},
    "Italiano": {"code": "it", "voices": {"Femenino": "it-IT-ElsaNeural", "Masculino": "it-IT-DiegoNeural"}},
    "Portugués": {"code": "pt", "voices": {"Femenino": "pt-BR-FranciscaNeural", "Masculino": "pt-BR-AntonioNeural"}},
    "Japonés": {"code": "ja", "voices": {"Femenino": "ja-JP-NanamiNeural", "Masculino": "ja-JP-KeitaNeural"}}
}

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class HandsFreeApp(ctk.CTk):
    def __init__(self):
        # 1. INICIALIZAR AUDIO PRIMERO (Evita errores de hilos)
        try:
            self.p = pyaudio.PyAudio()
        except Exception as e:
            print(f"Error PyAudio: {e}")

        super().__init__()
        
        self.CABLE_INPUT_ID = CABLE_INPUT_ID
        self.CABLE_OUTPUT_ID = CABLE_OUTPUT_ID
        self.REAL_MIC_ID = REAL_MIC_ID
        self.REAL_SPEAKER_ID = REAL_SPEAKER_ID

        self.is_running = False
        self.is_injecting_audio = False 
        self.is_muted = False 
        self.chat_history = [] 
        self.user_volume = 0
        self.other_volume = 0

        self.title("TraslSpeak Pro") 
        self.geometry("1200x950")
        self.configure(fg_color="#D9F2FF") 

        self.label_title = ctk.CTkLabel(self, text="🗣️ TraslSpeak Pro", font=("Arial Bold", 32), text_color="#006699")
        self.label_title.pack(pady=(15, 5))
        
        self.frame_voice_style = ctk.CTkFrame(self, fg_color="white", corner_radius=15, border_color="#006699", border_width=1)
        self.frame_voice_style.pack(fill="x", padx=300, pady=5)
        ctk.CTkLabel(self.frame_voice_style, text="GÉNERO DE LAS VOCES:", font=("Arial Bold", 13)).pack(side="left", padx=20, pady=10)
        self.gender_global = ctk.CTkOptionMenu(self.frame_voice_style, values=["Masculino", "Femenino"], fg_color="#555555", width=150)
        self.gender_global.set("Masculino"); self.gender_global.pack(side="right", padx=20, pady=10)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=5)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # PANEL TÚ
        self.frame_user = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="white", border_color="#00A8E8", border_width=3)
        self.frame_user.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.frame_user, text="MI IDIOMA:", font=("Arial Bold", 16)).pack(pady=(10,5))
        self.combo_user = ctk.CTkOptionMenu(self.frame_user, values=list(LANG_MAP.keys()), command=self.sync_languages_user, width=200)
        self.combo_user.set("Español"); self.combo_user.pack(pady=5)
        self.vol_meter_user = ctk.CTkProgressBar(self.frame_user, width=300, height=10); self.vol_meter_user.pack(pady=10)
        self.status_usuer = ctk.CTkLabel(self.frame_user, text="CARGANDO TURBO...", font=("Arial Bold", 14), text_color="gray"); self.status_usuer.pack()
        self.txt_user = ctk.CTkTextbox(self.frame_user, font=("Segoe UI", 15), fg_color="#F0F8FF", corner_radius=15, wrap="word", state="disabled")
        self.txt_user.pack(fill="both", expand=True, padx=15, pady=15)

        # PANEL RECEPTOR
        self.frame_other = ctk.CTkFrame(self.main_container, corner_radius=20, fg_color="white", border_color="#00C2E0", border_width=3)
        self.frame_other.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(self.frame_other, text="SU IDIOMA:", font=("Arial Bold", 16)).pack(pady=(10,5))
        self.combo_other = ctk.CTkOptionMenu(self.frame_other, values=list(LANG_MAP.keys()), command=self.sync_languages_other, width=200)
        self.combo_other.set("Inglés"); self.combo_other.pack(pady=5)
        self.vol_meter_other = ctk.CTkProgressBar(self.frame_other, width=300, height=10); self.vol_meter_other.pack(pady=10)
        self.status_other = ctk.CTkLabel(self.frame_other, text="ESPERANDO...", font=("Arial Bold", 14), text_color="gray"); self.status_other.pack()
        self.txt_other = ctk.CTkTextbox(self.frame_other, font=("Segoe UI", 15), fg_color="#F0FFFF", corner_radius=15, wrap="word", state="disabled")
        self.txt_other.pack(fill="both", expand=True, padx=15, pady=15)

        self.frame_controles = ctk.CTkFrame(self, height=80, fg_color="transparent")
        self.frame_controles.pack(fill="x", pady=15, padx=40, side="bottom")
        self.btn_mute = ctk.CTkButton(self.frame_controles, text="🎤 MUTE", command=self.toggle_mute, fg_color="#10B981", height=45)
        self.btn_mute.pack(side="left", padx=10)
        self.btn_report = ctk.CTkButton(self.frame_controles, text="📄 REPORTE HTML", command=self.save_html_report, fg_color="#555555", height=45)
        self.btn_report.pack(side="left", padx=10)
        self.btn_accion = ctk.CTkButton(self.frame_controles, text="▶ START SYSTEM", command=self.toggle_system, fg_color="#00C2E0", height=55, font=("Arial Bold", 20))
        self.btn_accion.pack(side="left", fill="x", expand=True, padx=10) 

        self.prev_user_lang = "Español"
        self.prev_other_lang = "Inglés"

        threading.Thread(target=self.load_model, daemon=True).start()
        self.update_vumeters_gui()

    def sync_languages_user(self, current_val):
        if current_val == self.combo_other.get(): self.combo_other.set(self.prev_user_lang)
        self.prev_user_lang = current_val

    def sync_languages_other(self, current_val):
        if current_val == self.combo_user.get(): self.combo_user.set(self.prev_other_lang)
        self.prev_other_lang = current_val

    def load_model(self):
        # CARGA DEL MODELO TURBO (El más preciso y veloz)
        self.model = WhisperModel("turbo", device="cpu", compute_type="int8")
        self.btn_accion.configure(state="normal")
        self.update_label(self.status_usuer, "LISTO ✅", "#00AA00")

    def toggle_system(self):
        if not self.is_running:
            self.chat_history = []
            for box in [self.txt_user, self.txt_other]:
                box.configure(state="normal"); box.delete("1.0", "end"); box.configure(state="disabled")
            self.is_running = True
            self.btn_accion.configure(text="⏹ STOP SYSTEM", fg_color="#FF5E78")
            threading.Thread(target=self.thread_user_listener, daemon=True).start()
            threading.Thread(target=self.thread_zoom_listener, daemon=True).start()
        else:
            self.is_running = False
            self.btn_accion.configure(text="▶ START SYSTEM", fg_color="#00C2E0")
            self.save_html_report()

    def thread_user_listener(self):
        if not hasattr(self, 'p'): return
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.REAL_MIC_ID, frames_per_buffer=1024)
        frames = []; is_speaking = False; silence_start = None
        while self.is_running:
            if self.is_injecting_audio or self.is_muted: self.user_volume = 0; time.sleep(0.1); continue
            try:
                data = stream.read(1024, exception_on_overflow=False)
                self.user_volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                if self.user_volume > 350:
                    if not is_speaking: self.update_label(self.status_usuer, "ESCUCHANDO...", "#FF9900")
                    is_speaking = True; silence_start = None; frames.append(data)
                elif is_speaking:
                    frames.append(data)
                    if silence_start is None: silence_start = time.time()
                    if (time.time() - silence_start > 1.3): # Reducido a 1.3 para mayor velocidad
                        self.update_label(self.status_usuer, "TRADUCIENDO...", "#FF4400")
                        gender = self.gender_global.get()
                        lang_name = self.combo_other.get()
                        dest_voice = LANG_MAP[lang_name]["voices"][gender]
                        src_code = LANG_MAP[self.combo_user.get()]["code"]
                        dest_code = LANG_MAP[lang_name]["code"]
                        self.save_audio(frames, "u.wav", 16000); frames = []; is_speaking = False
                        
                        text = self.transcribe_audio(src_code, "u.wav")
                        if text:
                            trans = self.translate_text(text, src_code, dest_code)
                            self.display_msg("USER", text, trans, src_code, dest_code)
                            self.speak_neural(trans, dest_voice, self.CABLE_INPUT_ID, "d.mp3") 
                        self.update_label(self.status_usuer, "ESCUCHANDO...", "#00AA00")
            except: break
        stream.stop_stream(); stream.close()

    def thread_zoom_listener(self):
        if not hasattr(self, 'p'): return
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=self.CABLE_OUTPUT_ID, frames_per_buffer=1024)
        frames = []; is_speaking = False; silence_start = None
        while self.is_running:
            try:
                data = stream.read(1024, exception_on_overflow=False)
                if self.is_injecting_audio: self.other_volume = 0; continue
                self.other_volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                if self.other_volume > 300: 
                    if not is_speaking: self.update_label(self.status_other, "RECIBIENDO...", "#FF9900")
                    is_speaking = True; silence_start = None; frames.append(data)
                elif is_speaking:
                    frames.append(data)
                    if silence_start is None: silence_start = time.time()
                    if (time.time() - silence_start > 1.3):
                        self.update_label(self.status_other, "TRADUCIENDO...", "#FF4400")
                        gender = self.gender_global.get()
                        lang_name = self.combo_user.get()
                        my_voice = LANG_MAP[lang_name]["voices"][gender]
                        src_code = LANG_MAP[self.combo_other.get()]["code"]
                        dest_code = LANG_MAP[lang_name]["code"]
                        self.save_audio(frames, "z.wav", 16000); frames = []; is_speaking = False
                        text = self.transcribe_audio(src_code, "z.wav")
                        if text:
                            trans = self.translate_text(text, src_code, dest_code)
                            self.display_msg("OTHER", text, trans, src_code, dest_code)
                            self.speak_neural(trans, my_voice, self.REAL_SPEAKER_ID, "v.mp3")
                        self.update_label(self.status_other, "ESPERANDO...", "gray")
            except: break
        stream.stop_stream(); stream.close()

    def speak_neural(self, text, voice, device_id, filename):
        self.is_injecting_audio = True
        try:
            asyncio.run(edge_tts.Communicate(text, voice, rate="+5%").save(filename))
            data, fs = sf.read(filename, dtype='float32')
            sd.play(data, fs, device=device_id); sd.wait()
        except: pass
        self.is_injecting_audio = False 

    def transcribe_audio(self, lang, file):
        try:
            # Optimización Turbo: beam_size=1 es suficiente y mucho más rápido
            segments, _ = self.model.transcribe(file, language=lang, beam_size=1)
            return "".join([s.text for s in segments]).strip()
        except: return ""

    def translate_text(self, text, src, dest):
        try: return GoogleTranslator(source=src, target=dest).translate(text)
        except: return text

    def save_audio(self, frames, filename, rate):
        import wave
        wf = wave.open(filename, 'wb'); wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(b''.join(frames)); wf.close()

    def display_msg(self, side, orig, trad, src, dest):
        box = self.txt_user if side == "USER" else self.txt_other
        box.configure(state="normal")
        tag_o = f"[{src.upper()}]: "; tag_t = f"➔ [{dest.upper()}]: "
        box.insert("end", tag_o, "bold"); box.insert("end", orig + "\n")
        box.insert("end", tag_t, "italic"); box.insert("end", trad + "\n\n")
        box.see("end"); box.configure(state="disabled")
        self.chat_history.append({'side': side, 'orig': orig, 'trad': trad, 'time': datetime.datetime.now().strftime('%H:%M:%S')})

    def save_html_report(self):
        if not self.chat_history: return
        filename = f"Reporte_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html = f"<html><head><meta charset='utf-8'><style>body{{font-family:'Segoe UI',sans-serif;background-color:#f4f7f9;padding:30px;}}.container{{max-width:800px;margin:auto;background:white;padding:20px;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1);}}h2{{color:#006699;text-align:center;border-bottom:2px solid #D9F2FF;padding-bottom:10px;}}.msg{{margin:15px 0;padding:15px;border-radius:12px;line-height:1.5;}}.user{{background:#e3f2fd;border-left:5px solid #00A8E8;}}.other{{background:#f1f8e9;border-left:5px solid #8bc34a;}}.orig{{font-weight:bold;}}.trad{{font-style:italic;color:#555;}}</style></head><body><div class='container'><h2>📄 TraslSpeak ProMAX</h2>"
        for m in self.chat_history:
            cl = "user" if m['side'] == "USER" else "other"
            html += f"<div class='msg {cl}'><b>[{m['time']}] {m['side']}</b><br><div class='orig'>{m['orig']}</div><div class='trad'>{m['trad']}</div></div>"
        html += "</div></body></html>"
        with open(filename, "w", encoding="utf-8") as f: f.write(html)
        os.startfile(filename)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.btn_mute.configure(text="🔇 SILENCIADO" if self.is_muted else "🎤 MUTE", fg_color="#EF4444" if self.is_muted else "#10B981")

    def update_vumeters_gui(self):
        if self.is_running:
            self.vol_meter_user.set(min((0 if self.is_muted else self.user_volume) / 4000, 1.0))
            self.vol_meter_other.set(min(self.other_volume / 4000, 1.0))
        self.after(50, self.update_vumeters_gui)

    def update_label(self, label, text, color):
        self.after(0, lambda: label.configure(text=text, text_color=color))

if __name__ == "__main__":
    app = HandsFreeApp()
    app.mainloop()