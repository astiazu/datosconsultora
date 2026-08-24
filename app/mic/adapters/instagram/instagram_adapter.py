# app/mic/adapters/instagram/instagram_adapter.py
from app.mic.adapters.facebook.facebook_adapter import FacebookAdapter
from app.mic.domain.enums import SourceType

class InstagramAdapter(FacebookAdapter):
    """Misma conversión que Facebook, pero la Conversation nace como INSTAGRAM."""
    source_type = SourceType.INSTAGRAM