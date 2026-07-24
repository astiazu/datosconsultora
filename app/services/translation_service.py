# app/services/translation_service.py
import os
from groq import Groq


class TranslationService:
    """Servicio de traducción usando Groq LLM."""

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
        self.model = model

    def traducir(self, texto: str, idioma_origen: str = "en", idioma_destino: str = "es") -> str:
        """
        Traduce un texto de un idioma a otro.
        
        :param texto: Texto a traducir
        :param idioma_origen: Idioma de origen (ej: 'en', 'es')
        :param idioma_destino: Idioma de destino (ej: 'es', 'en')
        :return: Texto traducido
        """
        if not texto or not texto.strip():
            return ""

        if idioma_origen == idioma_destino:
            return texto

        nombres_idiomas = {
            "es": "español",
            "en": "inglés",
            "pt": "portugués",
            "fr": "francés",
            "it": "italiano",
            "de": "alemán",
        }

        origen = nombres_idiomas.get(idioma_origen, idioma_origen)
        destino = nombres_idiomas.get(idioma_destino, idioma_destino)

        prompt = f"""Traducí el siguiente texto de {origen} a {destino}. 
        Mantené el formato, los párrafos y el tono del original. 
        Respondé SOLO con la traducción, sin agregar nada más.

        TEXTO A TRADUCIR:
        {texto}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Sos un traductor profesional de {origen} a {destino}. Traducís de forma natural y precisa. Respondés SOLO con la traducción."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Error traduciendo: {str(e)}")

    def get_name(self) -> str:
        return f"Groq LLM ({self.model})"
