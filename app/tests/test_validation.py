from datetime import datetime

from app.mic.domain.entities.conversation import Conversation

from app.mic.domain.enums import SourceType

from app.mic.pipeline.pipeline import Pipeline

from app.mic.pipeline.steps.validation_step import ValidationStep


def test_validation_without_messages():

    c = Conversation(
        conversation_id="1",
        source=SourceType.TEXT,
        title="Vacía",
        created_at=datetime.now()
    )

    pipeline = Pipeline()

    pipeline.add(ValidationStep())

    result = pipeline.run(c)

    assert result.success is False

    assert len(result.errors) == 2