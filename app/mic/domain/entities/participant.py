
# app/mic/domain/entities/participant.py
from dataclasses import dataclass, field
from typing import Dict, Any

from app.mic.domain.enums import ParticipantRole


@dataclass(slots=True)
class Participant:
    """
    Representa una persona que participa en una conversación.
    """

    participant_id: str

    display_name: str

    role: ParticipantRole = ParticipantRole.UNKNOWN

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

        