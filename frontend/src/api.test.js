import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { getRooms, suggestSlots } from "./api.js";

afterEach(() => {
  delete globalThis.fetch;
});

test("API errors keep the HTTP status", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: "Room is already booked for that time" }),
  });

  await assert.rejects(getRooms(), (err) => {
    assert.equal(err.status, 409);
    assert.equal(err.message, "Room is already booked for that time");
    return true;
  });
});

test("suggestSlots posts to the suggest endpoint", async () => {
  let captured = null;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return { ok: true, json: async () => ({ slots: [] }) };
  };

  await suggestSlots(3, { requester_id: 1 });

  assert.equal(captured.url, "/api/rooms/3/suggest");
  assert.equal(captured.options.method, "POST");
  assert.equal(captured.options.headers["Content-Type"], "application/json");
});
