export type ResultTabKey =
  | "proof_output"
  | "explanation"
  | "lean_context"
  | "know_more"
  | "solution_walkthrough"
  | "verification_report";

interface ResultTabsControllerProps {
  activeTab: ResultTabKey;
  onChange: (tab: ResultTabKey) => void;
}

const TABS: { key: ResultTabKey; label: string }[] = [
  { key: "proof_output", label: "Proof Output" },
  { key: "explanation", label: "Explanation" },
  { key: "lean_context", label: "Lean Context" },
  { key: "know_more", label: "Know More" },
  { key: "solution_walkthrough", label: "Solution Walkthrough" },
  { key: "verification_report", label: "Verification Report" },
];

export function ResultTabsController({
  activeTab,
  onChange,
}: ResultTabsControllerProps) {
  return (
    <div className="grid grid-cols-1 gap-2 rounded-md border border-border bg-panelAlt p-2 sm:grid-cols-2">
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
