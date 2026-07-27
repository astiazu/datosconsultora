# app/mic/adapters/adapter_factory.py
# from app.mic.adapters.csv.csv_adapter import CSVAdapter
from app.mic.adapters.facebook.facebook_adapter import FacebookAdapter
# from app.mic.adapters.instagram.instagram_adapter import InstagramAdapter
# from app.mic.adapters.whatsapp.whatsapp_adapter import WhatsAppAdapter


class AdapterFactory:
    _adapters = {
        "facebook": FacebookAdapter,
  #      "instagram": InstagramAdapter,
  #      "whatsapp": WhatsAppAdapter,
  #      "csv": CSVAdapter,
    }

    @classmethod
    def create(cls, source):
        if source not in cls._adapters:
            raise ValueError(f"No existe adapter para {source}")
        return cls._adapters[source]()