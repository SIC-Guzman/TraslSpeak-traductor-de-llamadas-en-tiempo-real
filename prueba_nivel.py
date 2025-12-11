import pyaudio
import numpy as np
import time

def barra_volumen():
    p = pyaudio.PyAudio()
    
    print("\n--- BUSCANDO DISPOSITIVOS DE AUDIO ---")
    info_devs = []
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0: # Es un micrófono/entrada
            print(f"ID {i}: {dev['name']}")
            info_devs.append(i)
            
    print("--------------------------------------")
    try:
        id_elegido = int(input("Escribe el ID (número) del 'CABLE Output': "))
    except:
        print("Número inválido")
        return

    print(f"\n🎧 ESCUCHANDO ID {id_elegido}... (Presiona Ctrl+C para salir)")
    print("Si no ves barras moviéndose, NO está llegando audio.\n")

    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        input_device_index=id_elegido,
                        frames_per_buffer=1024)

        while True:
            data = stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            # Calculamos el volumen pico
            peak = np.abs(audio_data).max()
            
            # Dibujamos una barra
            barras = "|" * int(peak / 300) 
            if peak > 500:
                print(f"Detectando: {barras}")
            else:
                # Imprimimos punto para saber que corre pero hay silencio
                print(".", end="", flush=True)
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nDetenido.")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        p.terminate()

if __name__ == "__main__":
    barra_volumen()