# app/services/conversation_service.py
from datetime import datetime
from uuid import uuid4
from app.services.scraper_service import ScraperService
from app.mic.adapters.adapter_factory import AdapterFactory
from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType
from app.services.analysis.text_cleaner import limpiar_comentarios

import re


class ConversationService:
    """
    Orquestador del Plan Plata.
    Encapsula el flujo: Scraper → Adapter → Conversation.
    También permite construir Conversations desde texto pegado manualmente.
    """

    def __init__(self):
        self.scraper = ScraperService()

    # =========================================================================
    # FLUJO 1: Extracción por URL (Requiere API de Meta aprobada)(descarga + guarda + parsea)
    # =========================================================================
    def extraer_conversation(self, url: str) -> dict:
        resultado = self.scraper.extraer_de_url(url)
        if not resultado["success"]:
            return resultado

        adapter = AdapterFactory.create(resultado["source"])
        build_result = adapter.convert(resultado["data"])

        if not getattr(build_result, "success", False) or getattr(build_result, "conversation", None) is None:
            errores = "; ".join(getattr(build_result, "errors", []) or ["No se pudo construir la conversación."])
            return {"success": False, "error_msg": f"Error al convertir los datos extraídos: {errores}"}

        conversation = build_result.conversation
        # ✅ Métricas de la publicación (likes/comentarios/compartidos) viajan con la Conversation
        conversation.metadata["stats"] = resultado.get("stats", {})

        if resultado.get("caption"):
            conversation.metadata["caption"] = resultado["caption"]

        conversation.metadata["url"] = url
        return {"success": True, "conversation": conversation}

    # =========================================================================
    # FLUJO 2: Construcción desde texto pegado manualmente (Plan Plata)
    # =========================================================================
    def from_manual_text(self, texto_crudo: str, contexto: str = "") -> dict:
        """
        Construye una Conversation a partir de texto copiado y pegado manualmente.
        Ideal para el Plan Plata cuando la extracción por URL no está disponible
        (API de Meta no aprobada) o el usuario prefiere pegar los comentarios.
        """
        comentarios_limpios, red_detectada = limpiar_comentarios(texto_crudo)
        
        if not comentarios_limpios:
            return {
                "success": False, 
                "error_msg": "No se encontraron comentarios válidos en el texto pegado."
            }
        
        # Determinar SourceType de forma segura
        red_lower = red_detectada.lower()
        if "instagram" in red_lower:
            source = SourceType.INSTAGRAM
        elif "facebook" in red_lower:
            source = SourceType.FACEBOOK
        elif "x" in red_lower or "twitter" in red_lower:
            source = SourceType.X
        elif "whatsapp" in red_lower:
            source = SourceType.WHATSAPP
        elif "transcripcion" in red_lower:
            source = SourceType.TEXT            
        else:
            source = SourceType.FACEBOOK  # Fallback por defecto
        
        # Crear la entidad Conversation
        conversation = Conversation(
            conversation_id=f"manual_{uuid4().hex}",
            source=source,
            title="Análisis Manual (Copiar y Pegar)",
            created_at=datetime.now(),
            metadata={"contexto": contexto} if contexto else {}
        )
        
        # Construir participantes y mensajes
        for i, c in enumerate(comentarios_limpios):
            pid = f"user_{i}"
            conversation.add_participant(Participant(
                participant_id=pid, 
                display_name=c["usuario"]
            ))
            conversation.add_message(Message(
                message_id=str(i),
                participant_id=pid,
                text=c["texto"],
                created_at=datetime.now(),
            ))
            
        return {
            "success": True,
            "conversation": conversation,
            "red_social": red_detectada
        }

    # =========================================================================
    # FLUJO 3: Construcción desde página guardada (Plan B / auditoría)
    # =========================================================================
    def from_saved_page(self, html_content: str, url_original: str, contexto: str = "") -> dict:
        """Construye una Conversation parseando el HTML de una página guardada."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # ✅ Detectar la red desde la URL o desde el propio HTML
        red = self.scraper.detectar_red_desde_html(soup, url_original)
        url_falsa = {
            "instagram": "https://instagram.com/p/guardada",
            "x": "https://x.com/guardado",
            "facebook": "https://facebook.com/guardada",
        }[red]

        comentarios = self.scraper._extraer_comentarios(soup, url_falsa)
        if not comentarios:
            return {
                "success": False,
                "error_msg": "No se encontraron comentarios en el archivo. Guardá la página con 'HTML completo' desde el navegador."
            }

        # ✅ Extraer URL canónica del HTML (meta og:url) para tenerla siempre disponible
        og_url = soup.find("meta", property="og:url")
        url_canonica = (og_url.get("content") if og_url and og_url.get("content") else "") or (url_original or "")

        # ✅ Caption (primer mensaje del autor) + métricas, igual que en el flujo por URL
        # Tolerante: matchea si el primer comentario EMPIEZA con el username
        caption = None
        m_autor = re.search(r"instagram\.com/([a-zA-Z0-9._-]+)/", url_canonica or "")
        autor = m_autor.group(1).lower() if m_autor else None
        
        # Si no vino autor por URL, intentar detectarlo desde el HTML (primer comentario más largo)
        if not autor and comentarios:
            # Heurística: el autor suele ser el primer comentario con mucho texto
            for i, c in enumerate(comentarios[:5]):
                if len(c["texto"]) > 200 and c["usuario"] != "Anónimo":
                    autor = c["usuario"].lower().replace("verified", "").strip()
                    break
        
        if autor and comentarios:
            primer_user = comentarios[0]["usuario"].lower().replace("verified", "").strip()
            if primer_user.startswith(autor) or autor.startswith(primer_user):
                caption = comentarios.pop(0)["texto"]

        stats = self.scraper._extraer_stats(soup, red)

        source = {
            "instagram": SourceType.INSTAGRAM,
            "x": SourceType.X,
            "facebook": SourceType.FACEBOOK,
        }[red]

        conversation = Conversation(
            conversation_id=f"pagina_{uuid4().hex}",
            source=source,
            title=f"Página guardada: {url_canonica or red}",
            created_at=datetime.now(),
            metadata={"contexto": contexto} if contexto else {}
        )
        conversation.metadata["stats"] = stats
        if caption:
            conversation.metadata["caption"] = caption
        conversation.metadata["url"] = url_canonica

        for i, c in enumerate(comentarios):
            pid = f"user_{i}"
            conversation.add_participant(Participant(participant_id=pid, display_name=c["usuario"]))
            conversation.add_message(Message(
                message_id=str(i), participant_id=pid,
                text=c["texto"], created_at=datetime.now(),
            ))
        return {"success": True, "conversation": conversation, "red_social": red}