# app/services/scraper_service.py
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time


class ScraperService:
    """
    Extrae comentarios de Facebook/Instagram usando Playwright (navegador real).
    Esto permite ejecutar JavaScript y obtener el contenido dinámico.
    """

    def extraer_de_url(self, url: str) -> dict:
        """
        Usa Playwright para navegar a la URL y extraer comentarios.
        """
        try:
            with sync_playwright() as p:
                # Lanzar navegador en modo headless
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()
                
                # Navegar a la URL
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Esperar a que cargue el contenido dinámico
                time.sleep(3)
                
                # Hacer scroll para cargar más comentarios
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                
                # Obtener el HTML completo después de renderizar
                html = page.content()
                browser.close()
                
                # Parsear con BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extraer comentarios (heurística para Instagram/Facebook)
                comentarios = self._extraer_comentarios(soup, url)
                
                if len(comentarios) < 3:
                    return {
                        "success": False,
                        "error_msg": f"Solo se pudieron extraer {len(comentarios)} comentarios. Instagram/Facebook puede estar bloqueando el acceso. Por favor, copiá y pegá los comentarios manualmente."
                    }
                
                # Formatear para el MIC
                data_para_mic = {
                    "post_id": url,
                    "title": "Extracción desde URL",
                    "comments": [
                        {
                            "comment_id": str(i),
                            "user_id": f"user_{i}",
                            "user_name": c.get("usuario", f"Usuario {i}"),
                            "text": c["texto"],
                            "date": datetime.now()
                        }
                        for i, c in enumerate(comentarios)
                    ]
                }
                
                return {"success": True, "data": data_para_mic}
                
        except Exception as e:
            return {
                "success": False,
                "error_msg": f"Error al extraer comentarios: {str(e)}. Por favor, usá el método de copiar y pegar."
            }

    def _extraer_comentarios(self, soup, url: str) -> list:
        """
        Extrae comentarios del HTML parseado.
        Heurística adaptada para Instagram y Facebook.
        """
        comentarios = []
        
        # Detectar si es Instagram o Facebook
        es_instagram = "instagram.com" in url
        es_facebook = "facebook.com" in url
        
        if es_instagram:
            # Instagram: buscar divs con clase específica de comentarios
            comment_elements = soup.find_all('div', {'class': lambda x: x and 'x1lliihq' in x})
            for elem in comment_elements:
                text_elem = elem.find('span', {'dir': 'auto'})
                if text_elem:
                    texto = text_elem.get_text(strip=True)
                    if len(texto) > 5:
                        usuario_elem = elem.find('span', {'class': lambda x: x and 'x193iq5w' in x})
                        usuario = usuario_elem.get_text(strip=True) if usuario_elem else "Anónimo"
                        comentarios.append({
                            "usuario": usuario,
                            "texto": texto
                        })
        elif es_facebook:
            # Facebook: buscar divs con data-ft o clases específicas
            comment_elements = soup.find_all('div', {'data-ft': True})
            for elem in comment_elements:
                text_elem = elem.find('span', {'dir': 'auto'})
                if text_elem:
                    texto = text_elem.get_text(strip=True)
                    if len(texto) > 5:
                        comentarios.append({
                            "usuario": "Anónimo",
                            "texto": texto
                        })
        
        # Si no encontramos comentarios con heurísticas específicas,
        # buscar cualquier texto que parezca un comentario
        if len(comentarios) < 3:
            for elem in soup.find_all(['p', 'span']):
                texto = elem.get_text(strip=True)
                if 20 < len(texto) < 500:
                    if not any(c["texto"] == texto for c in comentarios):
                        comentarios.append({
                            "usuario": "Anónimo",
                            "texto": texto
                        })
                if len(comentarios) >= 50:
                    break
        
        # Eliminar duplicados
        vistos = set()
        comentarios_unicos = []
        for c in comentarios:
            key = c["texto"].lower().strip()
            if key not in vistos and len(key) > 10:
                vistos.add(key)
                comentarios_unicos.append(c)
        
        return comentarios_unicos[:50]