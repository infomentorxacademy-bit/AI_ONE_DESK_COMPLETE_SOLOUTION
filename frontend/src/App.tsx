// App.tsx : the root component. It owns the few things shared by every screen:
//   * config  (which LLM is active, which providers exist)     * approvers + who the user is "acting as"
//   * the active tab                                            * refreshKey: bump it and every view reloads its data
import { useState } from "react";
import { api } from "./api/client";
import { ErrorBanner } from "./components/ErrorBanner";
import { Header } from "./components/Header";
import { Tabs, type TabId } from "./components/Tabs";
import { useAsync } from "./hooks/useAsync";
import { ApprovalsView } from "./views/ApprovalsView";
import { AuditView } from "./views/AuditView";
import { IncidentsView } from "./views/IncidentsView";
import { TicketsView } from "./views/TicketsView";

export default function App() {
  const [tab, setTab] = useState<TabId>("tickets");
  const [refreshKey, setRefreshKey] = useState(0);
  const [actingAs, setActingAs] = useState("L01");
  const bump = () => setRefreshKey((n) => n + 1);              // "something changed, reload your data"

  const config = useAsync(() => api.config(), [refreshKey]);
  const approvers = useAsync(() => api.approvers(), []);
  const pending = useAsync(() => api.approvals(), [refreshKey]);
  const approver = approvers.data?.find((a) => a.id === actingAs);

  if (!config.data) {
    return <main className="page"><ErrorBanner message={config.error} />{!config.error && <p className="muted">Connecting…</p>}</main>;
  }
  const llmReady = config.data.llm !== null;

  return (
    <>
      <Header config={config.data} approvers={approvers.data ?? []} actingAs={actingAs} onActingAs={setActingAs}
              onConfigChanged={bump} onDataReset={bump} />
      <Tabs active={tab} onChange={setTab} approvalCount={pending.data?.length ?? 0} />
      <main className="page">
        {!llmReady && (
          <div className="banner banner--warn" role="status">
            No LLM is selected yet. Choose OpenAI or Groq in the top bar (the API key must be set in <code>app/.env</code>).
            You can still browse tickets, incidents and the audit log.
          </div>
        )}
        {tab === "tickets" && <TicketsView approver={approver} llmReady={llmReady} refreshKey={refreshKey} onChanged={bump} />}
        {tab === "approvals" && <ApprovalsView approver={approver} refreshKey={refreshKey} onChanged={bump} />}
        {tab === "incidents" && <IncidentsView llmReady={llmReady} refreshKey={refreshKey} onChanged={bump} />}
        {tab === "audit" && <AuditView refreshKey={refreshKey} />}
      </main>
    </>
  );
}
