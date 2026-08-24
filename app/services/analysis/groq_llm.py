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
    
    def __init__(self, model: str | None = None):
        # ✅ Import diferido: evita el import circular
        # groq_llm → providers → groq_provider → groq_llm
        if model is None:
            from app.mic.providers.model_config import DEFAULT_MODEL
            model = DEFAULT_MODEL
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

    def analizar_sentimientos(self, comentarios: list, contexto: str = "", limite_comentarios: int | None = None) -> dict:
        """
        Analiza sentimientos de una lista de comentarios.
        Usado por planes Free/Bronce.
        Divide en lotes para evitar límites de TPM.
        """
        advertencia = None
        if limite_comentarios and len(comentarios) > limite_comentarios:
            advertencia = (
                f"Recibiste {len(comentarios)} comentarios. "
                f"Se analizaron solo los primeros {limite_comentarios} según tu plan."
            )
            comentarios = comentarios[:limite_comentarios]
        
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
            
            # Si un lote falla después de 3 intentos, lo marcamos como "no analizable"
            # y continuamos con los siguientes lotes. El usuario recibe un informe parcial
            # con una advertencia clara.
            if len(resultados_lotes) < idx_lote:
                # Crear análisis "vacíos" para los mensajes de este lote
                inicio_lote = (idx_lote - 1) * lote_tamano
                for i_rel, _ in enumerate(lote):
                    resultados_lotes.append({
                        "analisis_individual": [{
                            "message_id": str(inicio_lote + i_rel + 1),
                            "texto_original": lote[i_rel],
                            "sentiment": "neutral",
                            "tone": "ambiguous",
                            "irony": False,
                            "sarcasm": False,
                            "irony_polarity": "none",
                            "confidence": 0.0,
                            "literal_meaning": lote[i_rel],
                            "inferred_meaning": "No se pudo analizar (error del modelo).",
                            "evidence": [],
                        }],
                        "estadisticas": {"total": 1, "positivos": 0, "neutrales": 1, "negativos": 0},
                        "temas_principales": [],
                        "palabras_clave": [],
                        "insights": [],
                        "recomendaciones": [],
                        "resumen_general": "Análisis no disponible por error del modelo.",
                    })
        
        # Consolidar resultados de todos los lotes
        if len(resultados_lotes) == 1:
            resultado = resultados_lotes[0]
            if advertencia:
                resultado["advertencia"] = advertencia
            return resultado
     
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
            "recomendaciones": resultados_lotes[0].get("recomendaciones", []),
            "advertencia": advertencia,
        }

            
    def analizar_semantica(self, comentarios: list, contexto: str = "", limite_comentarios: int | None = None) -> dict:
        """
        Análisis semántico individual de comentarios.
        Usado por planes Plata+.
        Divide en lotes de 5 para evitar truncamiento de JSON por límite de tokens.
        ✅ Si el modelo no existe (404) o no tiene cuota (429/413), hace fallback
        automático al siguiente modelo de la cadena y reintenta el lote.
        """
        if not isinstance(comentarios, list):
            raise TypeError("comentarios debe ser una lista de textos.")
        advertencia = None
        if limite_comentarios and len(comentarios) > limite_comentarios:
            advertencia = (
                f"Recibiste {len(comentarios)} comentarios. "
                f"Se analizaron solo los primeros {limite_comentarios} según tu plan."
            )
            comentarios = comentarios[:limite_comentarios]

        if not comentarios:
            return {"analyses": []}

        # Normalizar comentarios
        comentarios_normalizados = []
        for comentario in comentarios:
            if comentario is None:
                comentario = ""
            comentario = str(comentario).strip()
            comentarios_normalizados.append(comentario)

        # Dividir en lotes de 5 para evitar truncamiento de JSON
        lote_tamano = 5
        lotes = [
            comentarios_normalizados[i:i + lote_tamano]
            for i in range(0, len(comentarios_normalizados), lote_tamano)
        ]

        todos_analyses = []
        offset = 0  # Para mantener message_id secuencial global
        modelos_intentados = [self.model]

        for idx_lote, lote in enumerate(lotes, 1):
            print(f"📦 Procesando lote {idx_lote}/{len(lotes)} ({len(lote)} comentarios) con modelo {self.model}")
            resultado_lote = None
            try:
                resultado_lote = self._analizar_semantica_lote(
                    comentarios=lote,
                    contexto=contexto,
                    offset=offset,
                )
            except Exception as e:
                error_str = str(e)
                es_modelo_muerto = (
                    "model_not_found" in error_str
                    or "does not exist" in error_str
                    or "404" in error_str
                )
                es_cuota = (
                    "429" in error_str
                    or "413" in error_str
                    or "rate_limit" in error_str.lower()
                )

                if es_modelo_muerto or es_cuota:
                    # ✅ FALLBACK AUTOMÁTICO: siguiente modelo de la cadena
                    from app.mic.providers.model_config import FALLBACK_CHAINS, AVAILABLE_MODELS
                    siguiente = None
                    for fb in FALLBACK_CHAINS.get(self.model, []):
                        if fb not in modelos_intentados:
                            siguiente = fb
                            break
                    if siguiente is None:  # última red de seguridad: cualquier modelo libre
                        for modelo_id in AVAILABLE_MODELS:
                            if modelo_id not in modelos_intentados:
                                siguiente = modelo_id
                                break

                    if siguiente:
                        motivo = "no existe en Groq" if es_modelo_muerto else "sin cuota"
                        print(f"🔄 Modelo {self.model} {motivo}. Cambiando a {siguiente}")
                        self.model = siguiente
                        modelos_intentados.append(siguiente)
                        if not advertencia:
                            advertencia = f"El modelo principal no está disponible; se usó {siguiente}."
                        # Reintentar ESTE lote con el modelo nuevo
                        try:
                            resultado_lote = self._analizar_semantica_lote(
                                comentarios=lote,
                                contexto=contexto,
                                offset=offset,
                            )
                        except Exception as e2:
                            print(f"❌ Lote {idx_lote} falló también con fallback: {str(e2)[:200]}")
                    else:
                        print(f"❌ No quedan modelos alternativos. Lote {idx_lote} sin análisis.")
                else:
                    print(f"❌ Lote {idx_lote} falló: {error_str[:200]}")

            if resultado_lote:
                todos_analyses.extend(resultado_lote.get("analyses", []))
            offset += len(lote)

        resultado = {"analyses": todos_analyses}
        if advertencia:
            resultado["warning"] = advertencia
        return resultado
    
    
    def _analizar_semantica_lote(
        self,
        comentarios: list,
        contexto: str,
        offset: int = 0,
    ) -> dict:
        """Analiza un lote de comentarios (método interno)."""
        comentarios_texto = "\n".join(
            f"[{i + 1}] {comentario}"
            for i, comentario in enumerate(comentarios)
        )
        contexto_texto = (
            f"CONTEXTO ESPECÍFICO:\n{contexto.strip()}"
            if contexto and contexto.strip()
            else "CONTEXTO ESPECÍFICO:\nNo proporcionado."
        )

        prompt_base = cargar_prompt("semantic_prompt.txt")
        prompt = f"{prompt_base}\n{contexto_texto}\nCOMENTARIOS:\n{comentarios_texto}"

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
                                "Respondé exclusivamente JSON válido. "
                                "NO incluyas 'texto_original' en el JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.15 if intento == 0 else 0.05,
                    max_tokens=6000,  # ✅ Aumentado de 4000 a 6000
                )

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

                if len(analyses) != len(comentarios):
                    raise ValueError(
                        f"El modelo analizó {len(analyses)} comentarios "
                        f"pero se enviaron {len(comentarios)}."
                    )

                # Validaciones de contrato
                sentiments_validos = {"positive", "negative", "neutral"}
                tones_validos = {
                    "positive", "negative", "neutral",
                    "ironic_positive", "ironic_negative",
                    "sarcastic", "mixed", "ambiguous",
                }
                irony_polarities_validas = {"positive", "negative", "neutral", "none"}

                for index, analysis in enumerate(analyses):
                    if not isinstance(analysis, dict):
                        raise ValueError(f"El análisis {index + 1} no es un objeto JSON.")

                    expected_id = str(index + 1)
                    if str(analysis.get("message_id")) != expected_id:
                        raise ValueError(
                            f"message_id incorrecto en posición {index + 1}."
                        )

                    sentiment = analysis.get("sentiment")
                    if sentiment not in sentiments_validos:
                        raise ValueError(
                            f"sentiment inválido en mensaje {expected_id}: {sentiment}"
                        )

                    tone = analysis.get("tone")
                    if tone not in tones_validos:
                        raise ValueError(
                            f"tone inválido en mensaje {expected_id}: {tone}"
                        )

                    irony = analysis.get("irony")
                    if not isinstance(irony, bool):
                        raise ValueError(
                            f"'irony' debe ser booleano en mensaje {expected_id}."
                        )

                    sarcasm = analysis.get("sarcasm")
                    if not isinstance(sarcasm, bool):
                        raise ValueError(
                            f"'sarcasm' debe ser booleano en mensaje {expected_id}."
                        )

                    irony_polarity = analysis.get("irony_polarity")
                    if irony_polarity not in irony_polarities_validas:
                        raise ValueError(
                            f"irony_polarity inválida en mensaje {expected_id}."
                        )

                    if not irony and irony_polarity != "none":
                        # Autocorrección defensiva: el modelo a veces deja polarity residual.
                        # No es un error del análisis, es una inconsistencia menor que corregimos.
                        analysis["irony_polarity"] = "none"
                        irony_polarity = "none"

                    confidence = analysis.get("confidence")
                    if not isinstance(confidence, (int, float)):
                        raise ValueError(
                            f"confidence inválida en mensaje {expected_id}."
                        )

                    if not 0.0 <= float(confidence) <= 1.0:
                        raise ValueError(
                            f"confidence fuera de rango en mensaje {expected_id}."
                        )

                    evidence = analysis.get("evidence")
                    if not isinstance(evidence, list):
                        raise ValueError(
                            f"'evidence' debe ser una lista en mensaje {expected_id}."
                        )

                    # ✅ Relajado: si hay ironía pero no hay evidencia, NO falla.
                    # El modelo a veces no genera evidencia aunque detecte ironía.
                    # if irony and len(evidence) == 0:
                    #     raise ValueError(...)

                    # ✅ Corregir message_id para mantener secuencia global
                    analysis["message_id"] = str(offset + index + 1)

                return resultado

            except Exception as e:
                error_type = type(e).__name__
                error_str = str(e)

                # ✅ FAIL-FAST: modelo inexistente (404 / model_not_found).
                # No quemar 3 reintentos contra un modelo muerto:
                # relanzamos YA para que analizar_semantica() cambie de
                # modelo y reintente el lote con el fallback.
                if (
                    "model_not_found" in error_str
                    or "does not exist" in error_str
                    or "404" in error_str
                ):
                    raise

                is_rate_limit = (
                    "RateLimitError" in error_type
                    or "rate_limit" in error_str.lower()
                    or "429" in error_str
                    or "413" in error_str
                )
                if is_rate_limit:
                    reset_info = self._extract_reset_time(error_str)
                    raise Exception(
                        f"⚠️ Rate limit de Groq alcanzado. "
                        f"NO se reintentará automáticamente. {reset_info}"
                    ) from e

                if isinstance(e, ValueError) and "JSON" in error_str:
                    ultimo_error = e
                    print(
                        f"⚠️ Lote semántico, Intento {intento + 1}/{max_intentos} "
                        f"falló (JSON inválido): {str(e)[:200]}"
                    )
                    continue

                ultimo_error = e
                print(
                    f"⚠️ Lote semántico, Intento {intento + 1}/{max_intentos} "
                    f"falló: {str(e)[:200]}"
                )
                continue

        raise Exception(
            f"Error procesando análisis semántico después de "
            f"{max_intentos} intentos: {str(ultimo_error)}"
        )

    # =========================================================================
    # RESUMEN EJECUTIVO (meta-análisis) — escalable por tandas
    # =========================================================================
    def resumir_conversacion(self, analyses: list, contexto: str = "") -> dict:
        """
        Meta-análisis: genera un resumen ejecutivo de la conversación.
        ✅ Escalable: si hay más de 50 análisis, resume por tandas y consolida.
        """
        if not analyses:
            return {}
        if len(analyses) > 50:
            return self._resumir_en_tandas(analyses, contexto)
        prompt = self._armar_prompt_resumen(analyses, contexto, trunc=80)
        return self._llamar_resumen(prompt)

    def _armar_prompt_resumen(self, analyses: list, contexto: str, trunc: int = 80) -> str:
        """Arma el prompt del resumen ejecutivo cargando el archivo de prompts."""
        vista = []
        for i, a in enumerate(analyses, 1):
            literal = (a.get('literal_meaning', '') or '')[:trunc]
            inferido = (a.get('inferred_meaning', '') or '')[:trunc]
            vista.append(
                f"[{i}] sent={a.get('sentiment')} | tone={a.get('tone')} | "
                f"irony={a.get('irony')} | sarc={a.get('sarcasm')} | "
                f"lit:{literal} | inf:{inferido}"
            )
        analyses_texto = "\n".join(vista)
        contexto_texto = contexto.strip() if contexto and contexto.strip() else "No proporcionado."

        prompt_base = cargar_prompt("resumen_ejecutivo_prompt.txt")
        return (
            prompt_base
            .replace("__CONTEXTO__", contexto_texto)
            .replace("__ANALISES__", analyses_texto)
        )

    def _llamar_resumen(self, prompt: str) -> dict:
        """Llama al LLM para el resumen ejecutivo, con reintentos y fallback TPM."""
        max_intentos = 3
        ultimo_error = None
        for intento in range(max_intentos):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Sos un analista de opinión pública. Respondés exclusivamente con JSON válido."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=1500,
                )
                if hasattr(self, "token_monitor") and self.token_monitor is not None:
                    self.token_monitor.update_from_response(response)
                contenido = response.choices[0].message.content.strip()
                resultado = self._extraer_json(contenido)
                if not isinstance(resultado, dict):
                    raise ValueError("El resumen no es un objeto JSON.")
                for campo in ["resumen_general", "conclusion", "enfoque_solucion"]:
                    if campo not in resultado:
                        raise ValueError(f"Falta el campo '{campo}' en el resumen.")
                return resultado
            except Exception as e:
                ultimo_error = e
                error_str = str(e)
                es_cuota = ("429" in error_str or "413" in error_str or "rate_limit" in error_str.lower())
                if es_cuota and intento == 0:
                    from app.mic.providers.model_config import FALLBACK_CHAINS
                    fallbacks = FALLBACK_CHAINS.get(self.model, [])
                    if fallbacks:
                        siguiente = fallbacks[0]
                        print(f"🔄 Resumen ejecutivo: {self.model} excedió TPM. Cambiando a {siguiente}")
                        self.model = siguiente
                        continue
                print(f"⚠️ Resumen ejecutivo, intento {intento + 1}/{max_intentos} falló: {error_str[:200]}")
                continue
        raise Exception(f"Error generando resumen ejecutivo: {str(ultimo_error)}")

    def _resumir_en_tandas(self, analyses: list, contexto: str) -> dict:
        """Para conversaciones grandes: resume por tandas de 50 y consolida."""
        tam_tanda = 50
        tandas = [analyses[i:i + tam_tanda] for i in range(0, len(analyses), tam_tanda)]
        parciales = []
        for n, tanda in enumerate(tandas, 1):
            print(f"📑 Resumen ejecutivo: tanda {n}/{len(tandas)} ({len(tanda)} análisis)")
            prompt = self._armar_prompt_resumen(tanda, contexto, trunc=60)
            try:
                parciales.append(self._llamar_resumen(prompt))
            except Exception as e:
                print(f"⚠️ Tanda {n} del resumen falló: {str(e)[:150]}")
        if not parciales:
            raise Exception("No se pudo generar ningún resumen parcial.")
        if len(parciales) == 1:
            return parciales[0]

        texto_parciales = "\n\n".join(
            f"PARTE {i}:\n"
            f"Resumen: {p.get('resumen_general', '')}\n"
            f"Puntos fuertes: {'; '.join(p.get('puntos_fuertes', []))}\n"
            f"Puntos débiles: {'; '.join(p.get('puntos_debiles', []))}\n"
            f"Polaridad: {p.get('polaridad_dominante', '')}\n"
            f"Conclusión: {p.get('conclusion', '')}\n"
            f"Enfoque: {p.get('enfoque_solucion', '')}"
            for i, p in enumerate(parciales, 1)
        )
        contexto_texto = contexto.strip() if contexto and contexto.strip() else "No proporcionado."

        prompt_base = cargar_prompt("resumen_consolidacion_prompt.txt")
        prompt_final = (
            prompt_base
            .replace("__CONTEXTO__", contexto_texto)
            .replace("__PARCIALES__", texto_parciales)
        )

        return self._llamar_resumen(prompt_final)

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