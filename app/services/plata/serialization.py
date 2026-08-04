# app/services/plata/serialization.py
"""
Serializa Conversation (dataclass del MIC) a dict/JSON y viceversa.
Esta es la única capa que conoce la estructura interna de Conversation
para persistirla. El MIC no sabe que existe.
"""
from datetime import datetime
from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType, ParticipantRole


def conversation_to_dict(conversation: Conversation) -> dict:
    """Convierte una Conversation en un dict serializable."""
    return {
        "conversation_id": conversation.conversation_id,
        "source": conversation.source.value,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "metadata": conversation.metadata,
        "participants": [
            {
                "participant_id": p.participant_id,
                "display_name": p.display_name,
                "role": p.role.value,
                "metadata": p.metadata,
            }
            for p in conversation.participants
        ],
        "messages": [
            {
                "message_id": m.message_id,
                "participant_id": m.participant_id,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
                "reply_to": m.reply_to,
                "reactions": m.reactions,
                "metadata": m.metadata,
            }
            for m in conversation.messages
        ],
    }


def conversation_from_dict(data: dict) -> Conversation:
    """Reconstruye una Conversation desde un dict (roundtrip)."""
    conversation = Conversation(
        conversation_id=data["conversation_id"],
        source=SourceType(data["source"]),
        title=data.get("title", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        metadata=data.get("metadata", {}),
    )

    for p in data.get("participants", []):
        conversation.add_participant(Participant(
            participant_id=p["participant_id"],
            display_name=p["display_name"],
            role=ParticipantRole(p.get("role", "unknown")),
            metadata=p.get("metadata", {}),
        ))

    for m in data.get("messages", []):
        conversation.add_message(Message(
            message_id=m["message_id"],
            participant_id=m["participant_id"],
            text=m["text"],
            created_at=datetime.fromisoformat(m["created_at"]),
            reply_to=m.get("reply_to"),
            reactions=m.get("reactions", 0),
            metadata=m.get("metadata", {}),
        ))

    return conversation