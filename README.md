🚀 TraslPeak Pro: Traductor Inteligente de Llamadas

🌟 Nuestra Visión
TraslPeak Pro es una solución avanzada de traducción de voz bidireccional en tiempo real. Está diseñado para integrarse perfectamente en plataformas de comunicación (Zoom, Meet, Teams, Discord) actuando como un intérprete invisible.

A diferencia de otros traductores, TraslPeak separa de forma inteligente tu voz del audio de la llamada, permitiendo que tú escuches la traducción de los demás y que ellos escuchen tu voz traducida de forma fluida y automática.

🛠️ Stack Tecnológico de Última Generación
Componente	Tecnología	Propósito
Motor de Inteligencia	FasterWhisper (Turbo)	El modelo más equilibrado: Precisión de nivel large-v3 con la velocidad de small.
Traducción Neuronal	Google Translate API	Traducción contextual precisa en milisegundos.
Voz Neural (TTS)	Edge-TTS	Voces humanas de alta fidelidad (Dalia, Jorge, Keita, etc.) con selección de género.
Gestión de Audio	PyAudio / SoundDevice	Captura y ruteo de señales de audio de baja latencia.
Interfaz de Usuario	CustomTkinter	GUI moderna con paneles de chat expandidos y medidores de volumen real.
Puente de Audio	VB-CABLE	Virtualización de hardware para inyectar audio en aplicaciones externas.
🚀 Características Principales v22
Modelo Turbo: Optimizado para procesar audio hasta 8 veces más rápido que los modelos estándar.

Cambio en Caliente: Cambia de idioma o género de voz mientras hablas, sin necesidad de detener el sistema.

Interfaz Ultra-Alargada: Paneles de chat que aprovechan el 100% de la altura de tu pantalla para leer conversaciones largas.

Seguridad de Edición: Bloqueo automático de las cajas de texto para evitar borrados accidentales durante la transcripción.

Vu-Meters Reales: Indicadores visuales de volumen para asegurar que tu micrófono y la llamada están siendo detectados.

💻 Instalación y Requisitos
1. Requisitos del Sistema

Python: 3.9 o superior.

Audio Virtual (OBLIGATORIO): Instalar VB-Audio Virtual Cable.

Configuración: El "CABLE Input" debe estar configurado como tu micrófono en Zoom/Discord.

2. Instalación de Dependencias

Ejecuta este comando en tu terminal:

Bash
pip install customtkinter pyaudio numpy faster-whisper edge-tts deep-translator sounddevice soundfile
⚙️ Configuración Crítica
Antes de iniciar, debes identificar los IDs de tus dispositivos de audio. Ejecuta un script de prueba de pyaudio y actualiza estas líneas en el código:

Python
# Busca los IDs exactos en tu panel de sonido de Windows
CABLE_INPUT_ID = 4      # ID del "CABLE Input (VB-Audio)"
CABLE_OUTPUT_ID = 2     # ID del "CABLE Output (VB-Audio)"
REAL_MIC_ID = 1         # ID de tu Micrófono Físico
REAL_SPEAKER_ID = 5     # ID de tus Altavoces/Auriculares reales
📖 Instrucciones de Uso
Lanzar App: Ejecuta python app.py. Espera a que el botón diga "TURBO LISTO ✅".

Configurar Llamada: En Zoom/Meet, selecciona CABLE Input como tu micrófono.

Seleccionar Idiomas: Elige tu idioma y el idioma de la otra persona.

Iniciar: Presiona START SYSTEM.

Comunicación fluida: Habla normalmente. El sistema detectará los silencios (1.3s) y lanzará la traducción automáticamente.

Posdata: Puedes cambiar el género de las voces en el selector central en cualquier momento; la siguiente frase ya saldrá con el nuevo género.
