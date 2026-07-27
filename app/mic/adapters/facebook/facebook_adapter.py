# app\mic\facebook\facebook_adapter.py
from datetime import datetime
from app.mic.adapters.base_adapter import BaseAdapter
from app.mic.builders.conversation_builder import ConversationBuilder
from app.mic.domain.enums import SourceType

class FacebookAdapter(BaseAdapter):
    """
    Convierte la respuesta de Facebook
    en una Conversation.
    """
    def convert(self, data):
        builder = ConversationBuilder()
        builder.create(
            conversation_id=data["post_id"],
            source=SourceType.FACEBOOK,
            title=data.get("title", "Facebook"),
            created_at=datetime.now()
        )

        users = {}

        for comment in data["comments"]:

            uid = comment["user_id"]

            if uid not in users:
                users[uid] = True
                builder.add_participant(
                    participant_id=uid,
                    display_name=comment["user_name"]
                )

            builder.add_message(
                message_id=comment["comment_id"],
                participant_id=uid,
                text=comment["text"],
                created_at=comment["date"]
            )

        return builder.build()