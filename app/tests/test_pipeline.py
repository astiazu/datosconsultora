
# app/mic/pipeline/test_pipeline.py
from app.mic.pipeline.pipeline import Pipeline

from app.mic.pipeline.steps.clean_step import CleanStep

from app.mic.pipeline.steps.validation_step import ValidationStep


def test_pipeline(conversation):

    pipeline = Pipeline()

    pipeline.add(CleanStep())

    pipeline.add(ValidationStep())

    result = pipeline.run(conversation)

    assert result.success

    assert conversation.messages[0].text == "Hola Mundo"