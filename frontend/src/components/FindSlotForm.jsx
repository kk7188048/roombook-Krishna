import { useEffect, useState } from "react";
import { createBooking, getRooms, getUsers, suggestSlots } from "../api.js";
import { formatTime } from "../dates.js";

export default function FindSlotForm({ date, onDateChange }) {
  const [rooms, setRooms] = useState([]);
  const [users, setUsers] = useState([]);
  const [formLoading, setFormLoading] = useState(true);
  const [formError, setFormError] = useState(null);
  const [roomId, setRoomId] = useState("");
  const [requesterId, setRequesterId] = useState("");
  const [attendeeIds, setAttendeeIds] = useState([]);
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [slots, setSlots] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotsError, setSlotsError] = useState(null);
  const [bookingSlot, setBookingSlot] = useState(null);
  const [bookError, setBookError] = useState(null);
  const [bookNotice, setBookNotice] = useState(null);

  useEffect(() => {
    Promise.all([getRooms(), getUsers()])
      .then(([roomData, userData]) => {
        setRooms(roomData);
        setUsers(userData);
        setRoomId(String(roomData[0].id));
        setRequesterId(String(userData[0].id));
      })
      .catch((err) => setFormError(err.message))
      .finally(() => setFormLoading(false));
  }, []);

  async function loadSlots() {
    setHasSearched(true);
    setSlotsLoading(true);
    setSlotsError(null);
    try {
      const data = await suggestSlots(parseInt(roomId, 10), {
        requester_id: parseInt(requesterId, 10),
        attendee_ids: attendeeIds,
        duration_minutes: durationMinutes,
        date,
      });
      setSlots(data.slots);
      return data.slots;
    } catch (err) {
      setSlots([]);
      setSlotsError(err.message);
      return [];
    } finally {
      setSlotsLoading(false);
    }
  }

  async function bookSlot(slot) {
    setBookingSlot(slot.start);
    setBookError(null);
    setBookNotice(null);
    try {
      await createBooking({
        room_id: parseInt(roomId, 10),
        creator_id: parseInt(requesterId, 10),
        title: "Booked from UI",
        attendee_ids: attendeeIds,
        start: slot.start,
        end: slot.end,
      });
      setBookNotice("Booked.");
      await loadSlots();
    } catch (err) {
      if (err.status === 409) {
        setBookError("That slot was just taken. Showing updated slots.");
        const refreshed = await loadSlots();
        if (refreshed.length === 0) {
          setBookError(null);
        }
      } else {
        setBookError(err.message);
      }
    } finally {
      setBookingSlot(null);
    }
  }

  if (formLoading) {
    return (
      <section className="card">
        <h2>Find a slot</h2>
        <p className="muted">Loading form…</p>
      </section>
    );
  }

  if (formError) {
    return (
      <section className="card">
        <h2>Find a slot</h2>
        <p className="error">{formError}</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Find a slot</h2>
      <form
        className="find-slot-form"
        onSubmit={(event) => {
          event.preventDefault();
          setSlots([]);
          setBookError(null);
          setBookNotice(null);
          loadSlots();
        }}
      >
        <label>
          Room
          <select value={roomId} onChange={(event) => setRoomId(event.target.value)}>
            {rooms.map((room) => (
              <option key={room.id} value={room.id}>
                {room.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Booked by
          <select value={requesterId} onChange={(event) => setRequesterId(event.target.value)}>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Attendees <span className="muted">(hold Ctrl/⌘ to pick multiple)</span>
          <select
            multiple
            value={attendeeIds.map(String)}
            onChange={(event) =>
              setAttendeeIds(
                Array.from(event.target.selectedOptions, (option) => parseInt(option.value, 10))
              )
            }
          >
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Duration
          <input
            type="number"
            min="15"
            max="240"
            step="15"
            value={durationMinutes}
            onChange={(event) => setDurationMinutes(parseInt(event.target.value, 10))}
          />
        </label>
        <label>
          Date
          <input type="date" value={date} onChange={(event) => onDateChange(event.target.value)} />
        </label>
        <button type="submit">Find slots</button>
      </form>

      {slotsLoading && <p className="muted">Finding slots…</p>}
      {slotsError && <p className="error">{slotsError}</p>}
      {bookNotice && <p className="muted">{bookNotice}</p>}
      {bookError && <p className="error">{bookError}</p>}
      {hasSearched && !slotsLoading && !slotsError && slots.length === 0 && (
        <p className="muted">No slots available.</p>
      )}
      <ul className="slots">
        {slots.map((slot) => (
          <li key={slot.start}>
            <button type="button" disabled={bookingSlot !== null} onClick={() => bookSlot(slot)}>
              {formatTime(slot.start)}–{formatTime(slot.end)}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
