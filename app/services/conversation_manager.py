from datetime import datetime

from app.mic.adapters.adapter_factory import AdapterFactory
from app.services.scraper_service import ScraperService


class ConversationManager:

    def crear_desde_url(self, url: str):

        scraper = ScraperService()

        respuesta = scraper.extraer_de_url(url)

        if not respuesta["success"]:
            return respuesta

        adapter = AdapterFactory.create("facebook")

        conversation = adapter.convert(respuesta["data"])

        conversation.metadata["url"] = url
        conversation.metadata["created"] = datetime.utcnow().isoformat()

        return {
            "success": True,
            "conversation": conversation
        }