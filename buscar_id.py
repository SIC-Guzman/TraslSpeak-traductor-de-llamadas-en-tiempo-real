import pyaudio

p = pyaudio.PyAudio()

print("\n--- BUSCANDO DISPOSITIVOS ---")
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    # Buscamos algo que diga "CABLE Output" o similar
    if "CABLE Output" in dev['name'] or "VB-Audio" in dev['name']:
        print(f"ENCONTRADO -> ID: {i} | Nombre: {dev['name']}")
    else:
        # Imprimir todos por si acaso tiene otro nombre
        print(f"ID: {i} | {dev['name']}")


import sounddevice as sd
print(sd.query_devices())
p.terminate()