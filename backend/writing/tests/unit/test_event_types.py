from backend.writing.events.event_types import make_writing_event


def test_make_writing_event_shapes_payload():
    evt = make_writing_event("DocumentCreated", user_id=1, document_id=9, metadata={"x": 1})
    assert evt.name == "DocumentCreated"
    assert evt.user_id == 1
    assert evt.document_id == 9
    assert evt.metadata == {"x": 1}
    assert evt.created_at

