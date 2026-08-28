# app/routes/api.py
"""
Ruta API mínima para exponer el MIC.

Endpoint:
    POST /api/analisis

Request body:
{
    "origen": "facebook",
    "comentarios": ["texto1", "texto2"],
    "contexto": "descripción opcional"
}

Response:
{
    "success": true,
    "tipo_analisis": "semantico",
    "analisis": {...}
}
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.analysis_service import AnalysisService
from app.services.plan_service import puede_analizar, registrar_uso_analisis, obtener_plan_usuario

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/analisis", methods=["POST"])
@login_required
def analizar():
    """
    Endpoint para análisis de comentarios.
    Valida el plan del usuario y delega al AnalysisService.
    """
    try:
        # 1. Validar request
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body debe ser JSON válido."
            }), 400
        
        # 2. Extraer parámetros
        origen = data.get("origen", "facebook")
        comentarios = data.get("comentarios", [])
        contexto = data.get("contexto", "")
        
        # 3. Validar comentarios
        if not isinstance(comentarios, list):
            return jsonify({
                "success": False,
                "error": "'comentarios' debe ser una lista de strings."
            }), 400
        
        if len(comentarios) == 0:
            return jsonify({
                "success": False,
                "error": "Debe proporcionar al menos un comentario."
            }), 400
        
        # 4. Construir datos_crudos en formato esperado
        datos_crudos = {
            "comments": [
                {"text": c} if isinstance(c, str) else c
                for c in comentarios
            ]
        }
        # agragado nuevo - limites
        puede, uso, limite = puede_analizar(current_user)
        if not puede:
            return jsonify({
                "success": False,
                "error": f"Límite de {limite} análisis mensuales alcanzado. Mejorá tu plan.",
            }), 429
        
        # 5. Plan REAL del usuario (User no tiene .plan; vive en UserPlan)
        user_plan = obtener_plan_usuario(current_user).obtener_plan_obj().nombre

        # 6. Ejecutar análisis
        service = AnalysisService()
        resultado = service.analizar(
            datos_crudos=datos_crudos,
            origen=origen,
            user_plan=user_plan,
            contexto=contexto,
        )

        # 7. Descontar cuota SOLO si el análisis funcionó
        if resultado.get("success"):
            registrar_uso_analisis(current_user)
            status_code = 200
        else:
            status_code = 400
        return jsonify(resultado), status_code
        
    except Exception as exc:
        return jsonify({
            "success": False,
            "error": f"Error interno del servidor: {exc}"
        }), 500


@api_bp.route("/tokens/status", methods=["GET"])
@login_required
def token_status():
    """Estado del consumo de tokens (solo admin)."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Solo administradores"}), 403
    
    from app.services.analysis.token_monitor import TokenMonitor
    monitor = TokenMonitor.get_instance()
    return jsonify(monitor.get_summary())