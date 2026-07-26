# app/services/agentes/jurisdicciones.py
"""
Registro de jurisdicciones soportadas por el modulo de agentes.

`necesita_login` determina si esa jurisdiccion requiere una
SesionJurisdiccion (subida por el usuario) para poder monitorearse en
background, o si es de consulta publica.

`soporta_automatizacion` indica si el worker en background puede chequearla
sin intervencion humana. Las jurisdicciones con captcha por busqueda (como
Cordoba) van con soporta_automatizacion=False: el usuario puede guardarlas
para tener un link directo, pero no van a generar avisos automaticos por
mail.
"""

JURISDICCIONES = {
    "mev_scba": {
        "nombre": "MEV - Suprema Corte de Justicia de Buenos Aires",
        "necesita_login": True,
        "soporta_automatizacion": True,
        "campos_formulario": [
            {"name": "url", "label": "URL de la consulta/set en la MEV", "tipo": "text"},
        ],
    },
    "cordoba_sac": {
        "nombre": "SAC - Poder Judicial de Cordoba",
        "necesita_login": False,
        "soporta_automatizacion": False,
        "url_consulta": "https://www.justiciacordoba.gob.ar/justiciacordoba/servicios/ConsultaJuicios.aspx",
        "campos_formulario": [
            {"name": "numero_expediente", "label": "Numero de expediente (si lo tenes)", "tipo": "text"},
            {"name": "apellido", "label": "Apellido de una de las partes", "tipo": "text"},
        ],
    },
}


def obtener_jurisdiccion(jid: str) -> dict | None:
    return JURISDICCIONES.get(jid)


def listar_jurisdicciones() -> dict:
    return JURISDICCIONES
