# app/mic/domain/entities/conversation.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

from app.mic.domain.enums import SourceType
from .message import Message
from .participant import Participant


@dataclass(slots=True)
class Conversation:
    """
    Entidad principal del MIC.

    Todo el motor trabaja sobre una conversación,
    independientemente de la plataforma de origen.
    """
    conversation_id: str
    source: SourceType
    title: str
    created_at: datetime
    participants: List[Participant] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Message):
        self.messages.append(message)

    def add_participant(self, participant: Participant):
        self.participants.append(participant)

    @property
    def total_messages(self):
        return len(self.messages)

    @property
    def total_participants(self):
        return len(self.participants)

    @property
    def is_empty(self):
        return len(self.messages) == 0

    @property
    def has_participants(self):
        return len(self.participants) > 0

    @property
    def has_messages(self):
        return len(self.messages) > 0

def get_participant(self, participant_id: str):
    for participant in self.participants:
        if participant.participant_id == participant_id:
            return participant
    return None