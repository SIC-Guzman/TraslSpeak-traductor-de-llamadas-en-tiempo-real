import os
import shutil
import urllib.request
import zipfile
import ssl

def reparar_modelo_vad():
    # 1. Encontrar la ruta donde PyTorch guarda los modelos
    home_dir = os.path.expanduser('~')
    hub_dir = os.path.join(home_dir, ".cache", "torch", "hub")
    
    # Esta es la carpeta que suele dar problemas
    vad_dir = os.path.join(hub_dir, "snakers4_silero-vad_master")
    zip_target = os.path.join(hub_dir, "master.zip")

    print(f"📍 Buscando en: {hub_dir}")

    # 2. BORRAR CACHÉ CORRUPTA
    if os.path.exists(vad_dir):
        print("🗑️  Borrando carpeta corrupta anterior...")
        try:
            shutil.rmtree(vad_dir)
        except Exception as e:
            print(f"⚠️ No se pudo borrar la carpeta (quizás está abierta): {e}")
            return

    if os.path.exists(zip_target):
        try: os.remove(zip_target)
        except: pass

    # Crear directorio si no existe
    if not os.path.exists(hub_dir):
        os.makedirs(hub_dir)

    # 3. DESCARGAR MANUALMENTE (Bypasseando torch.hub)
    url = "https://github.com/snakers4/silero-vad/zipball/master"
    print("⬇️  Descargando modelo VAD manualmente (esto puede tardar)...")
    
    try:
        # Contexto SSL para evitar errores de certificado
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ctx, timeout=60) as response, open(zip_target, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("✅ Descarga completada.")
    except Exception as e:
        print(f"❌ Error descargando: {e}")
        return

    # 4. DESCOMPRIMIR Y RENOMBRAR
    print("📦 Descomprimiendo...")
    try:
        with zipfile.ZipFile(zip_target, 'r') as zip_ref:
            zip_ref.extractall(hub_dir)
            
            # El zip extrae una carpeta con nombre raro (ej: snakers4-silero-vad-84a2b2...)
            # Necesitamos renombrarla a lo que espera tu programa: 'snakers4_silero-vad_master'
            extracted_folders = [f for f in os.listdir(hub_dir) if "silero-vad" in f and f != "master.zip"]
            
            if extracted_folders:
                extracted_folder_path = os.path.join(hub_dir, extracted_folders[0])
                # Renombrar a la carpeta oficial
                os.rename(extracted_folder_path, vad_dir)
                print("✅ Carpeta configurada correctamente.")
            else:
                print("⚠️ Algo raro pasó: No se encontró la carpeta descomprimida.")

        # Limpiar el zip
        os.remove(zip_target)
        print("\n✨ ¡LISTO! El modelo ha sido reparado.")
        print("👉 Ahora intenta ejecutar Opp_main.py de nuevo.")

    except Exception as e:
        print(f"❌ Error al descomprimir: {e}")

if __name__ == "__main__":
    reparar_modelo_vad()