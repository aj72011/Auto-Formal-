interface ExampleSuggestionsProps {
  visible: boolean;
  examples: string[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  onConfirmIndex: (index: number) => void;
}

export function ExampleSuggestions({
  visible,
  examples,
  selectedIndex,
  onSelectIndex,
  onConfirmIndex,
}: ExampleSuggestionsProps) {
  if (!visible || examples.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-surface/70 p-2">
      <p className="mb-2 text-[11px] uppercase tracking-wider text-textMuted">
        Guided examples (Tab to cycle, Enter to insert)
      </p>
      <div className="grid gap-2 md:grid-cols-2">
        {examples.map((example, index) => (
          <button
            key={example}
            type="button"
            onMouseEnter={() => onSelectIndex(index)}
            onFocus={() => onSelectIndex(index)}
            onClick={() => onConfirmIndex(index)}
            className={`rounded-md border px-3 py-2 text-left text-xs transition ${
              selectedIndex === index
                ? "border-accent/70 bg-accent/15 text-textMain"
                : "border-border bg-panelAlt text-textMuted hover:text-textMain"
            }`}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
