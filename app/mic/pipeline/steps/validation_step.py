from app.mic.pipeline.step import PipelineStep


class ValidationStep(PipelineStep):

    name = "Validate Conversation"

    def execute(self, context):

        if not context.conversation.messages:

            context.error("La conversación no contiene mensajes.")

        if not context.conversation.participants:

            context.error("La conversación no posee participantes.")