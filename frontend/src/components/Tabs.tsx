// components/Tabs.tsx : the top navigation (Tickets / Approvals / Incidents / Audit).
// It is "controlled": App.tsx owns which tab is active and passes it in, so other parts can switch tabs too.
export type TabId = "tickets" | "approvals" | "incidents" | "audit";

interface Props { active: TabId; onChange: (tab: TabId) => void; approvalCount: number }

const TABS: { id: TabId; label: string }[] = [
  { id: "tickets", label: "Tickets" },
  { id: "approvals", label: "Approvals" },
  { id: "incidents", label: "Incidents" },
  { id: "audit", label: "Audit log" },
];

export function Tabs({ active, onChange, approvalCount }: Props) {
  return (
    <nav className="tabs" aria-label="Main sections">
      {TABS.map((tab) => (
        <button key={tab.id} className={`tab ${active === tab.id ? "tab--active" : ""}`}
                aria-current={active === tab.id ? "page" : undefined} onClick={() => onChange(tab.id)}>
          {tab.label}
          {tab.id === "approvals" && approvalCount > 0 && <span className="count">{approvalCount}</span>}
        </button>
      ))}
    </nav>
  );
}
