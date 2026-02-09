interface TooltipProps {
  title: string;
  body: string;
  visible: boolean;
}

export function Tooltip({ title, body, visible }: TooltipProps) {
  if (!visible) return null;
  return (
    <div className="absolute right-0 top-7 z-20 w-72 rounded-md border border-border bg-panel p-3 text-xs shadow-xl transition-opacity duration-150">
      <p className="font-semibold text-accent">{title}</p>
      <p className="mt-1 whitespace-pre-wrap text-textMuted">{body}</p>
    </div>
  );
}
