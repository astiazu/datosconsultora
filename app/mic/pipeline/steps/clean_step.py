from app.mic.pipeline.step import PipelineStep


class CleanStep(PipelineStep):

    name = "Clean Conversation"

    def execute(self, context):

        for message in context.conversation.messages:

            message.text = message.text.strip()