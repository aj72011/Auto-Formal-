interface FocusModeToggleProps {
  enabled: boolean;
  onToggle: () => void;
}

export function FocusModeToggle({ enabled, onToggle }: FocusModeToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`rounded-md border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition ${
        enabled
          ? "border-accent/60 bg-accent/15 text-accent"
          : "border-border bg-panelAlt text-textMuted hover:text-textMain"
      }`}
    >
      {enabled ? "Focus Mode On" : "Focus Mode"}
    </button>
  );
}
