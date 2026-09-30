from sb_webex.normalize import attention, meetings, messages, readable_tools


def test_write_named_tools_are_never_selected() -> None:
    chosen = readable_tools(
        [
            {"name": "list_meetings", "description": "List scheduled meetings"},
            {"name": "send_message", "description": "Send a chat message"},
            {"name": "create_meeting", "description": "Schedule a meeting"},
            {"name": "list_rooms", "description": "List spaces"},
            {"name": "list_messages", "description": "List messages"},
            {"name": "delete_message", "description": "Delete a message"},
        ]
    )
    assert chosen == {
        "meeting": "list_meetings",
        "space": "list_rooms",
        "message": "list_messages",
    }


def test_meetings_drop_rows_without_an_id() -> None:
    rows = meetings(
        {
            "items": [
                {"title": "No id"},
                {"id": "m1", "title": "Standup", "start": "2026-09-30T15:00:00Z"},
            ]
        }
    )
    assert [row["id"] for row in rows] == ["m1"]


def test_messages_grouped_by_room_use_content() -> None:
    rows = messages(
        {
            "room-1": {
                "status_code": 200,
                "messages": [
                    {
                        "id": "msg1",
                        "content": "Can you review?",
                        "created": "2026-09-30T14:00:00Z",
                        "personEmail": "ada@example.com",
                    }
                ],
            }
        }
    )
    assert rows[0]["space_id"] == "room-1"
    assert rows[0]["preview"] == "Can you review?"
    assert rows[0]["sender_name"] == "ada@example.com"
    assert rows[0]["parent_message_id"] is None
    assert rows[0]["parent_sender_email"] is None
    assert rows[0]["is_reply_to_me"] is False


def test_messages_without_me_email_or_parent_lookup_leave_thread_fields_default() -> None:
    rows = messages(
        [
            {
                "id": "msg1",
                "parentId": "parent-1",
                "text": "reply",
                "personEmail": "ada@example.com",
            }
        ]
    )
    assert rows[0]["parent_message_id"] == "parent-1"
    assert rows[0]["parent_sender_email"] is None
    assert rows[0]["is_reply_to_me"] is False


def test_messages_marks_is_reply_to_me_when_parent_sender_matches(
) -> None:
    def parent_lookup(parent_id: str) -> dict | None:
        assert parent_id == "parent-1"
        return {"id": "parent-1", "personEmail": "me@example.com"}

    rows = messages(
        [{"id": "msg1", "parentId": "parent-1", "text": "reply", "personEmail": "ada@example.com"}],
        me_email="me@example.com",
        parent_lookup=parent_lookup,
    )
    assert rows[0]["parent_message_id"] == "parent-1"
    assert rows[0]["parent_sender_email"] == "me@example.com"
    assert rows[0]["is_reply_to_me"] is True


def test_messages_does_not_mark_is_reply_to_me_when_parent_sender_differs() -> None:
    def parent_lookup(parent_id: str) -> dict | None:
        return {"id": "parent-1", "personEmail": "bo@example.com"}

    rows = messages(
        [{"id": "msg1", "parentId": "parent-1", "text": "reply", "personEmail": "ada@example.com"}],
        me_email="me@example.com",
        parent_lookup=parent_lookup,
    )
    assert rows[0]["parent_sender_email"] == "bo@example.com"
    assert rows[0]["is_reply_to_me"] is False


def test_messages_handles_a_failed_parent_lookup_gracefully() -> None:
    def parent_lookup(parent_id: str) -> dict | None:
        return None

    rows = messages(
        [{"id": "msg1", "parentId": "parent-1", "text": "reply", "personEmail": "ada@example.com"}],
        me_email="me@example.com",
        parent_lookup=parent_lookup,
    )
    assert rows[0]["parent_message_id"] == "parent-1"
    assert rows[0]["parent_sender_email"] is None
    assert rows[0]["is_reply_to_me"] is False


def test_messages_survives_a_raising_parent_lookup() -> None:
    def parent_lookup(parent_id: str) -> dict | None:
        raise RuntimeError("network down")

    rows = messages(
        [{"id": "msg1", "parentId": "parent-1", "text": "reply", "personEmail": "ada@example.com"}],
        me_email="me@example.com",
        parent_lookup=parent_lookup,
    )
    assert rows[0]["is_reply_to_me"] is False


def test_messages_without_parent_id_never_calls_parent_lookup() -> None:
    def parent_lookup(parent_id: str) -> dict | None:
        raise AssertionError("must not be called without a parentId")

    rows = messages(
        [{"id": "msg1", "text": "top level", "personEmail": "ada@example.com"}],
        me_email="me@example.com",
        parent_lookup=parent_lookup,
    )
    assert rows[0]["parent_message_id"] is None


def test_attention_ranks_mentions_and_questions_first() -> None:
    ranked = attention(
        [
            {
                "id": "a",
                "preview": "hello",
                "is_unread": True,
                "occurred_at": "2026-09-30T12:00:00Z",
            },
            {
                "id": "b",
                "preview": "can you review?",
                "is_mention": True,
                "occurred_at": "2026-09-30T11:00:00Z",
            },
        ]
    )
    assert ranked[0]["id"] == "b"
