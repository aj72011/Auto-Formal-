export type ContextTabKey = "proof_output" | "explanation" | "know_more" | "solution";

interface ContextTabsProps {
  activeTab: ContextTabKey;
  onChange: (tab: ContextTabKey) => void;
}

const TABS: { key: ContextTabKey; label: string }[] = [
  { key: "proof_output", label: "Proof Output" },
  { key: "explanation", label: "Explanation" },
  { key: "know_more", label: "Know More" },
  { key: "solution", label: "Solution Walkthrough" },
];

export function ContextTabs({ activeTab, onChange }: ContextTabsProps) {
  return (
    <div className="grid grid-cols-2 gap-2 rounded-md border border-border bg-panelAlt p-2">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onChange(tab.key)}
          className={`rounded px-2 py-1.5 text-xs font-semibold transition ${
            activeTab === tab.key
              ? "bg-accent/18 text-accent"
              : "bg-transparent text-textMuted hover:text-textMain"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
