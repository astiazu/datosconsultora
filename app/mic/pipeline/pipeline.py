
# app/mic/pipeline/pipeline.py
from app.mic.pipeline.context import PipelineContext
from app.mic.pipeline.result import PipelineResult


class Pipeline:

    def __init__(self):

        self.steps = []

    def add(self, step):

        self.steps.append(step)

        return self

    def run(self, conversation):

        context = PipelineContext(conversation)

        for step in self.steps:

            step.execute(context)

            if context.errors:

                break

        return PipelineResult(

            success=len(context.errors) == 0,

            data=context.data,

            warnings=context.warnings,

            errors=context.errors

        )