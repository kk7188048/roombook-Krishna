from datetime import date, datetime, time, timedelta, timezone


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """True if the time range a overlaps the time range b."""
    return a_start < b_end and b_start < a_end


OFFICE_START = time(9, 30)
OFFICE_END = time(18, 30)
LUNCH_START = time(13, 0)
LUNCH_END = time(14, 0)
SLOT_STEP = timedelta(minutes=15)
BUFFER = timedelta(minutes=15)
LONG_MEETING = timedelta(minutes=60)
IST = timezone(timedelta(hours=5, minutes=30))


def slot_starts(day: date, duration_minutes: int) -> list[datetime]:
    current = datetime.combine(day, OFFICE_START)
    limit = datetime.combine(day, OFFICE_END)
    duration = timedelta(minutes=duration_minutes)
    starts = []
    while current + duration <= limit:
        starts.append(current)
        current += SLOT_STEP
    return starts


def buffered_end(start: datetime, end: datetime) -> datetime:
    if end - start > LONG_MEETING:
        return end + BUFFER
    return end


def overlaps_lunch(start: datetime, end: datetime, duration_minutes: int) -> bool:
    if duration_minutes <= 30:
        return False
    lunch_start = datetime.combine(start.date(), LUNCH_START)
    lunch_end = datetime.combine(start.date(), LUNCH_END)
    return overlaps(start, end, lunch_start, lunch_end)


def with_ist(value: datetime) -> datetime:
    return value.replace(tzinfo=IST)
