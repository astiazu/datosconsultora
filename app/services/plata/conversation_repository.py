# app/services/plata/conversation_repository.py
"""
Repository de Conversations del Plan Plata.
Persiste ConversationRecord (JSON) y reconstruye Conversation en memoria.
"""
import json
from app import db
from app.models import ConversationRecord
from app.services.plata.serialization import (
    conversation_to_dict,
    conversation_from_dict,
)


class ConversationRepository:
    """Acceso a datos de las conversaciones del Plan Plata."""

    def guardar(self, user_id: int, conversation, contexto: str = "") -> ConversationRecord:
        """Persiste una Conversation como JSON. Estado inicial: pendiente."""
        record = ConversationRecord(
            user_id=user_id,
            conversation_id=conversation.conversation_id,
            source=conversation.source.value,
            title=conversation.title,
            total_messages=conversation.total_messages,
            total_participants=conversation.total_participants,
            conversation_json=json.dumps(
                conversation_to_dict(conversation),
                ensure_ascii=False,
            ),
            contexto=contexto or None,
            estado="pendiente",
        )
        db.session.add(record)
        db.session.commit()
        return record

    def obtener(self, record_id: int, user_id: int) -> dict | None:
        """Carga un record y reconstruye la Conversation en memoria."""
        record = ConversationRecord.query.filter_by(
            id=record_id, user_id=user_id
        ).first()
        if not record:
            return None
        conversation = conversation_from_dict(json.loads(record.conversation_json))
        return {"record": record, "conversation": conversation}

    def listar(self, user_id: int):
        """Historial de conversaciones del usuario (más reciente primero)."""
        return (
            ConversationRecord.query
            .filter_by(user_id=user_id)
            .order_by(ConversationRecord.fecha.desc())
            .all()
        )

    def guardar_resultado(self, record_id: int, resultado_dict: dict) -> ConversationRecord | None:
        """Asocia el resultado del análisis semántico al record."""
        record = ConversationRecord.query.get(record_id)
        if not record:
            return None
        record.resultado_json = json.dumps(resultado_dict, ensure_ascii=False)
        record.estado = "analizada"
        db.session.commit()
        return record