interface WorkspaceHeaderProps {
  title: string;
  subtitle: string;
}

export function WorkspaceHeader({ title, subtitle }: WorkspaceHeaderProps) {
  return (
    <header className="rounded-xl border border-border/70 bg-gradient-to-b from-panel to-panelAlt p-5 shadow-sm">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent/90">
        AutoFormal+
      </p>
      <h1 className="mt-2 text-xl font-semibold text-textMain">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm text-textMuted">{subtitle}</p>
      <div className="mt-3 rounded-lg border border-border/80 bg-surface/60 p-3 text-xs text-textMuted">
        AutoFormal+ converts natural language statements into Lean 4 formalization, compiles and
        verifies proofs, and reports explanation and repair history in one workspace.
      </div>
    </header>
  );
}
