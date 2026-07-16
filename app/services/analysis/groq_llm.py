# app/services/analysis/groq_llm.py
import os
import json
import re
from groq import Groq


class GroqLLMClient:
    """Cliente para análisis de texto con modelos LLM de Groq."""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def _extraer_json(self, texto: str) -> dict:
        """
        Extrae JSON de una respuesta del LLM de forma robusta.
        Intenta múltiples estrategias si el JSON está malformado.
        """
        # Limpiar markdown code blocks
        texto = texto.strip()
        if texto.startswith("```"):
            # Extraer contenido entre ```
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', texto, re.DOTALL)
            if match:
                texto = match.group(1).strip()
        
        # Intento 1: Parseo directo
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            pass
        
        # Intento 2: Buscar el primer { y el último }
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Intento 3: Reparar strings unterminados (problema común)
        # Buscar strings con comillas sin cerrar
        texto_reparado = texto
        # Reemplazar comillas problemáticas dentro de strings
        texto_reparado = re.sub(r'(?<=")[^"\n]*"(?=[,\s\]\}])', lambda m: m.group(0).replace('"', '\\"'), texto_reparado)
        
        try:
            return json.loads(texto_reparado)
        except json.JSONDecodeError:
            pass
        
        # Intento 4: Si todo falla, devolver estructura básica con el texto crudo
        raise ValueError(f"No se pudo extraer JSON válido. Respuesta recibida (primeros 500 chars): {texto[:500]}")
    
    def analizar_sentimientos(self, comentarios: list, contexto: str = "") -> dict:
        """
        Analiza sentimientos de una lista de comentarios.
        
        :param comentarios: Lista de strings con los comentarios (ya limpios)
        :param contexto: Contexto opcional del análisis
        :return: Dict con análisis detallado
        """
        # Validar cantidad
        if len(comentarios) > 100:
            raise ValueError(f"Máximo 100 comentarios por análisis. Recibiste {len(comentarios)}.")
        
        comentarios_texto = "\n".join([f"{i+1}. {c}" for i, c in enumerate(comentarios)])
        
        contexto_texto = f"\nCONTEXTO: {contexto}" if contexto else ""
        
        prompt = f"""Eres un analista experto en sentimientos de redes sociales en español.

Analizá los siguientes {len(comentarios)} comentarios y devolvé SOLO un JSON válido (sin markdown, sin texto adicional) con esta estructura EXACTA:

{{
  "analisis_individual": [
    {{"numero": 1, "sentimiento": "positivo|neutral|negativo", "confianza": 0.95, "resumen_corto": "frase corta de máximo 10 palabras"}}
  ],
  "resumen_general": "párrafo de 2-3 oraciones con el panorama general",
  "estadisticas": {{
    "total": {len(comentarios)},
    "positivos": 0,
    "neutrales": 0,
    "negativos": 0,
    "porcentaje_positivo": 0,
    "porcentaje_neutral": 0,
    "porcentaje_negativo": 0
  }},
  "temas_principales": ["tema1", "tema2", "tema3"],
  "palabras_clave": ["palabra1", "palabra2", "palabra3"],
  "tono_general": "descripción breve del tono predominante",
  "insights": ["insight1", "insight2", "insight3"],
  "recomendaciones": ["recomendacion1", "recomendacion2"]
}}

REGLAS IMPORTANTES:
- Respondé SOLO con el JSON, sin texto antes ni después
- No uses markdown (ni ```json ni ```)
- Escapá correctamente las comillas dentro de strings
- Los strings NO deben contener saltos de línea
- La suma de positivos + neutrales + negativos debe ser igual a "total"
- Los porcentajes deben sumar 100{contexto_texto}

COMENTARIOS A ANALIZAR:
{comentarios_texto}"""
        
        # Retry con backoff si falla el parsing
        max_intentos = 3
        ultimo_error = None
        
        for intento in range(max_intentos):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "Sos un analista experto en sentimientos de redes sociales. Respondés SIEMPRE con JSON válido y en español argentino. NUNCA incluyas texto fuera del JSON. NUNCA uses markdown."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2 if intento == 0 else 0.1,  # Más determinístico en retries
                    max_tokens=3000,  # Aumentado para respuestas largas
                )
                
                contenido = response.choices[0].message.content.strip()
                resultado = self._extraer_json(contenido)
                
                # Validar estructura básica
                if "estadisticas" not in resultado or "analisis_individual" not in resultado:
                    raise ValueError("Faltan campos requeridos en la respuesta")
                
                return resultado
                
            except (json.JSONDecodeError, ValueError) as e:
                ultimo_error = e
                print(f"⚠️ Intento {intento + 1}/{max_intentos} falló: {str(e)[:100]}")
                continue
            except Exception as e:
                raise Exception(f"Error en análisis de sentimientos: {str(e)}")
        
        raise Exception(f"Error parseando respuesta del modelo después de {max_intentos} intentos: {str(ultimo_error)}")
    
    def generar_resumen(self, texto: str, contexto: str = "") -> str:
        """Genera un resumen de un texto dado."""
        prompt = f"""Resumí el siguiente texto de forma clara y concisa en 3-5 oraciones.
{f'Contexto: {contexto}' if contexto else ''}

TEXTO:
{texto}

Respondé solo con el resumen, sin texto adicional."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Sos un experto en síntesis de textos. Respondés en español."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Error generando resumen: {str(e)}")
    
    def get_name(self) -> str:
        return f"Groq LLM ({self.model})"