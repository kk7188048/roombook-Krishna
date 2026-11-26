# DECISIONS

## Assumptions

- Booking intervals are half-open `[start, end)`: a meeting ending at 11:00 does not clash with one starting at 11:00.
- Naive timestamps stored in the database represent IST wall-clock time.

## Trade-offs

- Fixed the shared `overlaps` helper instead of patching callers, so every current and future caller gets correct interval semantics.
- Left the issues below unfixed in this PR to keep it scoped to the reported bug.

## Other problems noticed

- High: `BookingIn.normalise_datetime` (`backend/app/schemas.py:39`) silently drops timezone and seconds, so a `Z` timestamp is reinterpreted as IST.
- High: no authentication; any `creator_id` can be passed by any caller (`backend/app/routers/bookings.py:39`).
- Medium: `POST /bookings` ignores office rules (working hours, weekends, 15-minute boundaries, lunch, intern restriction, capacity).
- Medium: `create_booking` does not check attendee conflicts in other rooms.
- Medium: `create_booking` loads every booking for a room into memory with no date filter (`backend/app/routers/bookings.py:47`).
- Medium: seeded booking "Budget planning" 09:30–13:00 crosses the 13:00–14:00 lunch hour (`backend/app/seed.py:38`).
- Medium: SQLite foreign keys are not enabled (`backend/app/db.py:6-10`).
- Medium: the date filter uses only `Booking.start`, so cross-day bookings are missed (`backend/app/routers/bookings.py:26-28`).
- Low: frontend API errors lose the HTTP status code (`frontend/src/api.js:5-9`).
- Low: CORS is hard-coded to port 5173 (`backend/app/main.py:25`).
- Low: `RoomList` has no loading state (`frontend/src/components/RoomList.jsx:8-12`).
- Low: seed relies on insertion order for stable IDs (`backend/app/seed.py:49-70`).

## With more time

- Timezone-aware UTC storage, authentication, full office-rule validation in booking creation, database-side overlap filtering, enabled SQLite foreign keys, and PostgreSQL locking/constraints.

## AI usage

- Used AI to check interval math and review the starter code.
- Rejected reading the cleaning-buffer rule as requiring the buffer to finish before 18:30, and rejected an immediate UTC migration: neither is required for this task.
