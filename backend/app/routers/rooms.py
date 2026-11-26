from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Booking, Room, User
from ..scheduling import buffered_end, overlaps, overlaps_lunch, slot_starts, with_ist
from ..schemas import RoomIn, RoomOut, SuggestRequest, SuggestResponse, SlotOut

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.scalars(select(Room).order_by(Room.id)).all()


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("", response_model=RoomOut, status_code=201)
def create_room(payload: RoomIn, db: Session = Depends(get_db)):
    room = Room(name=payload.name, capacity=payload.capacity)
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A room with that name already exists")
    return room


@router.post("/{room_id}/suggest", response_model=SuggestResponse)
def suggest_slots(room_id: int, payload: SuggestRequest, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    requester = db.get(User, payload.requester_id)
    if requester is None:
        raise HTTPException(status_code=404, detail="Requester not found")

    attendee_ids = set(payload.attendee_ids)
    attendees = db.scalars(select(User).where(User.id.in_(attendee_ids))).all()
    if len(attendees) != len(attendee_ids):
        raise HTTPException(status_code=400, detail="Unknown attendee")

    if requester.role == "intern" and room.name == "Board Room":
        raise HTTPException(status_code=403, detail="Interns cannot book the Board Room")

    if payload.date.weekday() >= 5:
        return SuggestResponse(slots=[])

    day_start = datetime.combine(payload.date, time.min)
    day_end = day_start + timedelta(days=1)
    bookings = db.scalars(
        select(Booking)
        .options(selectinload(Booking.attendees))
        .where(Booking.start < day_end, Booking.end > day_start)
    ).all()

    room_bookings = [booking for booking in bookings if booking.room_id == room_id]
    participant_ids = attendee_ids | {requester.id}
    user_busy = {uid: [] for uid in participant_ids}
    for booking in bookings:
        participants = {booking.creator_id} | {user.id for user in booking.attendees}
        for uid in participants & participant_ids:
            user_busy[uid].append((booking.start, booking.end))

    slots = []
    for start in slot_starts(payload.date, payload.duration_minutes):
        end = start + timedelta(minutes=payload.duration_minutes)
        if overlaps_lunch(start, end, payload.duration_minutes):
            continue
        candidate_end = buffered_end(start, end)
        if any(
            overlaps(start, candidate_end, booking.start, buffered_end(booking.start, booking.end))
            for booking in room_bookings
        ):
            continue
        if any(
            overlaps(start, end, busy_start, busy_end)
            for uid in participant_ids
            for busy_start, busy_end in user_busy[uid]
        ):
            continue
        slots.append(SlotOut(start=with_ist(start), end=with_ist(end)))
        if len(slots) == 3:
            break
    return SuggestResponse(slots=slots)
