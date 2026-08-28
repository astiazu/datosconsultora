# app/routes/monitor.py
"""
Panel de usuario del Agente de Monitoreo de Marca (Plata+).
Reutiliza app/services/agentes/monitor (MonitorAgent + MetaScraper +
ComparadorEvolucion + MicAdapter). Plan B (HTML subido) = BeautifulSoup,
rápido y sin bloqueos; la pata por URL usa Playwright como la LÓGICA 1.
"""
import json
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import MarcaMonitoreada
from app.utils.decorators import feature_required
from app.utils.datetime_utils import utc_now
from app.services.plan_service import puede_analizar, registrar_uso_analisis, obtener_plan_usuario
from app.services.agentes.monitor.config.monitor_config import slugify
from app.models import MarcaMonitoreada, MarcaSnapshot

monitor_bp = Blueprint("monitor", __name__, url_prefix="/dashboard/monitor")


def _base_user() -> Path:
    """Carpeta propia del usuario: estados/exports/informes del monitor."""
    p = Path(current_app.instance_path) / "monitor" / str(current_user.id)
    p.mkdir(parents=True, exist_ok=True)
    return p


@monitor_bp.route("/")
@login_required
@feature_required("motor_semantico")
def panel_monitor():
    marcas = (MarcaMonitoreada.query.filter_by(user_id=current_user.id, activo=True)
              .order_by(MarcaMonitoreada.creado.desc()).all())
    estados = {}
    for m in marcas:
        ruta = _base_user() / "estados" / f"estado_{slugify(m.nombre)}.json"
        if ruta.exists():
            try:
                estados[m.id] = json.loads(ruta.read_text(encoding="utf-8"))
            except Exception:
                estados[m.id] = None
    series = {m.id: m.snapshots.order_by(MarcaSnapshot.fecha.asc()).all() for m in marcas}
    return render_template("monitor_dashboard.html", marcas=marcas, estados=estados, series=series)    


@monitor_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@feature_required("motor_semantico")
def nuevo_monitor():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        platform = request.form.get("platform", "facebook")
        url = request.form.get("url", "").strip()
        keywords = [k.strip() for k in request.form.get("keywords", "").split(",") if k.strip()]
        if not nombre:
            flash("Poné un nombre para identificar la marca.", "error")
            return redirect(url_for("monitor.nuevo_monitor"))
        if platform not in ("facebook", "instagram", "x"):
            flash("Red no soportada.", "error")
            return redirect(url_for("monitor.nuevo_monitor"))
        marca = MarcaMonitoreada(user_id=current_user.id, nombre=nombre,
                                 platform=platform, url=url)
        marca.set_keywords(keywords)
        db.session.add(marca)
        db.session.commit()
        flash(f"'{nombre}' agregada a tu monitoreo.", "success")
        return redirect(url_for("monitor.panel_monitor"))
    return render_template("monitor_nuevo.html")


@monitor_bp.route("/<int:marca_id>/eliminar", methods=["POST"])
@login_required
@feature_required("motor_semantico")
def eliminar_monitor(marca_id):
    marca = MarcaMonitoreada.query.filter_by(id=marca_id, user_id=current_user.id).first_or_404()
    marca.activo = False
    db.session.commit()
    flash("Marca eliminada de tu monitoreo.", "success")
    return redirect(url_for("monitor.panel_monitor"))


@monitor_bp.route("/<int:marca_id>/export", methods=["POST"])
@login_required
@feature_required("motor_semantico")
def subir_export(marca_id):
    marca = MarcaMonitoreada.query.filter_by(id=marca_id, user_id=current_user.id).first_or_404()
    archivo = request.files.get("archivo_pagina")
    if not archivo or not archivo.filename or not archivo.filename.lower().endswith((".html", ".htm")):
        flash("Subí el .html que guardaste con Ctrl+S.", "error")
        return redirect(url_for("monitor.panel_monitor"))
    exports = _base_user() / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    path = exports / f"{uuid4().hex}_{secure_filename(archivo.filename)}"
    archivo.save(path)
    marca.ultimo_export = str(path)
    db.session.commit()
    flash("Export Plan B guardado. Ya podés correr el monitoreo.", "success")
    return redirect(url_for("monitor.panel_monitor"))

@monitor_bp.route("/<int:marca_id>/correr", methods=["POST"])
@login_required
@feature_required("motor_semantico")
def correr_monitor(marca_id):
    marca = MarcaMonitoreada.query.filter_by(id=marca_id, user_id=current_user.id).first_or_404()
    con_ia = request.form.get("con_ia") == "on"

    # ✅ Si subió el HTML en este mismo paso, lo guardamos como export Plan B
    archivo = request.files.get("archivo_pagina")
    if archivo and archivo.filename:
        exports = _base_user() / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        path = exports / f"{uuid4().hex}_{secure_filename(archivo.filename)}"
        archivo.save(path)
        marca.ultimo_export = str(path)
        db.session.commit()

    if con_ia:
        puede_usar, uso, limite = puede_analizar(current_user)
        if not puede_usar:
            flash(f"❌ Llegaste al límite de {limite} análisis este mes.", "error")
            return redirect(url_for("monitor.panel_monitor"))

    from app.services.agentes.monitor import MonitorAgent, MonitorConfig, MonitorTarget, Platform
    from app.services.agentes.monitor.scrapers.meta_scraper import MetaScraper

    target = MonitorTarget(
        nombre=marca.nombre,
        platform=Platform(marca.platform),
        url=marca.url,
        keywords=marca.keywords(),
        html_local=marca.ultimo_export,
    )
    base = _base_user()
    config = MonitorConfig(
        marca=marca.nombre,
        targets=[target],
        carpeta_estados=str(base / "estados"),
        carpeta_informes=str(base / "informes"),
        carpeta_exports=str(base / "exports"),
    )

    def factory(platform):
        service = None
        try:
            from app.services.scraper_service import ScraperService
            service = ScraperService()
        except ImportError:
            pass
        return MetaScraper(service)

    analysis = None
    if con_ia:
        from app.services.agentes.monitor.analyzers.mic_adapter import MicAdapter
        analysis = MicAdapter()

    agente = MonitorAgent(config, scraper_factory=factory, analysis_service=analysis)
    try:
        resultados = agente.correr()
    except Exception as e:
        current_app.logger.exception("Error corriendo el monitor de marca")
        flash(f"❌ El monitoreo falló: {e}", "error")
        return redirect(url_for("monitor.panel_monitor"))

    if con_ia:
        registrar_uso_analisis(current_user)

    res = resultados[0] if resultados else None
    if res is None:
        flash("❌ No se extrajo nada. Si Meta bloqueó la URL, subí el HTML guardado (Plan B).", "warning")
    elif res.comparacion.sin_novedades:
        flash(f"■ {marca.nombre}: SIN NOVEDADES.", "success")
    else:
        flash(f"✅ {marca.nombre}: +{len(res.comparacion.nuevos)} comentarios nuevos.", "success")
    if res and res.informe:
        marca.ultimo_informe = res.informe
    marca.ultima_corrida = utc_now()
    db.session.commit()

    # ✅ Snapshot para la línea de tiempo (gráfico de evolución)
    if res and res.scrape is not None:
        sent = res.comparacion.sentimiento_actual or {}
        snap = MarcaSnapshot(
            marca_id=marca.id,
            total_comentarios=len(res.scrape.comentarios),
            comentarios_nuevos=len(res.comparacion.nuevos),
            pct_positivo=sent.get("positivo", 0.0),
            pct_neutro=sent.get("neutro", 0.0),
            pct_negativo=sent.get("negativo", 0.0),
            riesgos_json=json.dumps(res.comparacion.riesgos, ensure_ascii=False),
            metodo=res.scrape.metodo,
        )
        db.session.add(snap)
        db.session.commit()
    return redirect(url_for("monitor.panel_monitor"))

@monitor_bp.route("/<int:marca_id>/generar-informe", methods=["POST"])
@login_required
def generar_informe(marca_id):
    """Genera el informe de inteligencia inicial tipo Cuello."""
    from app.models import MarcaMonitoreada, MarcaSnapshot
    from app.services.agentes.monitor.informe_service import InformeService
    from app.services.scraper_service import ScraperService
    from app.services.agentes.monitor.config.monitor_config import MonitorTarget, Platform

    marca = MarcaMonitoreada.query.get_or_404(marca_id)
    if marca.user_id != current_user.id:
        flash("No tenés permisos sobre esa marca.", "error")
        return redirect(url_for("monitor.panel_monitor"))

    # Validar plan (requiere motor_semantico = Plata+)
    user_plan = obtener_plan_usuario(current_user)
    plan_obj = user_plan.obtener_plan_obj()
    if not plan_obj or not plan_obj.tiene_feature("motor_semantico"):
        flash("Esta función requiere plan Plata o superior.", "error")
        return redirect(url_for("planes.mi_plan"))

    # Crear target desde la marca
    platform_map = {
        "facebook": Platform.FACEBOOK,
        "instagram": Platform.INSTAGRAM,
        "x": Platform.X,
    }
    platform = platform_map.get(marca.platform.lower(), Platform.FACEBOOK)

    target = MonitorTarget(
        nombre=marca.nombre,
        platform=platform,
        url=marca.url or "",
        keywords=marca.keywords() if marca.keywords else [],
        html_local=marca.ultimo_export,
    )

    # Instanciar servicios (IMPORTANTE: esta línea es la que faltaba)
    scraper_service = None
    try:
        scraper_service = ScraperService()
    except Exception:
        pass

    service = InformeService(scraper_service=scraper_service)

    # Contexto del operador
    contexto = request.form.get("contexto", "").strip()

    # Serie temporal para el anexo de evolución
    evolucion = [
        {
            "fecha": s.fecha.strftime("%d/%m %H:%M"),
            "total": s.total_comentarios,
            "nuevos": s.comentarios_nuevos,
            "positivo": s.pct_positivo,
            "neutro": s.pct_neutro,
            "negativo": s.pct_negativo,
        }
        for s in marca.snapshots.order_by(MarcaSnapshot.fecha.asc()).all()
    ]

    # Generar informe
    resultado = service.generar(
        target,
        user_plan=plan_obj.nombre,
        contexto=contexto,
        evolucion=evolucion,
    )

    if resultado["success"]:
        marca.ultimo_informe = resultado["ruta"]
        db.session.commit()
        flash(
            f"✅ Informe generado: {resultado['total_comentarios']} comentarios, "
            f"{resultado['total_barridos']} búsquedas web.",
            "success",
        )
    else:
        flash(f"❌ Error generando informe: {resultado['error']}", "error")

    return redirect(url_for("monitor.panel_monitor"))

@monitor_bp.route("/<int:marca_id>/ver-informe")
@login_required
def ver_informe(marca_id):
    """Muestra el último informe generado, renderizado como HTML."""
    from app.models import MarcaMonitoreada, MarcaSnapshot
    from pathlib import Path
    import markdown

    marca = MarcaMonitoreada.query.get_or_404(marca_id)
    if marca.user_id != current_user.id:
        flash("No tenés permisos sobre esa marca.", "error")
        return redirect(url_for("monitor.panel_monitor"))

    if not marca.ultimo_informe:
        flash("Todavía no se generó ningún informe.", "warning")
        return redirect(url_for("monitor.panel_monitor"))

    proyecto_dir = Path(__file__).parent.parent.parent
    ruta = Path(marca.ultimo_informe)
    if not ruta.is_absolute():
        ruta = proyecto_dir / ruta

    if not ruta.exists():
        flash(f"El archivo del informe no existe: {marca.ultimo_informe}", "error")
        return redirect(url_for("monitor.panel_monitor"))

    contenido_md = ruta.read_text(encoding="utf-8")

    contenido_html = markdown.markdown(
        contenido_md,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    # ✅ Serie temporal para el gráfico de evolución
    series = marca.snapshots.order_by(MarcaSnapshot.fecha.asc()).all()

    return render_template(
        "monitor_informe.html",
        marca=marca,
        contenido_html=contenido_html,
        contenido_md=contenido_md,
        ruta=ruta.name,
        series=series,           # ← ESTO FALTABA
    )