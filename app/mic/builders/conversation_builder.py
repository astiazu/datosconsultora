# app/mic/builders/conversation_builder.py
from __future__ import annotations

from datetime import datetime

from app.mic.builders.builder_result import BuilderResult

from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant

from app.mic.domain.enums import SourceType
from app.mic.domain.enums import ParticipantRole


class ConversationBuilder:
    """
    Builder oficial del MIC.
    Todos los conectores deberán utilizar esta clase.
    """

    def __init__(self):
        self.reset()

    # ---------------------------------------------------------

    def reset(self):
        self._conversation: Conversation | None = None
        self._result = BuilderResult(success=True)
        return self

    # ---------------------------------------------------------

    def create(
        self,
        conversation_id: str,
        source: SourceType,
        title: str,
        created_at: datetime | None = None,
    ):

        self._conversation = Conversation(
            conversation_id=conversation_id,
            source=source,
            title=title,
            created_at=created_at or datetime.now(),
        )
        return self

    # ---------------------------------------------------------

    def add_participant(
        self,
        participant_id: str,
        display_name: str,
        role: ParticipantRole = ParticipantRole.UNKNOWN,
        metadata: dict | None = None,
    ):

        if self._conversation is None:
            self._result.add_error(
                "Debe crear primero la conversación."
            )
            return self

        exists = any(
            p.participant_id == participant_id
            for p in self._conversation.participants
        )

        if exists:
            self._result.statistics.duplicate_participants += 1
            self._result.add_warning(
                f"Participante duplicado: {participant_id}"
            )
            return self

        participant = Participant(
            participant_id=participant_id,
            display_name=display_name,
            role=role,
            metadata=metadata or {},
        )
        self._conversation.add_participant(participant)
        self._result.statistics.participants_added += 1

        return self

    # ---------------------------------------------------------

    def add_message(
        self,
        message_id: str,
        participant_id: str,
        text: str,
        created_at: datetime | None = None,
        reply_to: str | None = None,
        reactions: int = 0,
    ):

        if self._conversation is None:
            self._result.add_error(
                "Debe crear primero la conversación."
            )
            return self

        text = text.strip()

        if not text:
            self._result.statistics.empty_messages += 1
            self._result.add_warning(
                f"Mensaje vacío descartado ({message_id})"
            )
            return self

        participant_exists = any(
            p.participant_id == participant_id
            for p in self._conversation.participants
        )

        if not participant_exists:
            self._result.add_error(
                f"Participante inexistente: {participant_id}"
            )
            return self
        duplicated = any(
            m.message_id == message_id
            for m in self._conversation.messages
        )

        if duplicated:
            self._result.statistics.duplicate_messages += 1
            self._result.add_warning(
                f"Mensaje duplicado: {message_id}"
            )
            return self

        message = Message(
            message_id=message_id,
            participant_id=participant_id,
            text=text,
            created_at=created_at or datetime.now(),
            reply_to=reply_to,
            reactions=reactions,
        )
        self._conversation.add_message(message)
        self._result.statistics.messages_added += 1
        return self

    # ---------------------------------------------------------

    def build(self) -> BuilderResult:

        if self._conversation is None:
            self._result.success = False
            self._result.add_error(
                "No existe ninguna conversación."
            )
            return self._result

        if len(self._conversation.participants) == 0:
            self._result.success = False
            self._result.add_error(
                "La conversación no tiene participantes."
            )

        if len(self._conversation.messages) == 0:
            self._result.success = False
            self._result.add_error(
                "La conversación no tiene mensajes."
            )

        self._result.conversation = self._conversation
        self._result.success = len(self._result.errors) == 0
        result = self._result
        self.reset()

        return result