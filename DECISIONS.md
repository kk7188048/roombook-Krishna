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

## Task 2: slot suggestions

- Assumptions: half-open intervals; naive database times are IST; the requester counts as a participant; participant conflicts include bookings where the user is creator or attendee.
- Intern rule: checked for the requester only; an intern attendee is allowed. Rejected requester+attendees because the spec says users who "book", not who attend. `403` is used because this is permission, not bad input.
- Duration: 15–240 minutes in 15-minute steps; invalid values return `422`.
- Weekend dates return an empty slot list instead of an error.
- Cleaning buffer: applies strictly when a booking or candidate is longer than 60 minutes. The candidate buffer is used only for room conflicts; attendee conflicts use raw meeting times. A candidate buffer may extend past 18:30 if the meeting ends by 18:30.
- One day-intersecting query loads bookings with attendees; participant conflicts are filtered in Python. No second query or SQL `or_()`.
- Slot generation stops at `18:30 - duration`; slot starts are `datetime` values built from the office open time.
- Timestamps are serialized as naive IST plus a fixed `+05:30` offset; no UTC conversion.
- `POST /bookings` is unchanged. Enforcing office rules there is deferred to keep this PR scoped to the `/suggest` endpoint.
- AI usage: used AI to check interval math and catch the creator-without-attendee conflict case; rejected the stricter intern-attendee reading and changing `POST /bookings` in this PR.

## Task 3: prevent double booking

- Chose a room-row lock: `SELECT ... FROM rooms WHERE id = ... FOR UPDATE` in `locked_room_query`, taken as the first database operation in `create_booking` and held until `db.commit()` or rollback.
- Serializes writers for the same room on PostgreSQL/Neon without a migration, extension, or new table. Locking `rooms.id` is necessary because no `bookings` row exists yet for the incoming request.
- Rejected a PostgreSQL exclusion constraint: stronger, but needs `btree_gist`, a migration, special SQLite handling, and error-code mapping; too much for this task.
- Rejected an advisory lock: also room-scoped, but more opaque and Postgres-only.
- Stops working if another writer inserts bookings without taking this lock, on databases that ignore `FOR UPDATE`, or under stricter isolation that requires retrying serialization failures.
- SQLite ignores `FOR UPDATE`, so the test checks the compiled PostgreSQL SQL and a sequential duplicate returns `409`; true simultaneous contention is not verified by pytest.
- The sequential duplicate test already passed before this change; it documents the user-visible outcome, while the lock is what addresses concurrency.
- AI usage: used AI to compare locking approaches and reject heavier schema options.

## Task 4: find a slot form

- Added a requester dropdown because the UI spec omits the requester but `/suggest` and `/bookings` both require one; default is Asha (`id: 1`).
- Reused the app-level date instead of a second independent date state, so the form and booking list stay in sync.
- Sent slot strings unchanged to `POST /bookings`. The backend strips the `+05:30` offset and stores the same wall-clock time as naive IST.
- Used a fixed title `Booked from UI` because the form does not ask for a title.
- Added `error.status` to frontend API errors so a `409` race can be detected reliably.
- On booking success or `409`, refreshed suggestions. If a `409` refresh returns no slots, cleared the race notice and showed `No slots available.`
- Rejected adding Vitest/React Testing Library because the frontend has no test setup and this task is intentionally small. Verified with Node tests for the API helper, `npm run build`, and a manual UI checklist.
- AI usage: used AI to plan the UI flow; rejected frontend UTC conversion and new frontend test dependencies.
