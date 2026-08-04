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


class ConversationService:
    """
    Orquestador del Plan Plata.
    Encapsula el flujo: Scraper → Adapter → Conversation.
    También permite construir Conversations desde texto pegado manualmente.
    """

    def __init__(self):
        self.scraper = ScraperService()

    # =========================================================================
    # FLUJO 1: Extracción por URL (Requiere API de Meta aprobada)
    # =========================================================================
    def extraer_conversation(self, url: str) -> dict:
        """
        Extrae comentarios desde una URL usando el Scraper y los convierte
        en una entidad Conversation mediante el Adapter correspondiente.
        """
        resultado = self.scraper.extraer_de_url(url)

        if not resultado["success"]:
            return resultado

        adapter = AdapterFactory.create(resultado["source"])
        conversation = adapter.convert(resultado["data"])

        return {
            "success": True,
            "conversation": conversation
        }

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