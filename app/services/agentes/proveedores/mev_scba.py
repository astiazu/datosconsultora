# app/services/agentes/proveedores/mev_scba.py
"""
Proveedor: Mesa de Entradas Virtual - Suprema Corte de Bs As (MEV-SCBA).

Misma logica de extraccion que el agente standalone
(proveedores/mev_scba.py del repo agente-poder-judicial), pero pensada para
correr desde el worker en background usando la sesion que el usuario subio
(SesionJurisdiccion), no un archivo local.
"""

from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext, Page

necesita_login = True


def preparar_pagina(contexto: BrowserContext, parametros: dict) -> Page:
    pagina = contexto.new_page()
    pagina.goto(parametros["url"], wait_until="domcontentloaded")

    if "UsuarioMEV" not in pagina.content():
        raise RuntimeError("sesion_expirada")

    return pagina


def extraer_expedientes(pagina: Page, parametros: dict) -> list[dict]:
    soup = BeautifulSoup(pagina.content(), "html.parser")
    expedientes = []
    filas = soup.select("table.pegada tr")

    i = 0
    while i < len(filas):
        fila = filas[i]
        link = fila.select_one("a[href*='procesales.asp']")
        if link:
            href = link.get("href", "")
            nid_causa = href.split("nidCausa=")[1].split("&")[0] if "nidCausa=" in href else None
            caratula = link.get_text(strip=True)

            datos = {
                "id": nid_causa,
                "caratula": caratula,
                "estado": None,
                "fecha_inicio": None,
                "ultima_novedad": None,
            }

            if i + 1 < len(filas):
                celdas = filas[i + 1].select("td")
                textos = [c.get_text(strip=True) for c in celdas]
                if len(textos) >= 5:
                    datos["estado"] = textos[0]
                    datos["fecha_inicio"] = textos[3]
                    datos["ultima_novedad"] = textos[4]
                i += 1

            if nid_causa:
                expedientes.append(datos)
        i += 1

    return expedientes
