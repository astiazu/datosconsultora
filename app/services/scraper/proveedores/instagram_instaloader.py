# app/services/scraper/proveedores/instagram_instaloader.py
"""
Conector Instagram vía instaloader (API GraphQL privada, sin navegador).
Aplica ritmo humano, checkpoints y detección de bloqueos.
"""
import base64
import json
import os
import random
import re
import tempfile
import time

import instaloader
from instaloader.exceptions import (
    ConnectionException,
    LoginRequiredException,
)

necesita_sesion = True

# ---------- Política de ritmo (anti-bloqueo) ----------
DELAY_COMENTARIO = (
    float(os.environ.get("SCRAPER_DELAY_MIN", "2")),
    float(os.environ.get("SCRAPER_DELAY_MAX", "7")),
)
PAUSA_MEDIA_EVERY = (20, 40)
PAUSA_MEDIA_SEGS = (60, 120)
PAUSA_LARGA_EVERY = (200, 300)
PAUSA_LARGA_SEGS = (300, 600)
CHECKPOINT_EVERY = 50
MAX_COMENTARIOS_POR_JOB = int(os.environ.get("SCRAPER_MAX_COMENTARIOS", "500"))


class RateLimitDetectado(Exception):
    """429 / rate limit: pausar y reintentar más tarde."""

class SesionInvalida(Exception):
    """Sesión expirada o login requerido: avisar al usuario."""

class BloqueoDetectado(Exception):
    """Captcha / bloqueo duro: detener sin reintento automático."""


def extraer_shortcode(url: str) -> str:
    m = re.search(r"(?:/p/|/reel/|/tv/)([A-Za-z0-9_-]+)", url)
    if not m:
        raise ValueError("URL de Instagram no válida (se espera /p/... o /reel/...).")
    return m.group(1)


def _cargar_loader(sesion_b64: str) -> instaloader.Instaloader:
    """Carga una sesión de instaloader desde su representación en base64."""
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
    )
    # Decodificar base64 a bytes pickle
    pickle_bytes = base64.b64decode(sesion_b64.encode("ascii"))

    # Escribir a archivo temporal (instaloader lo requiere así)
    tmp = tempfile.NamedTemporaryFile("wb", suffix=".pkl", delete=False)
    tmp.write(pickle_bytes)
    tmp.close()

    try:
        # load_session_from_file usa pickle internamente
        loader.load_session_from_file("", tmp.name)
    finally:
        os.unlink(tmp.name)
    return loader


def _es_rate_limit(mensaje: str) -> bool:
    """Detecta señales de rate limit / throttle en mensajes de error."""
    m = mensaje.lower()
    return any(k in m for k in (
        "429", "rate", "too many", "throttle",
        "try again later", "temporarily", "blocked",
    ))


def _es_captcha_o_bloqueo(mensaje: str) -> bool:
    """Detecta captcha, challenge o bloqueo duro."""
    m = mensaje.lower()
    return any(k in m for k in (
        "captcha", "challenge", "checkpoint",
        "suspicious", "verify your identity", "security code",
    ))


def extraer(sesion_b64, url, checkpoint=None, on_checkpoint=None) -> dict:
    """
    Extrae comentarios con ritmo humano y reanudación.
    checkpoint: {"ultimo_id": str, "comentarios": [...]} de una corrida anterior.
    on_checkpoint(chk, total): callback para persistir progreso.
    """
    checkpoint = checkpoint or {}
    shortcode = extraer_shortcode(url)
    loader = _cargar_loader(sesion_b64)

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        comentarios = list(checkpoint.get("comentarios", []))
        vistos = {c["id"] for c in comentarios}
        ultimo_id = checkpoint.get("ultimo_id")
        saltando = ultimo_id is not None

        nuevos = 0
        contados = 0
        prox_media = contados + random.randint(*PAUSA_MEDIA_EVERY)
        prox_larga = contados + random.randint(*PAUSA_LARGA_EVERY)

        for comment in post.get_comments():
            cid = str(comment.id)

            # Reanudación: saltear hasta el último ya procesado
            if saltando:
                if cid == ultimo_id:
                    saltando = False
                continue
            if cid in vistos:
                continue

            comentarios.append({
                "id": cid,
                "usuario": comment.owner.username,
                "texto": comment.text,
                "fecha": comment.created_at_utc.isoformat(),
                "likes": comment.likes_count,
            })
            vistos.add(cid)
            ultimo_id = cid
            nuevos += 1
            contados += 1

            # Checkpoint cada N nuevos
            if nuevos % CHECKPOINT_EVERY == 0 and on_checkpoint:
                on_checkpoint({"ultimo_id": ultimo_id, "comentarios": comentarios}, len(comentarios))

            if len(comentarios) >= MAX_COMENTARIOS_POR_JOB:
                break

            # Ritmo humano con variación
            if contados >= prox_larga:
                time.sleep(random.uniform(*PAUSA_LARGA_SEGS))
                prox_larga = contados + random.randint(*PAUSA_LARGA_EVERY)
            elif contados >= prox_media:
                time.sleep(random.uniform(*PAUSA_MEDIA_SEGS))
                prox_media = contados + random.randint(*PAUSA_MEDIA_EVERY)
            else:
                time.sleep(random.uniform(*DELAY_COMENTARIO))

        chk = {"ultimo_id": ultimo_id, "comentarios": comentarios}
        if on_checkpoint:
            on_checkpoint(chk, len(comentarios))
        return {"comentarios": comentarios, "checkpoint": chk}

    except LoginRequiredException as exc:
        raise SesionInvalida(str(exc)) from exc

    except ConnectionException as exc:
        msg = str(exc)
        if _es_captcha_o_bloqueo(msg):
            raise BloqueoDetectado(msg) from exc
        if _es_rate_limit(msg):
            raise RateLimitDetectado(msg) from exc
        raise BloqueoDetectado(msg) from exc

    except Exception as exc:
        msg = str(exc)
        t = type(exc).__name__
        # instaloader lanza RuntimeError/ValueError para algunos bloqueos
        if _es_captcha_o_bloqueo(msg) or "login" in msg.lower():
            raise BloqueoDetectado(f"{t}: {msg}") from exc
        if _es_rate_limit(msg):
            raise RateLimitDetectado(f"{t}: {msg}") from exc
        # Si es genérico, lo propagamos como bloqueo para que el worker lo maneje con cautela
        raise BloqueoDetectado(f"{t}: {msg}") from exc