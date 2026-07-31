# app/services/analysis/groq_llm.py
import os
import json
import re
from groq import Groq
from app.services.analysis.token_monitor import TokenMonitor


class GroqLLMClient:
    """Cliente para análisis de texto con modelos LLM de Groq."""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.token_monitor = TokenMonitor.get_instance()
    
    def _extraer_json(self, texto: str) -> dict:
        """
        Extrae JSON de una respuesta del LLM de forma robusta.
        Maneja bloques de código markdown y JSON malformados.
        """
        texto = texto.strip()
        
        # Intento 1: Buscar y extraer bloque de código markdown (```json ... ```)
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', texto)
        if match:
            texto = match.group(1).strip()
        
        # Intento 2: Parseo directo del texto limpio
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            pass
        
        # Intento 3: Buscar el primer '{' y el último '}'
        match = re.search(r'\{[\s\S]*\}', texto)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Intento 4: Reparar comillas problemáticas dentro de strings
        texto_reparado = re.sub(r'(?<=")[^"\n]*"(?=[,\s\]\}])', lambda m: m.group(0).replace('"', '\\"'), texto)
        try:
            return json.loads(texto_reparado)
        except json.JSONDecodeError:
            pass
        
        raise ValueError(f"No se pudo extraer JSON válido. Respuesta recibida: {texto[:500]}")
    
    def analizar_sentimientos(self, comentarios: list, contexto: str = "") -> dict:
        """
        Analiza sentimientos de una lista de comentarios con mayor precisión.
        """
        if len(comentarios) > 100:
            raise ValueError(f"Máximo 100 comentarios por análisis. Recibiste {len(comentarios)}.")
        
        comentarios_texto = "\n".join([f"{i+1}. {c}" for i, c in enumerate(comentarios)])
        contexto_texto = f"\nCONTEXTO ESPECÍFICO: {contexto}" if contexto else "\nCONTEXTO ESPECÍFICO: Análisis general de redes sociales sin contexto adicional."
        
        prompt = f"""Sos un analista senior de datos y sentimientos en redes sociales, especializado en el mercado y la jerga argentina. Tu objetivo es proporcionar un análisis profundo, detectando no solo el sentimiento básico, sino también ironía, sarcasmo, quejas constructivas y matices.

Analizá los siguientes {len(comentarios)} comentarios y devolvé EXCLUSIVAMENTE un objeto JSON válido (sin markdown, sin texto antes o después, sin saltos de línea dentro de los strings) con esta estructura exacta:

{{
  "analisis_individual": [
    {{"numero": 1, "sentimiento": "positivo|neutral|negativo", "confianza": 0.95, "resumen_corto": "Explicación breve de POR QUÉ tiene ese sentimiento, detectando si hay ironía (máx 15 palabras)"}}
  ],
  "resumen_general": "Párrafo de 2-3 oraciones que sintetice el panorama general, mencionando si hay polarización, consenso o un sentimiento predominante.",
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
  "tono_general": "Descripción precisa del tono (ej: 'Mayormente sarcástico con toques de frustración', 'Entusiasta y colaborativo')",
  "insights": ["Insight accionable 1 basado en datos", "Insight accionable 2", "Insight accionable 3"],
  "recomendaciones": ["Recomendación estratégica 1", "Recomendación estratégica 2"]
}}

REGLAS ESTRICTAS DE ANÁLISIS:
1. SARCASMO E IRONÍA: Prestá mucha atención. Un "¡Qué genial!" en un contexto de queja es negativo. La jerga argentina (ej: "groso", "pésimo", "llayllora") debe interpretarse en su contexto cultural.
2. COMENTARIOS MIXTOS: Si un comentario tiene aspectos positivos y negativos, clasificá según el sentimiento que predomina o el que representa el mayor dolor/valor para el usuario.
3. CONTEXTO: Usá el "CONTEXTO ESPECÍFICO" provisto para desambiguar términos, nombres propios o situaciones del sector.
4. MATEMÁTICAS: La suma de positivos + neutrales + negativos DEBE ser exactamente igual a "total". Los porcentajes DEBEN sumar 100. Redondeá a números enteros.
5. FORMATO JSON: Respondé SOLO con el JSON. No uses ```json ni ```. Escapá correctamente las comillas dobles dentro de los strings. No uses saltos de línea (\n) dentro de los valores de texto.

{contexto_texto}

COMENTARIOS A ANALIZAR:
{comentarios_texto}"""
        
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
                    temperature=0.15 if intento == 0 else 0.05,
                    max_tokens=3500,
                )
                
                if hasattr(self, "token_monitor") and self.token_monitor is not None:
                    self.token_monitor.update_from_response(response)

                contenido = response.choices[0].message.content.strip()
                resultado = self._extraer_json(contenido)
                
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
    
    def analizar_semantica(
        self,
        comentarios: list,
        contexto: str = "",
    ) -> dict:
        """
        Análisis semántico individual de comentarios.

        Responsabilidades:
        - Separar literalidad de intención.
        - Detectar ironía.
        - Detectar sarcasmo.
        - Determinar polaridad real.
        - Identificar tono.
        - Generar evidencias de la interpretación.
        - Informar nivel de confianza.

        Este método NO:
        - Calcula estadísticas.
        - Decide el plan del usuario.
        - Genera recomendaciones estratégicas.
        - Guarda memoria.
        - Aprende automáticamente.

        Esas responsabilidades pertenecen a capas superiores del MIC.
        """

        if not isinstance(comentarios, list):
            raise TypeError(
                "comentarios debe ser una lista de textos."
            )

        if not comentarios:
            return {
                "analyses": []
            }

        if len(comentarios) > 100:
            raise ValueError(
                f"Máximo 100 comentarios por análisis. "
                f"Recibiste {len(comentarios)}."
            )

        comentarios_normalizados = []

        for comentario in comentarios:

            if comentario is None:
                comentario = ""

            comentario = str(comentario).strip()

            comentarios_normalizados.append(comentario)

        comentarios_texto = "\n".join(
            f"[{i + 1}] {comentario}"
            for i, comentario in enumerate(comentarios_normalizados)
        )

        contexto_texto = (
            f"CONTEXTO ESPECÍFICO:\n{contexto.strip()}"
            if contexto and contexto.strip()
            else "CONTEXTO ESPECÍFICO:\nNo proporcionado."
        )

        prompt = f"""
Sos un lingüista experto en análisis de discurso argentino,
especializado en comunicación cotidiana, redes sociales,
lenguaje rioplatense, ironía, sarcasmo y análisis de intención.

Tu tarea NO es clasificar palabras.

Tu tarea es interpretar el significado probable del mensaje
considerando:

- significado literal
- intención comunicativa
- contexto disponible
- construcción lingüística
- contradicciones internas
- emojis
- expresiones coloquiales
- ironía
- sarcasmo
- polaridad real

El objetivo principal es REDUCIR FALSOS POSITIVOS DE IRONÍA.

{contexto_texto}

COMENTARIOS:

{comentarios_texto}


============================================================
REGLAS DE INTERPRETACIÓN
============================================================

1. LITERALIDAD VS INTENCIÓN

Separá siempre:

literal_meaning:
    Lo que literalmente expresa el comentario.

inferred_meaning:
    Lo que probablemente intenta comunicar.

No asumas que ambos significados son diferentes.

Si el comentario es literal, ambos pueden ser prácticamente iguales.


============================================================
2. IRONÍA
============================================================

La ironía ocurre cuando existe una diferencia relevante
entre el significado literal y la intención comunicativa.

Ejemplo:

"Qué buena gestión, cada día estamos mejor."

Si el contexto indica problemas de gestión:

irony = true
tone = ironic_negative

Pero:

"Qué buena gestión hicieron."

Sin contexto adicional NO demuestra ironía.

En ausencia de evidencia suficiente:

irony = false
tone = neutral o ambiguous


============================================================
3. SARCASMO
============================================================

No confundas sarcasmo con cualquier comentario negativo.

El sarcasmo suele implicar:

- burla
- ridiculización
- desprecio
- exageración intencional
- contraste deliberado

Un comentario puede ser:

irony = true
sarcasm = false

Por lo tanto, NO marques sarcasmo automáticamente
cuando detectes ironía.


============================================================
4. REGLA CONTRA FALSOS POSITIVOS
============================================================

Esta regla tiene prioridad.

NO inventes ironía.

NO interpretes automáticamente como irónicos:

"Qué fenómeno."

"Un genio."

"Excelente."

"Sí, claro."

"Una maravilla."

"Bueno... veremos."

Estas expresiones pueden ser:

- literales
- irónicas
- sarcásticas
- ambiguas

La decisión debe depender de la evidencia disponible.


============================================================
5. EVIDENCIA
============================================================

Si clasificás un comentario como irónico o sarcástico,
debe existir evidencia concreta.

Ejemplos de evidencia válida:

- "contraste entre elogio literal y contexto negativo"
- "expresión positiva seguida de una consecuencia negativa"
- "exageración incompatible con el contexto"
- "emoji que contradice el significado literal"
- "construcción lingüística utilizada como burla"

NO uses como única evidencia:

"parece irónico"

"suena irónico"

"probablemente es sarcasmo"

La evidencia debe explicar POR QUÉ.


============================================================
6. EMOJIS
============================================================

Los emojis son MODIFICADORES CONTEXTUALES.

NO son pruebas automáticas de ironía.

Ejemplos:

👏 💪 ✌️ 😊

Pueden reforzar una valoración positiva.

😡 👎 🙄

Pueden expresar rechazo, molestia o desaprobación.

😂

Puede representar:

- diversión
- humor
- burla
- complicidad
- ironía

Por lo tanto:

Un emoji aislado NO demuestra ironía.

Si el emoji contradice el texto literal,
puede constituir evidencia relevante.


============================================================
7. LENGUAJE ARGENTINO
============================================================

Reconocé expresiones como:

- laburar
- bancar
- boludo / boludeces
- fenómeno
- groso
- mamita
- capo
- maestro
- genio
- crack
- qué bárbaro
- dale
- sí, claro
- mirá vos

Pero NO determines la polaridad solamente por estas palabras.

El significado depende del contexto y de la construcción
completa del mensaje.


============================================================
8. POLARIDAD
============================================================

sentiment debe representar la valoración REAL del comentario:

positive
negative
neutral

No confundas:

literalidad positiva

con

intención positiva.


Ejemplo:

"Excelente, otra vez aumentaron los impuestos."

Literalmente:
positivo.

Intención:
negativa.

Por lo tanto:

sentiment = negative
irony = true
tone = ironic_negative


============================================================
9. AMBIGÜEDAD
============================================================

Cuando la evidencia no permite determinar correctamente
la intención:

NO inventes una interpretación.

Utilizá:

tone = ambiguous

y una confidence baja o moderada.

La ambigüedad es un resultado válido.

Es preferible:

"no podemos determinarlo"

antes que:

"probablemente sea irónico"


============================================================
10. CONFIANZA
============================================================

confidence debe representar la confianza en la interpretación.

Usá valores entre:

0.0 y 1.0

Orientativamente:

0.90 - 1.00
Evidencia muy clara.

0.75 - 0.89
Evidencia fuerte.

0.50 - 0.74
Interpretación razonable pero con incertidumbre.

0.00 - 0.49
Alta ambigüedad.


============================================================
FORMATO DE RESPUESTA
============================================================

Respondé ÚNICAMENTE JSON válido.

NO uses markdown.

NO agregues explicaciones fuera del JSON.

La estructura obligatoria es:

{{
  "analyses": [
    {{
      "message_id": "1",
      "texto_original": "texto completo del comentario",
      "sentiment": "positive|negative|neutral",
      "tone": "positive|negative|neutral|ironic_positive|ironic_negative|sarcastic|mixed|ambiguous",
      "irony": false,
      "sarcasm": false,
      "irony_polarity": "positive|negative|neutral|none",
      "confidence": 0.0,
      "literal_meaning": "significado literal",
      "inferred_meaning": "intención probable",
      "evidence": []
    }}
  ]
}}


============================================================
REGLAS DEL JSON
============================================================

1. "analyses" debe existir.

2. Debe contener exactamente un elemento
   por cada comentario recibido.

3. message_id debe ser:

"1"
"2"
"3"

etc.

4. texto_original debe conservar el comentario original.

5. sentiment debe ser exclusivamente:

positive
negative
neutral

6. tone debe ser exclusivamente:

positive
negative
neutral
ironic_positive
ironic_negative
sarcastic
mixed
ambiguous

7. irony debe ser booleano.

8. sarcasm debe ser booleano.

9. irony_polarity debe ser exclusivamente:

positive
negative
neutral
none

10. confidence debe estar entre 0.0 y 1.0.

11. evidence debe ser una lista.

12. Si irony = false:

irony_polarity = "none"

13. Si no existe evidencia suficiente:

NO marques irony = true.

14. No agregues campos adicionales.
"""

        max_intentos = 3
        ultimo_error = None

        for intento in range(max_intentos):

            try:

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Sos un lingüista experto en discurso argentino. "
                                "Analizás intención, ironía y sarcasmo. "
                                "Priorizás evidencia sobre suposiciones. "
                                "La ambigüedad es un resultado válido. "
                                "Nunca inventes ironía. "
                                "Respondé exclusivamente JSON válido."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=(
                        0.15 if intento == 0
                        else 0.05
                    ),
                    max_tokens=4000,
                )

                if hasattr(self, "token_monitor") and self.token_monitor is not None:
                    self.token_monitor.update_from_response(response)

                contenido = response.choices[0].message.content.strip()

                resultado = self._extraer_json(contenido)

                if not isinstance(resultado, dict):
                    raise ValueError(
                        "La respuesta del modelo no es un objeto JSON."
                    )

                if "analyses" not in resultado:
                    raise ValueError(
                        "Falta el campo 'analyses'."
                    )

                analyses = resultado["analyses"]

                if not isinstance(analyses, list):
                    raise ValueError(
                        "'analyses' debe ser una lista."
                    )

                if len(analyses) != len(comentarios_normalizados):

                    raise ValueError(
                        f"El modelo analizó "
                        f"{len(analyses)} comentarios "
                        f"pero se enviaron "
                        f"{len(comentarios_normalizados)}."
                    )

                sentiments_validos = {
                    "positive",
                    "negative",
                    "neutral",
                }

                tones_validos = {
                    "positive",
                    "negative",
                    "neutral",
                    "ironic_positive",
                    "ironic_negative",
                    "sarcastic",
                    "mixed",
                    "ambiguous",
                }

                irony_polarities_validas = {
                    "positive",
                    "negative",
                    "neutral",
                    "none",
                }

                for index, analysis in enumerate(analyses):

                    if not isinstance(analysis, dict):
                        raise ValueError(
                            f"El análisis {index + 1} "
                            "no es un objeto JSON."
                        )

                    expected_id = str(index + 1)

                    if str(
                        analysis.get("message_id")
                    ) != expected_id:

                        raise ValueError(
                            f"message_id incorrecto en "
                            f"posición {index + 1}."
                        )

                    sentiment = analysis.get("sentiment")

                    if sentiment not in sentiments_validos:

                        raise ValueError(
                            f"sentiment inválido en "
                            f"mensaje {expected_id}: "
                            f"{sentiment}"
                        )

                    tone = analysis.get("tone")

                    if tone not in tones_validos:

                        raise ValueError(
                            f"tone inválido en "
                            f"mensaje {expected_id}: "
                            f"{tone}"
                        )

                    irony = analysis.get("irony")

                    if not isinstance(irony, bool):

                        raise ValueError(
                            f"'irony' debe ser booleano "
                            f"en mensaje {expected_id}."
                        )

                    sarcasm = analysis.get("sarcasm")

                    if not isinstance(sarcasm, bool):

                        raise ValueError(
                            f"'sarcasm' debe ser booleano "
                            f"en mensaje {expected_id}."
                        )

                    irony_polarity = analysis.get(
                        "irony_polarity"
                    )

                    if (
                        irony_polarity
                        not in irony_polarities_validas
                    ):

                        raise ValueError(
                            f"irony_polarity inválida en "
                            f"mensaje {expected_id}."
                        )

                    if not irony and irony_polarity != "none":

                        raise ValueError(
                            f"Mensaje {expected_id}: "
                            "irony=false requiere "
                            "irony_polarity='none'."
                        )

                    confidence = analysis.get(
                        "confidence"
                    )

                    if not isinstance(
                        confidence,
                        (int, float),
                    ):

                        raise ValueError(
                            f"confidence inválida en "
                            f"mensaje {expected_id}."
                        )

                    if not 0.0 <= float(confidence) <= 1.0:

                        raise ValueError(
                            f"confidence fuera de rango "
                            f"en mensaje {expected_id}."
                        )

                    evidence = analysis.get(
                        "evidence"
                    )

                    if not isinstance(
                        evidence,
                        list,
                    ):

                        raise ValueError(
                            f"'evidence' debe ser una lista "
                            f"en mensaje {expected_id}."
                        )

                    if irony and len(evidence) == 0:

                        raise ValueError(
                            f"El mensaje {expected_id} "
                            "fue marcado como irónico "
                            "pero no contiene evidencias."
                        )

                return resultado

            # ---------------------------------------------------------
            # DETECCIÓN DE RATE LIMIT (NUEVO)
            # ---------------------------------------------------------
            except Exception as e:
                # Detectar rate limit de Groq (HTTP 429)
                # NO reintentar: el límite es diario, reintentar es inútil
                error_type = type(e).__name__
                error_str = str(e)
                
                is_rate_limit = (
                    "RateLimitError" in error_type or
                    "rate_limit" in error_str.lower() or
                    "429" in error_str
                )
                
                if is_rate_limit:
                    # Extraer tiempo de reseteo del mensaje si es posible
                    reset_info = self._extract_reset_time(error_str)
                    
                    raise Exception(
                        f"🚫 Rate limit de Groq alcanzado. "
                        f"NO se reintentará automáticamente. "
                        f"{reset_info}"
                    ) from e
                
                # Para errores de parsing JSON, reintentar
                if isinstance(e, (ValueError,)) and "JSON" in error_str:
                    ultimo_error = e
                    print(
                        f"⚠️ Intento "
                        f"{intento + 1}/{max_intentos} "
                        f"falló (JSON inválido): "
                        f"{str(e)[:200]}"
                    )
                    continue
                
                # Para otros errores, también reintentar
                ultimo_error = e
                print(
                    f"⚠️ Intento "
                    f"{intento + 1}/{max_intentos} "
                    f"falló en analizar_semantica: "
                    f"{str(e)[:200]}"
                )
                continue

        raise Exception(
            "Error procesando análisis semántico "
            f"después de {max_intentos} intentos: "
            f"{str(ultimo_error)}"
        )
    
    def _extract_reset_time(self, error_message: str) -> str:
        """
        Extrae información de tiempo de reseteo del mensaje de error de Groq.
        
        Ejemplo de mensaje:
        "Please try again in 1h5m7.872s"
        
        Retorna un string legible con el tiempo estimado.
        """
        import re
        
        # Buscar patrón "XhYmZs"
        match = re.search(
            r'(\d+)h(\d+)m([\d.]+)s',
            error_message
        )
        
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            if total_seconds > 3600:
                return (
                    f"Esperá aproximadamente "
                    f"{hours}h {minutes}m para reintentar."
                )
            elif total_seconds > 60:
                return (
                    f"Esperá aproximadamente "
                    f"{minutes}m {int(seconds)}s para reintentar."
                )
            else:
                return (
                    f"Esperá aproximadamente "
                    f"{int(seconds)}s para reintentar."
                )
        
        # Buscar patrón alternativo "in Xs"
        match = re.search(r'in ([\d.]+)s', error_message)
        if match:
            seconds = float(match.group(1))
            return f"Esperá aproximadamente {int(seconds)}s para reintentar."
        
        return "Esperá un tiempo antes de reintentar."
    
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