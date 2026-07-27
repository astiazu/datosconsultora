
# app/mic/domain/estities/message.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

from .attachment import Attachment


@dataclass(slots=True)
class Message:
    message_id: str
    participant_id: str
    text: str
    created_at: datetime
    reply_to: str | None = None
    reactions: int = 0
    attachments: List[Attachment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_attachment(self, attachment: Attachment):
        self.attachments.append(attachment)

        