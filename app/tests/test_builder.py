from app.mic.builders.conversation_builder import ConversationBuilder
from app.mic.domain.enums import SourceType


def test_builder():

    builder = ConversationBuilder()

    result = (
        builder
        .create(
            conversation_id="1",
            source=SourceType.TEXT,
            title="Demo"
        )
        .add_participant(
            participant_id="u1",
            display_name="José"
        )
        .add_message(
            message_id="m1",
            participant_id="u1",
            text="Hola mundo"
        )
        .build()
    )

    assert result.success
    assert result.conversation.total_messages == 1
    assert result.conversation.total_participants == 1