# worker/scraper_worker.py
"""
Worker de extracción de comentarios (Instagram vía instaloader).
Una pasada:  python -m worker.scraper_worker
En loop:     python -m worker.scraper_worker --loop
"""
import random
import sys
import time
from datetime import datetime, timedelta

from app import create_app, db
from app.models import ExtraccionJob, SesionPlataforma
from app.services.scraper.proveedores import instagram_instaloader as ig
from app.utils.datetime_utils import utc_now


def procesar_job(job: ExtraccionJob) -> None:
    sesion = SesionPlataforma.query.filter_by(
        user_id=job.user_id, plataforma=job.plataforma, expirada=False
    ).first()
    if not sesion:
        job.estado = "fallido"
        job.error = "No hay sesión de Instagram conectada."
        db.session.commit()
        return

    job.estado = "progreso"
    job.actualizado = utc_now()
    db.session.commit()

    def on_checkpoint(chk, total):
        job.set_checkpoint(chk)
        job.total_extraido = total
        job.actualizado = utc_now()
        db.session.commit()

    try:
        resultado = ig.extraer(sesion.storage_state_json, job.url, job.checkpoint(), on_checkpoint)
    except ig.RateLimitDetectado as exc:
        job.estado = "pausa_rate_limit"
        job.proximo_intento = utc_now() + timedelta(minutes=random.randint(5, 10))
        job.error = str(exc)[:400]
        db.session.commit()
        print(f"[job {job.id}] Rate limit. Pausa hasta {job.proximo_intento}.")
        return
    except ig.SesionInvalida as exc:
        sesion.expirada = True
        job.estado = "fallido"
        job.error = "Sesión expirada o inválida. Subí una nueva sesión."
        db.session.commit()
        print(f"[job {job.id}] Sesión inválida: {exc}")
        return
    except Exception as exc:
        job.estado = "fallido"
        job.error = str(exc)[:400]
        db.session.commit()
        print(f"[job {job.id}] ERROR: {exc}")
        return

    comentarios = resultado["comentarios"]
    if not comentarios:
        job.estado = "fallido"
        job.error = "La publicación no tiene comentarios visibles."
        db.session.commit()
        return

    from app.mic.builders.conversation_builder import ConversationBuilder
    from app.mic.domain.enums import SourceType
    from app.services.plata.conversation_repository import ConversationRepository

    builder = ConversationBuilder()
    builder.create(
        conversation_id=f"ig_job_{job.id}",
        source=SourceType.INSTAGRAM,
        title=f"Instagram: {job.url[:120]}",
        created_at=utc_now(),
    )
    vistos = set()
    for c in comentarios:
        if c["usuario"] not in vistos:
            builder.add_participant(participant_id=c["usuario"], display_name=c["usuario"])
            vistos.add(c["usuario"])
        builder.add_message(
            message_id=c["id"],
            participant_id=c["usuario"],
            text=c["texto"],
            created_at=datetime.fromisoformat(c["fecha"]),
            reactions=c.get("likes", 0),
        )
    res = builder.build()
    if not res.success:
        job.estado = "fallido"
        job.error = "; ".join(res.errors)[:400]
        db.session.commit()
        return

    record = ConversationRepository().guardar(job.user_id, res.conversation, contexto=job.contexto)
    job.conversation_record_id = record.id
    job.estado = "completado"
    job.total_extraido = len(comentarios)
    job.error = None
    job.actualizado = utc_now()
    db.session.commit()
    print(f"[job {job.id}] Completado: {len(comentarios)} comentarios.")


def pendientes():
    ahora = utc_now()
    return ExtraccionJob.query.filter(
        ExtraccionJob.estado.in_(["cola", "progreso", "pausa_rate_limit"]),
        db.or_(ExtraccionJob.proximo_intento == None, ExtraccionJob.proximo_intento <= ahora),
    ).order_by(ExtraccionJob.creado).all()


def main() -> None:
    app = create_app()
    loop = "--loop" in sys.argv
    with app.app_context():
        while True:
            for job in pendientes():
                print(f"[job {job.id}] Procesando ({job.estado})...")
                procesar_job(job)
            if not loop:
                break
            time.sleep(30)


if __name__ == "__main__":
    sys.exit(main() or 0)
