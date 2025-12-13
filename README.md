
# 🚀 TraslPeaker: Traductor de llamadas en tiempo real 

## 🌟 Nuestra visión

**TraslPeak** es un traductor de voz en tiempo real diseñado para operar de manera completamente automática, dentro de plataformas de videollamadas (Zoom, Meet, Teams, WhatsApp, etc). Utiliza redes neuronales locales (`FasterWhisper`) y la API de traducción de Google para ofrecer una comunicación fluida, separando la voz del usuario del audio de la llamada mediante cables virtuales.

-----

## 🛠️ ¿Qué herramientas fueron Utilizadas?

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Núcleo de Voz/STT** | `FasterWhisper` | Transcripción ultrarrápida (Speech-to-Text) con modelos locales (CPU). |
| **Traducción** | `deep_translator` | Utiliza el motor de Google Translate para la traducción de texto. |
| **TTS (Voz)** | `gTTS` / `sounddevice` | Generación de la voz traducida y reproducción en el dispositivo de audio correcto. |
| **Audio I/O** | `PyAudio`, `sounddevice` | Manejo del micrófono y control de los dispositivos de audio virtuales. |
| **Cables Virtuales** | **VB-CABLE** | Sistema esencial para inyectar y capturar audio desde y hacia la videollamada. |
| **Interfaz (GUI)** | `CustomTkinter` | Interfaz gráfica de usuario moderna, limpia y agradable a la vista. |

-----

## 💻 Requisitos e Instalación

### Requisitos del Sistema

  * **Python:** Versión 3.9 o superior.
  * **Audio Virtual (CRÍTICO):**
      * **Windows:** Instalar [VB-Audio Virtual Cable](https://vb-audio.com/Cable/index.htm).
      * **macOS:** Instalar [VB-Audio Virtual Cable](https://vb-audio.com/Cable/index.htm)

### Instalación de Librerías

Ejecuta el siguiente comando para instalar todas las dependencias necesarias:

```bash
pip install customtkinter pyaudio numpy faster-whisper gtts deep-translator sounddevice soundfile
```
-----

## ⚙️ Configuración y Uso

Para un funcionamiento bidireccional fluido, es necesario un **Cruce de Cables Virtuales**.

### 1\. Ajuste de Archivo `app.py`

Si usas **Windows**, verifica que los IDs de los cables en la sección de configuración de tu `app.py` sean los correctos, ya que estos IDs varían en cada PC.

  * `CABLE_INPUT_ID_WIN`: ID del **CABLE Input** (Salida de la App, escucha Zoom).
  * `CABLE_OUTPUT_ID_WIN`: ID del **CABLE Output** (Entrada de la App, escucha Zoom).

### 2\. Configuración de la Videollamada

Esta configuración es **CRUCIAL** y debe hacerse antes de iniciar la llamada.

| Dispositivo de Zoom/Meet | Dispositivo Seleccionado | Propósito |
| :--- | :--- | :--- |
| **Micrófono (Input)** | **VB-CABLE Output** | Zoom escucha la traducción inyectada por la App. |
| **Altavoz (Output)** | **VB-CABLE Input** | Envía el audio de la llamada al cable, permitiendo que la App lo "escuche" para traducirlo. |

### 3\. Ejecución

Ejecuta la aplicación desde la terminal:

```bash
python app.py
```

Una vez iniciada la aplicación:

1.  Haz clic en **"▶ START"**.
2.  **Si tú hablas (ES):** La App te escucha, traduce y **habla en EN por el cable** a la persona en Zoom.
3.  **Si ellos hablan (EN):** La App escucha el audio del cable, traduce y **habla en ES por tus Audífonos Reales**.

-----

## 🧑‍💻 El Equipo de Desarrollo

Este proyecto fue desarrollado por el siguiente equipo:

| Nombre | Rol Principal |
| :--- | :--- |
| **José Osorio** | Arquitectura del Sistema |
| **Guillermo Marroquin** | Desarrollo de Hilos y Lógica de Audio |
| **Jhossua García** | Implementación de Interfaces (GUI) |
| **Axel Aguilar** | Integración de Modelos de IA (Whisper) |

-----

## Licencia

Este proyecto está liberado bajo la licencia MIT.
