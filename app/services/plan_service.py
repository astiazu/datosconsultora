# app/services/plan_service.py
from app import db
from app.models import Plan, UserPlan, User
from datetime import datetime

def inicializar_planes_por_defecto():
    if Plan.query.count() > 0:
        return
    
    planes = [
        # ⭐ NUEVO: Plan Free (agregado al inicio)
        Plan(
            nombre='free', 
            display_name='Free', 
            descripcion='Plan de prueba para conocer la plataforma.', 
            precio_mensual=0.0, 
            precio_anual=0.0, 
            precio_lifetime=0.0, 
            es_lifetime=False, 
            activo=True, 
            orden=0,  # ⭐ Orden 0 para que aparezca primero
            incluye_historial=False, 
            incluye_motor_semantico=False, 
            incluye_agentes=False, 
            incluye_actividad_completa=False, 
            limite_transcripciones_mes=3,  # ⭐ Límite bajo
            limite_analisis_mes=2,  # ⭐ Límite bajo
            icono='bi-gift-fill', 
            color='info'
        ),
        Plan(nombre='bronce', display_name='Bronce', descripcion='Plan gratuito para empezar.', precio_mensual=0.0, precio_anual=0.0, precio_lifetime=0.0, es_lifetime=False, activo=True, orden=1, incluye_historial=False, incluye_motor_semantico=False, incluye_agentes=False, incluye_actividad_completa=False, limite_transcripciones_mes=5, limite_analisis_mes=3, icono='bi-award-fill', color='warning'),
        Plan(nombre='plata', display_name='Plata', descripcion='Para profesionales.', precio_mensual=15000.0, precio_anual=144000.0, precio_lifetime=250000.0, es_lifetime=False, activo=True, orden=2, incluye_historial=True, incluye_motor_semantico=True, incluye_agentes=False, incluye_actividad_completa=False, limite_transcripciones_mes=100, limite_analisis_mes=50, icono='bi-award-fill', color='secondary'),
        Plan(nombre='oro', display_name='Oro', descripcion='Para empresas.', precio_mensual=35000.0, precio_anual=336000.0, precio_lifetime=600000.0, es_lifetime=False, activo=True, orden=3, incluye_historial=True, incluye_motor_semantico=True, incluye_agentes=True, incluye_actividad_completa=True, limite_transcripciones_mes=500, limite_analisis_mes=200, icono='bi-trophy-fill', color='warning'),
        Plan(nombre='lifetime', display_name='Lifetime', descripcion='Acceso de por vida.', precio_mensual=0.0, precio_anual=0.0, precio_lifetime=900000.0, es_lifetime=True, activo=True, orden=4, incluye_historial=True, incluye_motor_semantico=True, incluye_agentes=True, incluye_actividad_completa=True, limite_transcripciones_mes=999999, limite_analisis_mes=999999, icono='bi-gem', color='danger'),
    ]
    
    for plan in planes:
        db.session.add(plan)
    db.session.commit()

def obtener_plan_usuario(user):
    user_plan = UserPlan.query.filter_by(user_id=user.id).first()
    if not user_plan:
        # ⭐ CAMBIO: Asignar plan Free a nuevos usuarios
        plan_free = Plan.query.filter_by(nombre='free').first()
        user_plan = UserPlan(
            user_id=user.id, 
            plan_id=plan_free.id if plan_free else None, 
            plan='free',  # ⭐ Cambiado de 'bronce' a 'free'
            limite_transcripciones=3,  # ⭐ Límites del plan Free
            limite_analisis=2
        )
        db.session.add(user_plan)
        db.session.commit()
    return user_plan
def obtener_todos_los_planes():
    return Plan.query.filter_by(activo=True).order_by(Plan.orden).all()

def puede_transcribir(user):
    user_plan = obtener_plan_usuario(user)
    plan = user_plan.obtener_plan_obj()
    limite = plan.limite_transcripciones_mes if plan else 5
    if limite >= 999999:
        return True, user_plan.consumo_transcripciones_mes(), limite
    uso = user_plan.consumo_transcripciones_mes()
    return uso < limite, uso, limite

def registrar_uso_transcripcion(user):
    user_plan = obtener_plan_usuario(user)
    user_plan.consumo_transcripciones += 1
    db.session.commit()

def puede_analizar(user):
    user_plan = obtener_plan_usuario(user)
    plan = user_plan.obtener_plan_obj()
    limite = plan.limite_analisis_mes if plan else 3
    if limite >= 999999:
        return True, user_plan.consumo_analisis_mes(), limite
    uso = user_plan.consumo_analisis_mes()
    return uso < limite, uso, limite

def registrar_uso_analisis(user):
    user_plan = obtener_plan_usuario(user)
    user_plan.consumo_analisis += 1
    db.session.commit()
