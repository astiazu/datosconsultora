from app.mic.adapters.facebook.facebook_adapter import FacebookAdapter
from app.mic.adapters.facebook.sample_data import facebook_post


def test_facebook_adapter():
    adapter = FacebookAdapter()
    result = adapter.convert(facebook_post)
    assert result.success
    conversation = result.conversation
    assert conversation.title == "¿Qué opinás del proyecto?"
    assert conversation.total_participants == 3
    assert conversation.total_messages == 3