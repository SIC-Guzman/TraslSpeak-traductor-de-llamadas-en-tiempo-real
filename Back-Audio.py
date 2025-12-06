import pyaudio
import numpy as np
import torch    
from faster_whisper import WhisperModel

#la parte de la configuracion del audio
MODEL_SIZE = "tiny"
COMPUTE_TYPE = "int8"
SAMPLE_RATE = 16000
CHUNK_SIZE = 512

print("Cargando modelo...")

#cargamos el modelo de silero, usadndo el repo oficial

vad_model, vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      trust_repo = True)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = vad_utils

#vamos a cargar el modelo de faster-whisper

Whipser_Mod = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)

#probamos el microfono
print("modelos cargados, iniciando audio...")

#ahora configuramos el microfono
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE)

BufferAudio = [] #aca guardamos la voz fragmentada
voz_Activa = False #para saber si hay voz activa o que esten hablando
silencio_cont = 0 #para asber cuando cortar la grabacion
Lapso_tiempo = 15 #tiempo de silencio para cortar la grabacion, que es medio segundo

#prueba, borrar despues
print("Iniciando transcripcion, hable ahora...")

try:
    while True:
        #primero leemos el audio del microfono
        data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        
        #lo comvertimos a floar32
        audio_float32 = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        audio_int16 = np.frombuffer(data, dtype=np.int16)   

        #ahora detectamos si hay voz en este fragmento
        tensor = torch.from_numpy(audio_float32)
        problab_voz = vad_model(tensor, sr = SAMPLE_RATE).item()

        #con esto verificamos si grabamos o no
        if problab_voz > 0.5:
            #si hay voz activa
            voz_Activa = True
            silencio_cont = 0
            BufferAudio.append(audio_float32)
            print("Voz detectada, grabando..." )
        elif voz_Activa:
            #si no hay voz pero ya habia voz activa
            #seguimos grabando un poco mas por si es una pausa corta
            BufferAudio.append(audio_float32)
            silencio_cont += 1
        
        #si el silencio es muy largo, cortamos la grabacion
        if silencio_cont > Lapso_tiempo:
            print("Silencio detectado, procesando transcripcion...")
            #unimos todo el audio grabado
            audio_completo = np.concatenate(BufferAudio)

            #whiper
            segmentos, info = Whipser_Mod.transcribe(audio_completo, beam_size=5, language="es")

            texto_final = ""
            #transcribimos con faster-whisper
            for segmento in segmentos:
                texto_final += segmento.text

            #resultado final
            print(f"\rTranscripcion: , {texto_final}\n")

            #resetamos para la siguiente frase
            BufferAudio = []
            voz_Activa = False
            silencio_cont = 0

except KeyboardInterrupt:
    print("Apagando...")
    stream.stop_stream()
    stream.close()
    p.terminate()
          