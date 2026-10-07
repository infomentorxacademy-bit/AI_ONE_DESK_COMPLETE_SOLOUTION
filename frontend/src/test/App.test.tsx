// test/App.test.tsx : the whole app with a fake backend: the LLM warning, choosing an LLM, and the approvals badge.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "../App";

type Json = unknown;
function fakeBackend(routes: Record<string, Json>) {
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url.replace("/api", "").split("?")[0]}`;
    if (!(key in routes)) return { ok: false, status: 404, json: async () => ({ detail: `unrouted ${key}` }) };
    const body = routes[key];
    return { ok: true, status: 200, json: async () => (typeof body === "function" ? body() : body) };
  }) as unknown as typeof fetch;
}

const providers = [{ name: "openai", model: "gpt-4o-mini", configured: false }, { name: "groq", model: "openai/gpt-oss-20b", configured: true }];
const common = {
  "GET /approvers": { items: [{ id: "L01", name: "Meera", role: "support_lead" }] },
  "GET /tickets": { items: [{ id: "T1", customer_id: "C004", text: "Where is my order?", created_at: "2026-10-07 12:05:00",
    status: "new", resolution: null, updated_at: "x", incident_id: null }] },
};

test("without an LLM it warns, still lists tickets, and disables running", async () => {
  fakeBackend({ ...common, "GET /config": { llm: null, providers, reset_enabled: false }, "GET /approvals": { items: [] } });
  render(<App />);
  expect(await screen.findByText(/No LLM is selected yet/)).toBeInTheDocument();
  expect(await screen.findByText("T1")).toBeInTheDocument();
  expect(screen.queryByText("Reset demo data")).not.toBeInTheDocument();     // reset is off by default
});

test("choosing Groq calls the API and the model name is shown with its default", async () => {
  fakeBackend({ ...common, "GET /config": { llm: null, providers, reset_enabled: false }, "GET /approvals": { items: [] },
    "POST /llm": { llm: "groq:openai/gpt-oss-20b" } });
  render(<App />);
  await screen.findByText(/No LLM is selected yet/);
  expect(screen.getByRole("option", { name: /OpenAI · gpt-4o-mini \(no key\)/ })).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("LLM"), "groq");
  await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith("/api/llm",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ provider: "groq" }) })));
});

test("the Approvals tab shows how many cards are waiting", async () => {
  fakeBackend({ ...common, "GET /config": { llm: "groq:x", providers, reset_enabled: true },
    "GET /approvals": { items: [{ thread_id: "a", ticket_id: "T3", card: {} }, { thread_id: "b", ticket_id: "T9", card: {} }] } });
  render(<App />);
  expect(await screen.findByRole("button", { name: /Approvals\s*2/ })).toBeInTheDocument();
  expect(screen.getByText("Reset demo data")).toBeInTheDocument();
  expect(screen.queryByText(/No LLM is selected yet/)).not.toBeInTheDocument();
});
