"""
Fixtures compartidas para todos los tests del MIC.
"""

from datetime import datetime

import pytest

from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType


@pytest.fixture
def conversation():

    c = Conversation(
        conversation_id="conversation-demo",
        source=SourceType.TEXT,
        title="Conversación Demo",
        created_at=datetime.now(),
    )

    c.add_participant(
        Participant(
            participant_id="user_1",
            display_name="José"
        )
    )

    c.add_message(
        Message(
            message_id="msg_1",
            participant_id="user_1",
            text=" Hola Mundo ",
            created_at=datetime.now()
        )
    )

    return c



