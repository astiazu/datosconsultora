# app/services/analysis/text_cleaner.py
"""
Limpieza inteligente de comentarios copiados de redes sociales.
Detecta automáticamente la red social y extrae pares (Usuario, Comentario).
"""
import re
from typing import List, Tuple

# Patrones de metadata que deben eliminarse por completo
PATTERNS_METADATA = [
    r'^\s*\d+\s*[dhms]\s*$',  # "1 d ", "2 h "
    r'^\s*\d+\s*(?:día|días|hora|horas|minuto|minutos|segundo|segundos)\s*$',
    r'^\s*\d+\s*(?:Me gusta|like|likes)\s*$',
    r'^\s*Responder\s*$',
    r'^\s*Reply\s*$',
    r'^\s*·\s*$',              # El punto medio de Facebook/Instagram
    r'^\s*\d+\s*$',            # Números sueltos (reacciones)
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PATTERNS_METADATA]


def limpiar_linea(linea: str) -> str:
    """Limpia una línea individual eliminando metadata conocida."""
    linea = linea.strip()
    for pattern in COMPILED_PATTERNS:
        if pattern.match(linea):
            return ""
    return linea


def detectar_red_social(texto: str) -> str:
    """Detecta la red social de origen basándose en patrones."""
    texto_lower = texto.lower()
    
    instagram_signals = [r'\d+\s*[dhms]\s*\d+\s*me gusta\s*responder', r'\d+\s*me gusta\s*responder']
    for pattern in instagram_signals:
        if re.search(pattern, texto_lower):
            return "instagram"
            
    facebook_signals = [r'\d+\s*(?:día|días|hora|horas)\s*\n\s*responder', r'ver más']
    for pattern in facebook_signals:
        if re.search(pattern, texto_lower):
            return "facebook"
            
    x_signals = [r'\d+\s*(?:Retweets|retweets|Me gusta|me gusta)', r'·\s*\d+\s*[dhms]']
    for pattern in x_signals:
        if re.search(pattern, texto):
            return "x"
            
    return "desconocido"


def es_emoji_problematico(char: str) -> bool:
    """Detecta emojis que pueden romper JSON (opcional, ya que Python maneja bien UTF-8, pero lo mantenemos por seguridad)."""
    code = ord(char)
    return (
        0x1F600 <= code <= 0x1F64F or
        0x1F300 <= code <= 0x1F5FF or
        0x1F680 <= code <= 0x1F6FF or
        0x1F900 <= code <= 0x1F9FF or
        0x2600 <= code <= 0x26FF or
        0x2700 <= code <= 0x27BF
    )


def sanitizar_para_json(texto: str) -> str:
    """Sanitiza texto para que sea 100% seguro en JSON."""
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    
    # Opcional: reemplazar emojis por [emoji] si causan problemas, 
    # pero hoy en día json.dumps con ensure_ascii=False los maneja perfecto.
    # Lo dejamos limpio de caracteres de control invisibles.
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    return texto.strip()


def limpiar_comentarios(texto_crudo: str) -> Tuple[List[dict], str]:
    """
    Limpia comentarios de redes sociales y los estructura en pares (usuario, texto).
    """
    red_social = detectar_red_social(texto_crudo)
    
    # 1. Dividir en líneas y pre-limpiar
    lineas = texto_crudo.split('\n')
    lineas_limpias = []
    
    for linea in lineas:
        # Eliminar "Ver más" / "Ver menos" del final de la línea ANTES de evaluar
        linea = re.sub(r'\s*(?:Ver más|Ver menos|See more|See less)\s*$', '', linea, flags=re.IGNORECASE)
        linea_limpia = limpiar_linea(linea).strip()
        if linea_limpia:
            lineas_limpias.append(linea_limpia)

    comentarios = []
    i = 0
    
    while i < len(lineas_limpias):
        linea_actual = lineas_limpias[i]
        
        # Heurística mejorada para nombre de usuario:
        # - 1 a 4 palabras
        # - Longitud razonable (< 40 chars)
        # - No termina en puntuación fuerte
        # - No es una palabra de metadata que se escapó
        palabras = linea_actual.split()
        es_posible_usuario = (
            1 <= len(palabras) <= 4 and
            len(linea_actual) < 40 and
            not re.search(r'[.!?,;:]$', linea_actual) and
            not any(es_emoji_problematico(c) for c in linea_actual) and
            linea_actual.lower() not in ['responder', 'reply', 'me gusta', 'like', 'likes']
        )
        
        if es_posible_usuario and i + 1 < len(lineas_limpias):
            usuario = linea_actual
            i += 1
            
            # Acumular todas las líneas siguientes que pertenecen a este comentario
            lineas_comentario = []
            while i < len(lineas_limpias):
                siguiente = lineas_limpias[i]
                palabras_sig = siguiente.split()
                
                # Si la siguiente línea parece OTRO usuario, paramos de acumular
                if (1 <= len(palabras_sig) <= 4 and 
                    len(siguiente) < 40 and
                    not re.search(r'[.!?,;:]$', siguiente) and
                    not any(es_emoji_problematico(c) for c in siguiente) and
                    siguiente.lower() not in ['responder', 'reply', 'me gusta', 'like', 'likes']):
                    break
                
                # Si es metadata suelta, la saltamos
                if siguiente.lower() in ['responder', 'reply', 'me gusta', 'like', 'likes']:
                    i += 1
                    continue
                    
                lineas_comentario.append(siguiente)
                i += 1
            
            if lineas_comentario:
                # Unir líneas del comentario y limpiar espacios extra
                texto_comentario = re.sub(r'\s+', ' ', ' '.join(lineas_comentario)).strip()
                
                # Solo guardar si el comentario tiene sustancia (más de 10 caracteres)
                if len(texto_comentario) > 10:
                    comentarios.append({
                        "usuario": usuario,
                        "texto": texto_comentario,
                    })
        else:
            # Fallback: Si no parece usuario, podría ser un comentario suelto (ej: si el nombre no se copió)
            if len(linea_actual) > 15 and linea_actual.lower() not in ['responder', 'reply']:
                comentarios.append({
                    "usuario": "Anónimo",
                    "texto": linea_actual,
                })
            i += 1

    # Eliminar duplicados exactos de texto
    vistos = set()
    comentarios_unicos = []
    for c in comentarios:
        texto_key = c["texto"].lower().strip()
        if texto_key not in vistos and len(texto_key) > 10:
            vistos.add(texto_key)
            comentarios_unicos.append(c)

    # Sanitizar para JSON
    for c in comentarios_unicos:
        c["texto"] = sanitizar_para_json(c["texto"])
        c["usuario"] = sanitizar_para_json(c["usuario"])

    return comentarios_unicos, red_social


def formatear_comentarios_para_prompt(comentarios: List[dict]) -> str:
    """Formatea comentarios para enviar al prompt del LLM."""
    lineas = []
    for i, c in enumerate(comentarios, 1):
        lineas.append(f"{i}. [{c['usuario']}]: {c['texto']}")
    return '\n'.join(lineas)