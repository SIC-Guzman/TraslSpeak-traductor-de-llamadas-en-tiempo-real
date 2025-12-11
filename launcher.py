import os
import sys
import subprocess
import ctypes
import urllib.request
import zipfile
import time

# Nombre de tu archivo principal
MAIN_PROGRAM = "Opp_main.py"

def es_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_vb_cable_instalado():
    """
    Verifica si existe la carpeta de instalación por defecto de VB-CABLE.
    Es una forma rápida de saber si ya está instalado sin tocar el registro.
    """
    rutas_comunes = [
        r"C:\Program Files\VB\CABLE",
        r"C:\Program Files (x86)\VB\CABLE"
    ]
    for ruta in rutas_comunes:
        if os.path.exists(ruta):
            return True
    return False

def instalar_driver():
    print("-------------------------------------------------")
    print("⚠️  VB-CABLE NO DETECTADO. INICIANDO INSTALACIÓN...")
    print("-------------------------------------------------")

    # Verificar permisos de administrador
    if not es_admin():
        print("Solicitando permisos de administrador para instalar el driver...")
        # Relanzar este mismo script como administrador
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit() # Cerramos esta instancia para que corra la del admin

    print("1. Descargando VB-CABLE (Driver)...")
    try:
        url = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip"
        zip_path = "vbcable_temp.zip"
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print(f"Error descargando: {e}")
        return False

    print("2. Descomprimiendo archivos...")
    try:
        if not os.path.exists("vbcable_install"):
            os.makedirs("vbcable_install")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("vbcable_install")
    except Exception as e:
        print(f"Error descomprimiendo: {e}")
        return False

    print("3. Ejecutando Instalador de Windows...")
    # Detectar si es sistema de 64 bits para usar el instalador correcto
    installer_name = "VBCABLE_Setup_x64.exe" if sys.maxsize > 2**32 else "VBCABLE_Setup.exe"
    installer_path = os.path.abspath(f"vbcable_install/{installer_name}")

    if os.path.exists(installer_path):
        # Ejecutamos el instalador. 
        # NOTA: Windows pedirá confirmación visual.
        subprocess.run([installer_path], shell=True)
        print("✅ Instalación del driver finalizada.")
        
        # Limpieza de archivos temporales (Opcional)
        try:
            os.remove(zip_path)
            # shutil.rmtree("vbcable_install") # Requiere import shutil
        except:
            pass
        
        return True
    else:
        print("❌ No se encontró el ejecutable del instalador.")
        return False

def iniciar_tralspeak():
    print("\n" + "="*40)
    print(f"🚀 INICIANDO {MAIN_PROGRAM}...")
    print("="*40 + "\n")
    
    # Ejecutamos el programa principal
    subprocess.run([sys.executable, MAIN_PROGRAM])

def main():
    # 1. Chequeo
    if check_vb_cable_instalado():
        print("✅ Driver de Audio Virtual detectado.")
        # 2. Si existe, vamos directo al programa
        iniciar_tralspeak()
    else:
        # 2. Si no existe, instalamos
        exito = instalar_driver()
        
        if exito:
            print("\n⚠️  IMPORTANTE: Acabas de instalar el driver.")
            print("    Para que funcione correctamente, RECOMENDAMOS REINICIAR LA PC.")
            print("    Sin embargo, intentaremos abrir el programa ahora.")
            print("    (Si no se escucha el audio, cierra, reinicia la PC y vuelve a abrir).")
            time.sleep(5) # Damos tiempo para leer
            iniciar_tralspeak()
        else:
            print("Hubo un problema instalando el driver.")
            input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()