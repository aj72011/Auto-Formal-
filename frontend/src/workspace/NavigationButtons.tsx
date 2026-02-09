interface NavigationButtonsProps {
  page: "input" | "result";
  canViewResults: boolean;
  disableView?: boolean;
  viewLabel?: string;
  onViewResults: () => void;
  onBackToInput: () => void;
}

export function NavigationButtons({
  page,
  canViewResults,
  disableView = false,
  viewLabel,
  onViewResults,
  onBackToInput,
}: NavigationButtonsProps) {
  if (page === "input") {
    return (
      <div className="flex items-center justify-end">
        <button
          type="button"
          onClick={onViewResults}
          disabled={!canViewResults || disableView}
          className="rounded-md border border-accent/50 bg-accent/15 px-6 py-3 text-base font-semibold text-accent transition hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {viewLabel ?? "View Results ->"}
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-start">
      <button
        type="button"
        onClick={onBackToInput}
        className="rounded-md border border-border bg-panelAlt px-4 py-2 text-sm font-semibold text-textMain transition hover:border-accent/40 hover:text-accent"
      >
        {"<- Back to Input"}
      </button>
    </div>
  );
}
