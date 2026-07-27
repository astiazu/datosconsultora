# app/examples/pipeline_example.py
from datetime import datetime

from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType

from app.mic.pipeline import Pipeline

from app.mic.pipeline.steps.clean_step import CleanStep
from app.mic.pipeline.steps.validation_step import ValidationStep


conversation = Conversation(
    conversation_id="1",
    source=SourceType.TEXT,
    title="Demo",
    created_at=datetime.now()
)

conversation.add_participant(
    Participant(
        participant_id="1",
        display_name="José"
    )
)

conversation.add_message(
    Message(
        message_id="1",
        participant_id="1",
        text="   Hola Mundo    ",
        created_at=datetime.now()
    )
)

pipeline = Pipeline()

pipeline.add(CleanStep())

pipeline.add(ValidationStep())

result = pipeline.run(conversation)

print(result.success)

print(conversation.messages[0].text)
