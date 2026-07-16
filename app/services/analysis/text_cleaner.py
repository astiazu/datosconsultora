# app/services/analysis/text_cleaner.py
"""
Limpieza inteligente de comentarios copiados de redes sociales.
Detecta automáticamente la red social (X, Facebook, Instagram) y elimina:
- Metadata (timestamps, likes, botones)
- Patrones repetidos
- Comentarios duplicados
- Caracteres problemáticos para JSON
"""
import re
from typing import List, Tuple


# Patrones de metadata por red social
PATTERNS_METADATA = [
    # Timestamps: "1 d", "2 h", "30 m", "1 día", "2 horas", "1d", "2h"
    r'^\s*\d+\s*[dhms](?:\s|$)',
    r'^\s*\d+\s*(?:día|días|hora|horas|minuto|minutos|segundo|segundos)\s*$',
    # Likes: "1 Me gusta", "2 Me gusta", "1 like"
    r'^\s*\d+\s*(?:Me gusta|like|likes)\s*$',
    # Botones
    r'^\s*Responder\s*$',
    r'^\s*Ver más\s*$',
    r'^\s*Ver menos\s*$',
    r'^\s*Traducir\s*$',
    # Combinaciones comunes en Instagram
    r'^\s*\d+\s*[dhms]\s*\d+\s*(?:Me gusta|like)\s*Responder\s*$',
    r'^\s*\d+\s*[dhms]\s*Responder\s*$',
    # X/Twitter: "·", separadores
    r'^\s*·\s*$',
    # Números sueltos (reacciones)
    r'^\s*\d+\s*$',
]

# Compilar patrones una sola vez
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PATTERNS_METADATA]


def limpiar_linea(linea: str) -> str:
    """Limpia una línea individual eliminando metadata."""
    linea = linea.strip()
    
    # Eliminar líneas que son solo metadata
    for pattern in COMPILED_PATTERNS:
        if pattern.match(linea):
            return ""
    
    return linea


def detectar_red_social(texto: str) -> str:
    """Detecta la red social de origen basándose en patrones."""
    texto_lower = texto.lower()
    
    # Patrones específicos de Instagram
    instagram_signals = [
        r'\d+\s*[dhms]\s*\d+\s*me gusta\s*responder',
        r'\d+\s*me gusta\s*responder',
    ]
    for pattern in instagram_signals:
        if re.search(pattern, texto_lower):
            return "instagram"
    
    # Patrones de Facebook
    facebook_signals = [
        r'\d+\s*(?:día|días|hora|horas)\s*\n\s*responder',
        r'ver más',
    ]
    for pattern in facebook_signals:
        if re.search(pattern, texto_lower):
            return "facebook"
    
    # Patrones de X/Twitter
    x_signals = [
        r'\d+\s*(?:Retweets|retweets|Me gusta|me gusta)',
        r'·\s*\d+\s*[dhms]',
    ]
    for pattern in x_signals:
        if re.search(pattern, texto):
            return "x"
    
    return "desconocido"


def es_emoji_problematico(char: str) -> bool:
    """Detecta emojis que pueden romper JSON."""
    code = ord(char)
    # Rango de emojis problemáticos
    return (
        0x1F600 <= code <= 0x1F64F or  # Emoticonos
        0x1F300 <= code <= 0x1F5FF or  # Símbolos misc
        0x1F680 <= code <= 0x1F6FF or  # Transporte
        0x1F900 <= code <= 0x1F9FF or  # Supplemental
        0x2600 <= code <= 0x26FF or    # Misc symbols
        0x2700 <= code <= 0x27BF       # Dingbats
    )


def sanitizar_para_json(texto: str) -> str:
    """
    Sanitiza texto para que sea seguro en JSON.
    - Escapa comillas y caracteres especiales
    - Elimina emojis problemáticos (los reemplaza con descripción)
    - Normaliza saltos de línea
    """
    # Normalizar saltos de línea
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    
    # Reemplazar emojis por [emoji] para evitar problemas
    resultado = []
    for char in texto:
        if es_emoji_problematico(char):
            resultado.append('[emoji]')
        else:
            resultado.append(char)
    
    texto = ''.join(resultado)
    
    # Eliminar caracteres de control excepto saltos de línea
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    
    return texto


def limpiar_comentarios(texto_crudo: str) -> Tuple[List[dict], str]:
    """
    Limpia comentarios de redes sociales y los estructura.
    
    :param texto_crudo: Texto copiado de la red social
    :return: (lista_de_comentarios, red_social_detectada)
             Cada comentario es {"usuario": str, "texto": str}
    """
    red_social = detectar_red_social(texto_crudo)
    
    # Dividir en líneas
    lineas = texto_crudo.split('\n')
    
    # Limpiar cada línea
    lineas_limpias = []
    for linea in lineas:
        linea_limpia = limpiar_linea(linea)
        if linea_limpia:
            lineas_limpias.append(linea_limpia)
    
    # Estructurar en pares (usuario, comentario)
    comentarios = []
    i = 0
    while i < len(lineas_limpias):
        # Heurística: un nombre de usuario suele ser corto (1-3 palabras, sin signos de puntuación fuertes)
        linea_actual = lineas_limpias[i].strip()
        
        if not linea_actual:
            i += 1
            continue
        
        # Detectar si es un nombre de usuario
        es_nombre_usuario = False
        
        # Nombres de usuario suelen:
        # - Tener 1-4 palabras
        # - No terminar en punto, coma, signo de exclamación/interrogación
        # - No contener emojis
        # - Ser más cortos que el comentario típico
        
        palabras = linea_actual.split()
        if 1 <= len(palabras) <= 4:
            # No tiene puntuación fuerte al final
            if not linea_actual[-1] in '.!?,;:':
                # No es muy largo
                if len(linea_actual) < 50:
                    # No tiene emojis
                    if not any(es_emoji_problematico(c) for c in linea_actual):
                        # No parece un comentario (no tiene verbos comunes)
                        es_nombre_usuario = True
        
        if es_nombre_usuario and i + 1 < len(lineas_limpias):
            # El siguiente bloque es el comentario
            usuario = linea_actual
            i += 1
            
            # Recopilar líneas del comentario hasta el siguiente usuario o fin
            lineas_comentario = []
            while i < len(lineas_limpias):
                siguiente = lineas_limpias[i].strip()
                
                # Verificar si es el siguiente usuario
                palabras_sig = siguiente.split()
                if (1 <= len(palabras_sig) <= 4 and 
                    not siguiente[-1] in '.!?,;:' and
                    len(siguiente) < 50 and
                    not any(es_emoji_problematico(c) for c in siguiente)):
                    break
                
                lineas_comentario.append(siguiente)
                i += 1
            
            if lineas_comentario:
                texto_comentario = ' '.join(lineas_comentario)
                comentarios.append({
                    "usuario": usuario,
                    "texto": texto_comentario,
                })
        else:
            # Si no es nombre de usuario, tratar como comentario suelto
            if len(linea_actual) > 10:  # Solo si es un texto sustancial
                comentarios.append({
                    "usuario": "Anónimo",
                    "texto": linea_actual,
                })
            i += 1
    
    # Eliminar duplicados (mismo texto)
    vistos = set()
    comentarios_unicos = []
    for c in comentarios:
        texto_key = c["texto"].lower().strip()
        if texto_key not in vistos and len(texto_key) > 3:
            vistos.add(texto_key)
            comentarios_unicos.append(c)
    
    # Sanitizar para JSON
    for c in comentarios_unicos:
        c["texto"] = sanitizar_para_json(c["texto"])
        c["usuario"] = sanitizar_para_json(c["usuario"])
    
    return comentarios_unicos, red_social


def formatear_comentarios_para_prompt(comentarios: List[dict]) -> str:
    """
    Formatea comentarios para enviar al prompt del LLM.
    Formato numerado limpio.
    """
    lineas = []
    for i, c in enumerate(comentarios, 1):
        lineas.append(f"{i}. [{c['usuario']}]: {c['texto']}")
    return '\n'.join(lineas)