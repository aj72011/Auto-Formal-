interface MetricCardProps {
  label: string;
  value: string;
}

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="animate-slideIn rounded-md border border-border bg-panelAlt px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">{label}</p>
      <p className="mt-1 font-mono text-sm text-textMain">{value}</p>
    </div>
  );
}
