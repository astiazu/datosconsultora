# app/routes/historial.py
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import Transcription, AnalysisSession

historial_bp = Blueprint("historial", __name__)

@historial_bp.route("/dashboard/historial")
@login_required
def mi_historial():
    """Vista de historial combinado de transcripciones y análisis."""
    filtro = request.args.get("filtro", "todos")
    
    # Obtener transcripciones
    transcripciones = Transcription.query.filter_by(user_id=current_user.id).order_by(Transcription.fecha.desc()).all()
    
    # Obtener análisis
    analisis = AnalysisSession.query.filter_by(user_id=current_user.id).order_by(AnalysisSession.fecha.desc()).all()
    
    # Combinar y ordenar por fecha
    historial_combinado = []
    
    if filtro in ["todos", "transcripciones"]:
        for t in transcripciones:
            historial_combinado.append({
                "tipo": "transcripcion",
                "fecha": t.fecha,
                "titulo": f"Transcripción: {t.file.filename if t.file else 'Archivo'}",
                "resumen": t.texto[:150] + "..." if len(t.texto) > 150 else t.texto,
                "id": t.id,
                "detalle": t
            })
    
    if filtro in ["todos", "analisis"]:
        for a in analisis:
            resultado = a.obtener_resultado()
            estadisticas = resultado.get("estadisticas", {})
            resumen = resultado.get("resumen_general", "Análisis de sentimientos")
            
            historial_combinado.append({
                "tipo": "analisis",
                "fecha": a.fecha,
                "titulo": f"Análisis: {a.red_social.upper() if a.red_social else 'Red Social'}",
                "resumen": resumen[:150] + "..." if len(resumen) > 150 else resumen,
                "id": a.id,
                "detalle": a,
                "estadisticas": estadisticas
            })
    
    # Ordenar por fecha (más reciente primero)
    historial_combinado.sort(key=lambda x: x["fecha"], reverse=True)
    
    return render_template(
        "historial.html",
        historial=historial_combinado,
        filtro=filtro,
        total_transcripciones=len(transcripciones),
        total_analisis=len(analisis)
    )

@historial_bp.route("/dashboard/historial/transcripcion/<int:transcription_id>")
@login_required
def ver_transcripcion(transcription_id):
    """Ver detalle de una transcripción."""
    transcription = Transcription.query.get_or_404(transcription_id)
    
    # Verificar que pertenece al usuario
    if transcription.user_id != current_user.id:
        from flask import flash, redirect, url_for
        flash("No tenés permisos para ver esta transcripción", "error")
        return redirect(url_for("historial.mi_historial"))
    
    return render_template("ver_transcripcion.html", transcription=transcription)

@historial_bp.route("/dashboard/historial/analisis/<int:analysis_id>")
@login_required
def ver_analisis(analysis_id):
    """Ver detalle de un análisis."""
    analysis = AnalysisSession.query.get_or_404(analysis_id)
    
    # Verificar que pertenece al usuario
    if analysis.user_id != current_user.id:
        from flask import flash, redirect, url_for
        flash("No tenés permisos para ver este análisis", "error")
        return redirect(url_for("historial.mi_historial"))
    
    resultado = analysis.obtener_resultado()
    
    return render_template("ver_analisis.html", analysis=analysis, resultado=resultado)