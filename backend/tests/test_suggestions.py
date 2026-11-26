import pytest

FREE_REQUESTER_ID = 4
BASE = {
    "requester_id": FREE_REQUESTER_ID,
    "attendee_ids": [],
    "duration_minutes": 30,
    "date": "2026-12-07",
}


def suggest(client, room_id, **overrides):
    return client.post(f"/rooms/{room_id}/suggest", json={**BASE, **overrides})


def starts(body):
    return [slot["start"] for slot in body["slots"]]


def test_suggest_returns_first_three_valid_slots_with_ist_offset(client):
    res = suggest(client, 1)
    assert res.status_code == 200
    assert res.json()["slots"] == [
        {
            "start": "2026-12-07T11:45:00+05:30",
            "end": "2026-12-07T12:15:00+05:30",
        },
        {
            "start": "2026-12-07T12:00:00+05:30",
            "end": "2026-12-07T12:30:00+05:30",
        },
        {
            "start": "2026-12-07T12:15:00+05:30",
            "end": "2026-12-07T12:45:00+05:30",
        },
    ]


def test_existing_long_booking_buffer_blocks_1130_but_not_1145(client):
    res = suggest(client, 1, duration_minutes=45)
    assert res.status_code == 200
    slot_starts = starts(res.json())
    assert "2026-12-07T11:30:00+05:30" not in slot_starts
    assert slot_starts[0] == "2026-12-07T11:45:00+05:30"


def test_own_buffer_rejects_90_minute_candidate_at_1430(client):
    res = suggest(client, 1, duration_minutes=90)
    assert res.status_code == 200
    slot_starts = starts(res.json())
    assert "2026-12-07T14:30:00+05:30" not in slot_starts
    assert slot_starts[0] == "2026-12-07T16:30:00+05:30"


def test_attendee_busy_in_another_room_is_excluded(client):
    res = suggest(client, 1, attendee_ids=[2])
    assert res.status_code == 200
    assert starts(res.json())[0] == "2026-12-07T12:15:00+05:30"


def test_creator_without_attendee_membership_is_busy(client):
    room = client.post("/rooms", json={"name": "Quiet", "capacity": 10})
    assert room.status_code == 201
    booking = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": FREE_REQUESTER_ID,
            "attendee_ids": [],
            "start": "2026-12-07T15:00:00",
            "end": "2026-12-07T15:30:00",
        },
    )
    assert booking.status_code == 201

    res = suggest(client, room.json()["id"], requester_id=FREE_REQUESTER_ID, duration_minutes=240)
    assert res.status_code == 200
    assert res.json()["slots"] == []


def test_long_meeting_overlapping_lunch_is_skipped(client):
    res = suggest(client, 2, requester_id=6, duration_minutes=45)
    assert res.status_code == 200
    slot_starts = starts(res.json())
    assert not {"2026-12-07T13:15:00+05:30", "2026-12-07T13:30:00+05:30", "2026-12-07T13:45:00+05:30"} & set(slot_starts)
    assert slot_starts[0] == "2026-12-07T14:00:00+05:30"


def test_short_meeting_may_overlap_lunch(client):
    res = suggest(client, 2, requester_id=5)
    assert res.status_code == 200
    assert starts(res.json())[0] == "2026-12-07T13:15:00+05:30"


def test_intern_requester_blocked_but_intern_attendee_allowed(client):
    res = suggest(client, 2)
    assert res.status_code == 403

    res = suggest(client, 2, requester_id=3, attendee_ids=[4])
    assert res.status_code == 200


def test_weekend_returns_no_slots(client):
    res = suggest(client, 1, date="2026-12-06")
    assert res.status_code == 200
    assert res.json() == {"slots": []}


@pytest.mark.parametrize("duration", [0, 20, 250])
def test_invalid_duration_rejected(client, duration):
    res = suggest(client, 1, duration_minutes=duration)
    assert res.status_code == 422


def test_unknown_room(client):
    assert suggest(client, 99).status_code == 404


def test_unknown_requester(client):
    assert suggest(client, 1, requester_id=99).status_code == 404


def test_unknown_attendee(client):
    assert suggest(client, 1, attendee_ids=[99]).status_code == 400
