from transformers import MarianMTModel, MarianTokenizer

class Traductor:
    def __init__(self, origen="es", destino="en"):
        print(f"--- Cargando traductor {origen} -> {destino} ---")
        # Nombre del modelo en Hugging Face
        self.nombre_modelo = f"Helsinki-NLP/opus-mt-{origen}-{destino}"
        
        # Cargar el tokenizador y el modelo
        self.tokenizer = MarianTokenizer.from_pretrained(self.nombre_modelo)
        self.model = MarianMTModel.from_pretrained(self.nombre_modelo)
        print("--- Traductor cargado exitosamente ---")

    def traducir(self, texto):
        if not texto: return ""
        try:
            # 1. Preparar texto (Tokenizar)
            inputs = self.tokenizer(texto, return_tensors="pt", padding=True)
            
            # 2. Generar traducción (Inferencia)
            translated = self.model.generate(**inputs)
            
            # 3. Convertir números a texto (Decodificar)
            texto_traducido = self.tokenizer.decode(translated[0], skip_special_tokens=True)
            
            return texto_traducido
        except Exception as e:
            return f"Error traducción: {e}"