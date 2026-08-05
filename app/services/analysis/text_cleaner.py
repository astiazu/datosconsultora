# app/services/analysis/text_cleaner.py
"""
Limpieza inteligente de comentarios copiados de redes sociales, chats y transcripciones.
Detecta automáticamente la fuente y extrae pares (Usuario, Comentario).

Fuentes soportadas:
- facebook
- instagram
- x (twitter)
- whatsapp (chat exportado)
- transcripcion (audio/video o texto continuo sin estructura)
"""
import re
from typing import List, Tuple

# Patrones de metadata que deben eliminarse por completo
PATTERNS_METADATA = [
    r'^\s*\d+\s*[dhms]\s*$',  # "1 d", "2 h"
    r'^\s*\d+\s*(?:día|días|hora|horas|minuto|minutos|segundo|segundos|semana|semanas)\s*$',
    r'^\s*\d+\s*(?:me\s*gusta|likes?)\s*$',
    r'^\s*(?:me\s*gusta|likes?|responder|reply|compartir|guardar|reenviar|ver\s*traducción|retweet|repost)\s*$',
    r'^\s*me\s*gusta\s+responder\s*$',
    r'^\s*\d+\s*me\s*gusta\s+responder\s*$',
    r'^\s*·\s*$',
    r'^\s*·\s*\d+\s*[dhms]\s*$',
    r'^\s*\d+\s*$',  # Números sueltos (reacciones)
    # X / Twitter
    r'^\s*\d+\s*(?:retweets?|reposts?)\s*$',
    r'^\s*\d+\s*(?:me\s*gusta|likes?)\s*·\s*\d+\s*(?:retweets?|reposts?)\s*$',
    # Facebook
    r'^\s*(?:ver\s*más|ver\s*menos|see\s*more|see\s*less)\s*$',
    r'^\s*(?:ocultar\s*respuestas|ver\s*(?:\d+\s*)?comentarios?\s*más)\s*$',
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PATTERNS_METADATA]

# Línea de WhatsApp: "10/5/26 14:32 - José: texto" o "[10/5/26, 14:32] José: texto"
WHATSAPP_LINE = re.compile(
    r'^\s*\[?'
    r'\d{1,2}[/.]\d{1,2}[/.]\d{2,4}'          # fecha
    r'[,\s]+'
    r'\d{1,2}[:.]\d{2}(?:[:.]\d{2})?'         # hora
    r'(?:\s*[ap]\.?\s?m\.?)?'                 # am/pm
    r'\]?\s*[-–—]?\s*'                        # separador
    r'([^:]+?)\s*:\s*(.*)$',                  # usuario: texto
    re.IGNORECASE,
)

WHATSAPP_SYSTEM = re.compile(
    r'(?:cifrad|end-to-end|security\s+code|se\s+unió|creaste|saliste|eliminaste|'
    r'añadiste|cambiaste|bloqueaste|los\s+mensajes|llamadas?\s+cifradas|'
    r'imagen\s+omitida|video\s+omitido|audio\s+omitido|documento\s+omitido|'
    r'sticker|llamada\s+(?:de\s+)?(?:voz|video))',
    re.IGNORECASE,
)


def limpiar_linea(linea: str) -> str:
    """Limpia una línea individual eliminando metadata conocida."""
    linea = linea.strip()
    for pattern in COMPILED_PATTERNS:
        if pattern.match(linea):
            return ""
    return linea


def detectar_red_social(texto: str) -> str:
    """Detecta la fuente de origen basándose en patrones."""
    # 1) WhatsApp (chat exportado) - se chequea primero
    whatsapp_signals = [
        r'\d{1,2}[/.]\d{1,2}[/.]\d{2,4}[,\s]+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?\s*(?:[ap]\.?\s?m\.?)?\s*[-–—]\s*[^:\n]+:',
        r'\[\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\]',
    ]
    for pattern in whatsapp_signals:
        if re.search(pattern, texto, re.IGNORECASE):
            return "whatsapp"

    # 2) X (Twitter)
    x_signals = [
        r'\d+\s*(?:retweets?|reposts?)',
        r'@\w+\s*·\s*\d+\s*[dhms]\b',
    ]
    for pattern in x_signals:
        if re.search(pattern, texto, re.IGNORECASE):
            return "x"

    # 3) Instagram: "Me gusta Responder" en la MISMA línea (espacio horizontal)
    instagram_signals = [
        r'\d+\s*[dhms]\s*\n\s*\d+\s*me\s*gusta',
        r'\d+\s*me\s*gusta\s*\n\s*responder',
        r'me\s*gusta[ \t]+responder',  # ← [ \t] NO cruza saltos de línea
    ]
    for pattern in instagram_signals:
        if re.search(pattern, texto, re.IGNORECASE):
            return "instagram"

    # 4) Facebook: "Me gusta" y "Responder" en líneas SEPARADAS, o "· 2 h"
    facebook_signals = [
        r'ver\s*más',
        r'·\s*\d+\s*[dhms]\b',              # "José Pérez · 2 h"
        r'me\s*gusta\s*\n\s*responder',     # ← líneas separadas
    ]
    for pattern in facebook_signals:
        if re.search(pattern, texto, re.IGNORECASE):
            return "facebook"

    return "desconocido"


def es_emoji_problematico(char: str) -> bool:
    """Detecta emojis que pueden romper JSON (seguridad)."""
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
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    return texto.strip()


def _limpiar_nombre_usuario(nombre: str) -> str:
    """Elimina sufijos de tiempo del nombre de usuario ('· 3h', '2d', 'hace 2 horas')."""
    nombre = nombre.strip()
    nombre = re.sub(r'\s*[·|]\s*\d+\s*[dhms]\s*$', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\s*\d+\s*[dhms]\s*$', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\s*hace\s+\d+\s*(?:días?|horas?|minutos?|semanas?|meses?)\s*$', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\s*(?:día|días|hora|horas|minuto|minutos)\s*$', '', nombre, flags=re.IGNORECASE)
    return nombre.strip() or "Anónimo"


def _es_posible_usuario(linea: str) -> bool:
    """Heurística para detectar una línea que es un nombre de usuario.
    Ignora los sufijos de tiempo ('· 2 h', '2 d', 'hace 2 horas') ANTES de evaluar."""
    base = linea.strip()
    # "José Pérez · 2 h" → "José Pérez" | "usuario1 2d" → "usuario1" | "@user · 3h" → "@user"
    base = re.sub(r'\s*[·|]?\s*\d+\s*[dhms]\s*$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'\s*hace\s+\d+\s*(?:días?|horas?|minutos?|semanas?|meses?)\s*$', '', base, flags=re.IGNORECASE)
    base = base.strip()

    palabras = base.split()
    return (
        1 <= len(palabras) <= 4 and
        len(base) < 40 and
        not re.search(r'[.!?,;:]$', base) and
        not any(es_emoji_problematico(c) for c in base) and
        base.lower() not in ['responder', 'reply', 'me gusta', 'like', 'likes']
    )

def _tiene_estructura_de_redes(texto: str) -> bool:
    """True si el texto parece copiado de una red social (usuarios/metadata)."""
    for linea in texto.split('\n'):
        l = linea.strip()
        if not l:
            continue
        if any(p.match(l) for p in COMPILED_PATTERNS):
            return True
        if _es_posible_usuario(l):
            return True
    return False


def _parsear_whatsapp(texto_crudo: str) -> List[dict]:
    """Parsea un chat exportado de WhatsApp (con timestamps y multilinea)."""
    comentarios = []
    actual = None
    for linea in texto_crudo.split('\n'):
        linea = linea.strip()
        if not linea:
            continue
        m = WHATSAPP_LINE.match(linea)
        if m:
            usuario = m.group(1).strip()
            texto = m.group(2).strip()
            # Saltear líneas de sistema que tengan formato de mensaje
            if WHATSAPP_SYSTEM.search(usuario):
                continue
            if actual:
                comentarios.append(actual)
            actual = {"usuario": usuario, "texto": texto}
        else:
            # Línea de sistema suelta al inicio → ignorar
            if actual is None and WHATSAPP_SYSTEM.search(linea):
                continue
            # Continuación de un mensaje multilinea
            if actual:
                actual["texto"] += " " + linea
    if actual:
        comentarios.append(actual)
    return comentarios


def _split_por_frases(texto: str, max_len: int) -> List[str]:
    """Divide un texto largo en fragmentos de hasta max_len cortando en frases."""
    frases = re.split(r'(?<=[.!?])\s+', texto)
    chunks = []
    actual = ""
    for frase in frases:
        if not actual or len(actual) + len(frase) + 1 <= max_len:
            actual = (actual + " " + frase).strip()
        else:
            chunks.append(actual)
            actual = frase
    if actual:
        chunks.append(actual)
    return chunks


def _parsear_continuo(texto_crudo: str) -> List[dict]:
    """Divide texto continuo (transcripción de audio/video) en fragmentos analizables."""
    texto = sanitizar_para_json(texto_crudo)
    parrafos = [p.strip() for p in re.split(r'\n\s*\n', texto) if p.strip()]
    if not parrafos and texto.strip():
        parrafos = [texto.strip()]

    fragmentos = []
    for parrafo in parrafos:
        if len(parrafo) <= 600:
            fragmentos.append(parrafo)
        else:
            fragmentos.extend(_split_por_frases(parrafo, 600))

    comentarios = []
    for idx, frag in enumerate(fragmentos, 1):
        frag = re.sub(r'\s+', ' ', frag).strip()
        if len(frag) > 10:
            comentarios.append({"usuario": f"Fragmento {idx}", "texto": frag})
    return comentarios


def _parsear_redes(texto_crudo: str) -> List[dict]:
    """Parser original para Facebook/Instagram/X (usuario en línea propia)."""
    lineas = texto_crudo.split('\n')
    lineas_limpias = []
    for linea in lineas:
        linea = re.sub(r'\s*(?:Ver más|Ver menos|See more|See less)\s*$', '', linea, flags=re.IGNORECASE)
        linea_limpia = limpiar_linea(linea).strip()
        if linea_limpia:
            lineas_limpias.append(linea_limpia)

    comentarios = []
    i = 0
    while i < len(lineas_limpias):
        linea_actual = lineas_limpias[i]

        if _es_posible_usuario(linea_actual) and i + 1 < len(lineas_limpias):
            usuario = _limpiar_nombre_usuario(linea_actual)
            i += 1
            lineas_comentario = []
            while i < len(lineas_limpias):
                siguiente = lineas_limpias[i]
                # Si parece otro usuario, paramos de acumular
                if _es_posible_usuario(siguiente):
                    break
                # Si es metadata suelta, la saltamos
                if any(p.match(siguiente) for p in COMPILED_PATTERNS):
                    i += 1
                    continue
                lineas_comentario.append(siguiente)
                i += 1
            if lineas_comentario:
                texto_comentario = re.sub(r'\s+', ' ', ' '.join(lineas_comentario)).strip()
                if len(texto_comentario) > 10:
                    comentarios.append({"usuario": usuario, "texto": texto_comentario})
        else:
            # Fallback: comentario suelto sin nombre
            if len(linea_actual) > 15 and linea_actual.lower() not in ['responder', 'reply']:
                comentarios.append({"usuario": "Anónimo", "texto": linea_actual})
            i += 1

    return comentarios


def _dedup_y_sanitizar(comentarios: List[dict]) -> List[dict]:
    """Elimina duplicados exactos y sanitiza para JSON."""
    vistos = set()
    unicos = []
    for c in comentarios:
        texto_key = c["texto"].lower().strip()
        if texto_key not in vistos and len(texto_key) > 10:
            vistos.add(texto_key)
            unicos.append(c)
    for c in unicos:
        c["texto"] = sanitizar_para_json(c["texto"])
        c["usuario"] = sanitizar_para_json(c["usuario"])
    return unicos


def limpiar_comentarios(texto_crudo: str) -> Tuple[List[dict], str]:
    """
    Limpia comentarios y los estructura en pares (usuario, texto).
    Devuelve (comentarios, red_social).
    """
    red_social = detectar_red_social(texto_crudo)

    if red_social == "whatsapp":
        comentarios = _parsear_whatsapp(texto_crudo)
    elif red_social == "desconocido" and not _tiene_estructura_de_redes(texto_crudo):
        # Texto continuo sin estructura → transcripción de audio/video
        comentarios = _parsear_continuo(texto_crudo)
        if comentarios:
            red_social = "transcripcion"
    else:
        comentarios = _parsear_redes(texto_crudo)

    return _dedup_y_sanitizar(comentarios), red_social


def formatear_comentarios_para_prompt(comentarios: List[dict]) -> str:
    """Formatea comentarios para enviar al prompt del LLM."""
    lineas = []
    for i, c in enumerate(comentarios, 1):
        lineas.append(f"{i}. [{c['usuario']}]: {c['texto']}")
    return '\n'.join(lineas)