# app/mic/adapters/x/x_adapter.py
from app.mic.adapters.facebook.facebook_adapter import FacebookAdapter
from app.mic.domain.enums import SourceType

class XAdapter(FacebookAdapter):
    """Misma conversión que Facebook, pero la Conversation nace como X."""
    source_type = SourceType.X