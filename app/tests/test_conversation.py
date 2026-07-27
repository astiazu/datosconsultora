from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant


def test_conversation_creation(conversation):

    assert conversation.title == "Conversación Demo"

    assert conversation.total_messages == 1

    assert conversation.total_participants == 1


def test_add_participant(conversation):

    conversation.add_participant(
        Participant(
            participant_id="2",
            display_name="María"
        )
    )

    assert conversation.total_participants == 2


def test_add_message(conversation):

    conversation.add_message(
        Message(
            message_id="2",
            participant_id="2",
            text="Segundo mensaje",
            created_at=conversation.created_at
        )
    )

    assert conversation.total_messages == 2