# app/services/analysis/groq_llm.py
"""
Cliente LLM para Groq.
Provee métodos para análisis de sentimientos y semántico.
"""
import os
import json
import re
from groq import Groq
from app.services.analysis.token_monitor import TokenMonitor


def cargar_prompt(nombre: str) -> str:
    """Carga el contenido de un archivo de prompt desde app/mic/prompts/"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ruta = os.path.join(base_dir, "mic", "prompts", nombre)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Prompt '{nombre}' no encontrado en {ruta}")


class GroqLLMClient:
    """Cliente para análisis de texto con modelos LLM de Groq."""
    
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.token_monitor = TokenMonitor.get_instance()

    def _extraer_json(self, texto: str) -> dict:
        """Extrae JSON de una respuesta del LLM de forma robusta."""

        texto = texto.strip()

        # Limpiar bloques markdown
        if texto.startswith("```"):
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', texto)
            if match:
                texto = match.group(1).strip()

        # Reparar errores comunes del modelo:
        # Ej: "resumen_corto " -> "resumen_corto"
        texto = re.sub(
            r'"([a-zA-Z_][a-zA-Z0-9_]*)\s+"',
            r'"\1"',
            texto
        )

        # Intento directo
        try:
            return json.loads(texto)

        except json.JSONDecodeError:
            pass

        # Buscar objeto JSON dentro del texto
        primer_llave = texto.find("{")
        ultima_llave = texto.rfind("}")

        if primer_llave != -1 and ultima_llave != -1:
            texto_extraido = texto[primer_llave:ultima_llave + 1]

            try:
                return json.loads(texto_extraido)

            except json.JSONDecodeError:
                pass


        # Reparar JSON truncado
        try:

            abiertas = texto.count("{")
            cerradas = texto.count("}")

            if abiertas > cerradas:
                texto += "}" * (abiertas - cerradas)

            abiertos = texto.count("[")
            cerrados = texto.count("]")

            if abiertos > cerrados:
                texto += "]" * (abiertos - cerrados)

            return json.loads(texto)

        except json.JSONDecodeError:
            pass


        raise ValueError(
            f"No se pudo extraer JSON válido. Respuesta recibida: {texto[:300]}"
        )

    def analizar_sentimientos(self, comentarios: list, contexto: str = "") -> dict:
        """
        Analiza sentimientos de una lista de comentarios.
        Usado por planes Free/Bronce.
        Divide en lotes para evitar límites de TPM.
        """
        if len(comentarios) > 100:
            raise ValueError(f"Máximo 100 comentarios por análisis. Recibiste {len(comentarios)}.")
        
        # Dividir en lotes de 15 para evitar error 413
        lote_tamano = 15
        lotes = [comentarios[i:i + lote_tamano] for i in range(0, len(comentarios), lote_tamano)]
        resultados_lotes = []
        
        for idx_lote, lote in enumerate(lotes, 1):
            comentarios_texto = "\n".join([f"{i+1}. {c}" for i, c in enumerate(lote)])
            contexto_texto = f"\nCONTEXTO ESPECÍFICO: {contexto}" if contexto else "\nCONTEXTO ESPECÍFICO: Análisis general de redes sociales sin contexto adicional."
            
            # Cargar prompt desde archivo
            prompt_base = cargar_prompt("sentimientos_prompt.txt")
            prompt = prompt_base.format(
                total_comentarios=len(lote),
                contexto_texto=contexto_texto,
                comentarios_texto=comentarios_texto
            )
            
            max_intentos = 3
            ultimo_error = None
            
            for intento in range(max_intentos):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system", 
                                "content": "Respondé SIEMPRE con JSON válido. NUNCA incluyas texto fuera del JSON. NUNCA uses bloques de código markdown."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.15 if intento == 0 else 0.05,
                        max_tokens=3500,
                    )
                    
                    # ✅ CORRECCIÓN DEFENSIVA
                    if hasattr(self, "token_monitor") and self.token_monitor is not None:
                        self.token_monitor.update_from_response(response)
                    
                    contenido = response.choices[0].message.content.strip()

                    print("\n======================")
                    print(contenido)
                    print("======================\n")

                    resultado = self._extraer_json(contenido)


                    if "estadisticas" not in resultado or "analisis_individual" not in resultado:
                        raise ValueError(
                            "Faltan campos requeridos en la respuesta"
                        )


                    # Validar cantidad de análisis recibidos
                    cantidad_recibida = len(
                        resultado.get("analisis_individual", [])
                    )

                    cantidad_esperada = len(lote)


                    if cantidad_recibida != cantidad_esperada:
                        raise ValueError(
                            f"El modelo devolvió {cantidad_recibida} análisis "
                            f"pero se enviaron {cantidad_esperada} comentarios"
                        )


                    resultados_lotes.append(resultado)

                    break
                    
                except (json.JSONDecodeError, ValueError) as e:
                    ultimo_error = e
                    print(f"⚠️ Lote {idx_lote}, Intento {intento + 1}/{max_intentos} falló: {str(e)[:100]}")
                    continue
                except Exception as e:
                    error_str = str(e)
                    if "413" in error_str or "rate_limit" in error_str.lower():
                        # Si es error 413, no reintentar con el mismo modelo
                        print(f" Lote {idx_lote} falló por límite de tokens. Se usará fallback.")
                        raise  # Re-lanzar para que el provider maneje el fallback
                    ultimo_error = e
                    print(f"⚠️ Lote {idx_lote}, Intento {intento + 1}/{max_intentos} falló: {str(e)[:100]}")
                    continue
            
            # Si un lote falla completamente, detener el análisis.
            # No devolver resultados parciales.

            if len(resultados_lotes) < idx_lote:
                raise ValueError(
                    f"No se pudo procesar el lote {idx_lote} "
                    f"después de {max_intentos} intentos."
                )
        
        # Consolidar resultados de todos los lotes
        if len(resultados_lotes) == 1:
            return resultados_lotes[0]
        
        # Consolidación múltiple
        analisis_individual_consolidado = []
        temas_set, palabras_set, insights_set = set(), set(), set()
        total_positivos = total_neutrales = total_negativos = total_comentarios = 0
        
        for resultado in resultados_lotes:
            for item in resultado.get("analisis_individual", []):
                item["numero"] = (
                    len(analisis_individual_consolidado) + 1
                )
                analisis_individual_consolidado.append(item)

            temas_set.update(resultado.get("temas_principales", []))
            palabras_set.update(resultado.get("palabras_clave", []))
            insights_set.update(resultado.get("insights", []))
            
            stats = resultado.get("estadisticas", {})
            total_positivos += stats.get("positivos", 0)
            total_neutrales += stats.get("neutrales", 0)
            total_negativos += stats.get("negativos", 0)
            total_comentarios += stats.get("total", 0)
        
        pct_positivo = round((total_positivos / total_comentarios * 100)) if total_comentarios > 0 else 0
        pct_neutral = round((total_neutrales / total_comentarios * 100)) if total_comentarios > 0 else 0
        pct_negativo = round((total_negativos / total_comentarios * 100)) if total_comentarios > 0 else 0
        
        return {
            "analisis_individual": analisis_individual_consolidado,
            "resumen_general": "Análisis consolidado de múltiples lotes. " + resultados_lotes[0].get("resumen_general", ""),
            "estadisticas": {
                "total": total_comentarios,
                "positivos": total_positivos,
                "neutrales": total_neutrales,
                "negativos": total_negativos,
                "porcentaje_positivo": pct_positivo,
                "porcentaje_neutral": pct_neutral,
                "porcentaje_negativo": pct_negativo
            },
            "temas_principales": list(temas_set)[:5],
            "palabras_clave": list(palabras_set)[:5],
            "tono_general": resultados_lotes[0].get("tono_general", ""),
            "insights": list(insights_set)[:3],
            "recomendaciones": resultados_lotes[0].get("recomendaciones", [])
        }

    def analizar_semantica(self, comentarios: list, contexto: str = "") -> dict:
        """
        Análisis semántico individual de comentarios.
        Usado por planes Plata+.
        """
        if not isinstance(comentarios, list):
            raise TypeError("comentarios debe ser una lista de textos.")
        
        if len(comentarios) > 100:
            raise ValueError(f"Máximo 100 comentarios por análisis. Recibiste {len(comentarios)}.")
        
        if not comentarios:
            return {"analyses": []}
        
        comentarios = comentarios[:25]
        
        comentarios_normalizados = []
        for comentario in comentarios:
            if comentario is None:
                comentario = ""
            comentario = str(comentario).strip()
            comentarios_normalizados.append(comentario)
        
        comentarios_texto = "\n".join(f"[{i + 1}] {comentario}" for i, comentario in enumerate(comentarios_normalizados))
        contexto_texto = f"CONTEXTO ESPECÍFICO:\n{contexto.strip()}" if contexto and contexto.strip() else "CONTEXTO ESPECÍFICO:\nNo proporcionado."
        
        # Cargar prompt desde archivo
        prompt_base = cargar_prompt("semantic_prompt.txt")
        prompt = f"{prompt_base}\n\n{contexto_texto}\n\nCOMENTARIOS:\n\n{comentarios_texto}"
        
        max_intentos = 3
        ultimo_error = None
        
        for intento in range(max_intentos):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Sos un lingüista experto en discurso argentino. Analizás intención, ironía y sarcasmo. Priorizás evidencia sobre suposiciones. La ambigüedad es un resultado válido. Nunca inventes ironía. Respondé exclusivamente JSON válido."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.15 if intento == 0 else 0.05,
                    max_tokens=4000,
                )
                
                # ✅ CORRECCIÓN DEFENSIVA
                if hasattr(self, "token_monitor") and self.token_monitor is not None:
                    self.token_monitor.update_from_response(response)
                
                contenido = response.choices[0].message.content.strip()
                resultado = self._extraer_json(contenido)
                
                if not isinstance(resultado, dict):
                    raise ValueError("La respuesta del modelo no es un objeto JSON.")
                
                if "analyses" not in resultado:
                    raise ValueError("Falta el campo 'analyses'.")
                
                analyses = resultado["analyses"]
                
                if not isinstance(analyses, list):
                    raise ValueError("'analyses' debe ser una lista.")
                
                if len(analyses) != len(comentarios_normalizados):
                    raise ValueError(f"El modelo analizó {len(analyses)} comentarios pero se enviaron {len(comentarios_normalizados)}.")
                
                # Validaciones de contrato
                sentiments_validos = {"positive", "negative", "neutral"}
                tones_validos = {"positive", "negative", "neutral", "ironic_positive", "ironic_negative", "sarcastic", "mixed", "ambiguous"}
                irony_polarities_validas = {"positive", "negative", "neutral", "none"}
                
                for index, analysis in enumerate(analyses):
                    if not isinstance(analysis, dict):
                        raise ValueError(f"El análisis {index + 1} no es un objeto JSON.")
                    
                    expected_id = str(index + 1)
                    if str(analysis.get("message_id")) != expected_id:
                        raise ValueError(f"message_id incorrecto en posición {index + 1}.")
                    
                    sentiment = analysis.get("sentiment")
                    if sentiment not in sentiments_validos:
                        raise ValueError(f"sentiment inválido en mensaje {expected_id}: {sentiment}")
                    
                    tone = analysis.get("tone")
                    if tone not in tones_validos:
                        raise ValueError(f"tone inválido en mensaje {expected_id}: {tone}")
                    
                    irony = analysis.get("irony")
                    if not isinstance(irony, bool):
                        raise ValueError(f"'irony' debe ser booleano en mensaje {expected_id}.")
                    
                    sarcasm = analysis.get("sarcasm")
                    if not isinstance(sarcasm, bool):
                        raise ValueError(f"'sarcasm' debe ser booleano en mensaje {expected_id}.")
                    
                    irony_polarity = analysis.get("irony_polarity")
                    if irony_polarity not in irony_polarities_validas:
                        raise ValueError(f"irony_polarity inválida en mensaje {expected_id}.")
                    
                    if not irony and irony_polarity != "none":
                        raise ValueError(f"Mensaje {expected_id}: irony=false requiere irony_polarity='none'.")
                    
                    confidence = analysis.get("confidence")
                    if not isinstance(confidence, (int, float)):
                        raise ValueError(f"confidence inválida en mensaje {expected_id}.")
                    
                    if not 0.0 <= float(confidence) <= 1.0:
                        raise ValueError(f"confidence fuera de rango en mensaje {expected_id}.")
                    
                    evidence = analysis.get("evidence")
                    if not isinstance(evidence, list):
                        raise ValueError(f"'evidence' debe ser una lista en mensaje {expected_id}.")
                    
                    if irony and len(evidence) == 0:
                        raise ValueError(f"El mensaje {expected_id} fue marcado como irónico pero no contiene evidencias.")
                
                return resultado
                
            except Exception as e:
                error_type = type(e).__name__
                error_str = str(e)
                
                is_rate_limit = "RateLimitError" in error_type or "rate_limit" in error_str.lower() or "429" in error_str or "413" in error_str
                
                if is_rate_limit:
                    reset_info = self._extract_reset_time(error_str)
                    raise Exception(f" Rate limit de Groq alcanzado. NO se reintentará automáticamente. {reset_info}") from e
                
                if isinstance(e, (ValueError,)) and "JSON" in error_str:
                    ultimo_error = e
                    print(f"⚠️ Intento {intento + 1}/{max_intentos} falló (JSON inválido): {str(e)[:200]}")
                    continue
                
                ultimo_error = e
                print(f"⚠️ Intento {intento + 1}/{max_intentos} falló en analizar_semantica: {str(e)[:200]}")
                continue
        
        raise Exception(f"Error procesando análisis semántico después de {max_intentos} intentos: {str(ultimo_error)}")

    def _extract_reset_time(self, error_message: str) -> str:
        """Extrae información de tiempo de reseteo del mensaje de error de Groq."""
        match = re.search(r'(\d+)h(\d+)m([\d.]+)s', error_message)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            if total_seconds > 3600:
                return f"Esperá aproximadamente {hours}h {minutes}m para reintentar."
            elif total_seconds > 60:
                return f"Esperá aproximadamente {minutes}m {int(seconds)}s para reintentar."
            else:
                return f"Esperá aproximadamente {int(seconds)}s para reintentar."
        
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