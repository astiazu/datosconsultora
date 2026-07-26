# worker/monitor_worker.py
"""
Worker de chequeo periodico de expedientes, para correr como proceso aparte
(por ejemplo un Render Cron Job cada X horas), NO como parte del servidor
web de Flask. Playwright con un Chrome real es demasiado pesado y lento
para el ciclo request/response de un web server.

Uso:
    python -m worker.monitor_worker

Requiere las mismas variables de entorno que la app (DATABASE_URL, MAIL_*),
mas playwright y su Chrome instalados en el entorno donde corra este
worker (que puede ser un servicio separado del web app en Render).

Solo procesa jurisdicciones con soporta_automatizacion=True (hoy: MEV-SCBA).
Las que requieren captcha por busqueda (ej Cordoba) se saltean: esas las
revisa el usuario a mano desde el link que tiene en su panel.
"""

import sys

from playwright.sync_api import sync_playwright

from app import create_app, db, mail
from app.models import ExpedienteMonitoreado, SesionJurisdiccion
from app.services.agentes.jurisdicciones import obtener_jurisdiccion
from app.services.agentes.monitor_service import (
    obtener_estado_guardado,
    guardar_o_actualizar_estado,
    comparar_con_guardado,
)


def obtener_proveedor(nombre_jurisdiccion: str):
    import importlib
    return importlib.import_module(f"app.services.agentes.proveedores.{nombre_jurisdiccion}")


def enviar_aviso(destinatario: str, asunto: str, cuerpo: str) -> None:
    from flask_mail import Message
    msg = Message(subject=asunto, recipients=[destinatario], body=cuerpo)
    mail.send(msg)


def procesar_expediente(browser, expediente: ExpedienteMonitoreado) -> None:
    jurisdiccion = obtener_jurisdiccion(expediente.jurisdiccion)
    if not jurisdiccion or not jurisdiccion["soporta_automatizacion"]:
        return  # ej: cordoba_sac, se salteA

    sesion = None
    if jurisdiccion["necesita_login"]:
        sesion = SesionJurisdiccion.query.filter_by(
            user_id=expediente.user_id, jurisdiccion=expediente.jurisdiccion
        ).first()
        if not sesion or sesion.expirada:
            print(f"[{expediente.id}] Sin sesion valida para {expediente.jurisdiccion}, se saltea.")
            return

    proveedor = obtener_proveedor(expediente.jurisdiccion)

    kwargs = {"locale": "es-AR", "viewport": None}
    archivo_temporal_sesion = None
    if sesion:
        # Playwright pide un path para storage_state, asi que volcamos el
        # contenido guardado en la base a un archivo temporal.
        import tempfile
        archivo_temporal_sesion = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        archivo_temporal_sesion.write(sesion.storage_state_json)
        archivo_temporal_sesion.close()
        kwargs["storage_state"] = archivo_temporal_sesion.name

    contexto = browser.new_context(**kwargs)

    try:
        pagina = proveedor.preparar_pagina(contexto, expediente.parametros())
        expedientes_encontrados = proveedor.extraer_expedientes(pagina, expediente.parametros())
    except RuntimeError as exc:
        if str(exc) == "sesion_expirada" and sesion:
            sesion.expirada = True
            db.session.commit()
            print(f"[{expediente.id}] La sesion de {expediente.jurisdiccion} expiro.")
        else:
            print(f"[{expediente.id}] ERROR: {exc}")
        contexto.close()
        if archivo_temporal_sesion:
            import os
            os.unlink(archivo_temporal_sesion.name)
        return
    except Exception as exc:
        print(f"[{expediente.id}] ERROR al procesar: {exc}")
        contexto.close()
        if archivo_temporal_sesion:
            import os
            os.unlink(archivo_temporal_sesion.name)
        return

    for actual in expedientes_encontrados:
        anterior = obtener_estado_guardado(expediente.id, actual["id"])

        if anterior is None:
            guardar_o_actualizar_estado(expediente.id, actual)
            print(f"[{expediente.id}/{actual['id']}] Primer chequeo: {actual['caratula']}")
            continue

        cambios = comparar_con_guardado(anterior, actual)
        if cambios:
            detalle = "\n".join(cambios)
            print(f"[{expediente.id}/{actual['id']}] CAMBIOS: {detalle}")
            try:
                enviar_aviso(
                    destinatario=expediente.user.email,
                    asunto=f"[Agente Judicial] Novedad en {actual['caratula']}",
                    cuerpo=(
                        f"Expediente: {expediente.nombre}\n"
                        f"Carátula: {actual['caratula']}\n\n{detalle}\n"
                    ),
                )
            except Exception as exc:
                print(f"[{expediente.id}/{actual['id']}] ERROR al enviar mail: {exc}")

            guardar_o_actualizar_estado(expediente.id, actual)
        else:
            print(f"[{expediente.id}/{actual['id']}] sin novedades")

    contexto.close()
    if archivo_temporal_sesion:
        import os
        os.unlink(archivo_temporal_sesion.name)


def main() -> None:
    app = create_app()
    with app.app_context():
        expedientes = ExpedienteMonitoreado.query.filter_by(activo=True).all()

        if not expedientes:
            print("No hay expedientes activos para chequear.")
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,  # el worker corre en un servidor sin GUI
                args=["--disable-blink-features=AutomationControlled"],
            )

            for expediente in expedientes:
                print(f"\n=== Expediente #{expediente.id} ({expediente.nombre}) ===")
                procesar_expediente(browser, expediente)

            browser.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
