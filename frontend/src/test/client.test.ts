// test/client.test.ts : the API client turns backend answers into typed data, and failures into readable errors.
import { vi } from "vitest";
import { api, ApiError } from "../api/client";

function mockFetch(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body }) as unknown as typeof fetch;
}

afterEach(() => vi.restoreAllMocks());

test("returns the items of a list endpoint", async () => {
  mockFetch(200, { items: [{ id: "T1" }] });
  expect(await api.tickets("new")).toEqual([{ id: "T1" }]);
  expect(globalThis.fetch).toHaveBeenCalledWith("/api/tickets?limit=100&status=new", expect.anything());
});

test("a string detail becomes the error message", async () => {
  mockFetch(400, { detail: "GROQ_API_KEY is not set." });
  await expect(api.selectLlm("groq")).rejects.toMatchObject({ message: "GROQ_API_KEY is not set.", status: 400 });
});

test("validation errors (422) are joined into one readable message", async () => {
  mockFetch(422, { detail: [{ msg: "Field required" }, { msg: "Value too short" }] });
  await expect(api.createTicket("x")).rejects.toThrow("Field required; Value too short");
});

test("a network failure says the backend is unreachable", async () => {
  globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("fetch failed")) as unknown as typeof fetch;
  const error = await api.config().catch((e) => e);
  expect(error).toBeInstanceOf(ApiError);
  expect(error.message).toMatch(/Cannot reach the backend/);
});

test("answering an approval posts the answer as JSON to the right thread", async () => {
  mockFetch(200, { state: "finished" });
  await api.answerApproval("T10-abc", { action: "cancel" });
  expect(globalThis.fetch).toHaveBeenCalledWith("/api/approvals/T10-abc",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ action: "cancel" }) }));
});
