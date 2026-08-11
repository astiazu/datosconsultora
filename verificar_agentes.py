"""
Script de diagnóstico para verificar por qué no se habilitan los agentes.
Ejecutar: python verificar_agentes.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, UserPlan, Plan
from app.services.plan_service import obtener_plan_usuario

def verificar():
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO DE AGENTES JUDICIALES")
        print("=" * 80)
        
        # 1. Ver todos los planes y sus features
        print("\n📋 PLANES DISPONIBLES:")
        print("-" * 80)
        planes = Plan.query.order_by(Plan.orden).all()
        for plan in planes:
            print(f"\n{plan.display_name} (nombre='{plan.nombre}'):")
            print(f"  - incluye_historial: {plan.incluye_historial}")
            print(f"  - incluye_motor_semantico: {plan.incluye_motor_semantico}")
            print(f"  - incluye_agentes: {plan.incluye_agentes} ← ¿TRUE?")
            print(f"  - incluye_actividad_completa: {plan.incluye_actividad_completa}")
            print(f"  - tiene_feature('agentes'): {plan.tiene_feature('agentes')}")
        
        # 2. Ver usuarios y sus planes
        print("\n\n👥 USUARIOS Y SUS PLANES:")
        print("-" * 80)
        usuarios = User.query.filter_by(is_active_account=True).all()
        for user in usuarios:
            user_plan = obtener_plan_usuario(user)
            plan_obj = user_plan.obtener_plan_obj() if user_plan else None
            
            print(f"\n{user.nombre} ({user.email}):")
            print(f"  - Plan asignado: {plan_obj.display_name if plan_obj else 'SIN PLAN'}")
            print(f"  - tiene_feature('agentes'): {plan_obj.tiene_feature('agentes') if plan_obj else False}")
            
            # Verificar si puede acceder a agentes
            if plan_obj and plan_obj.tiene_feature('agentes'):
                print(f"  ✅ DEBERÍA VER AGENTES HABILITADOS")
            else:
                print(f"  ❌ NO PUEDE VER AGENTES (falta feature o plan incorrecto)")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    verificar()