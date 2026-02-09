interface CopyProofButtonProps {
  leanCode: string;
  onCopied: () => void;
}

export function CopyProofButton({ leanCode, onCopied }: CopyProofButtonProps) {
  async function onCopyClick() {
    if (!leanCode.trim()) {
      return;
    }

    try {
      await navigator.clipboard.writeText(leanCode);
      onCopied();
    } catch {
      // Clipboard permission is browser-dependent; fail silently in UI.
    }
  }

  return (
    <button
      type="button"
      onClick={onCopyClick}
      disabled={!leanCode.trim()}
      className="rounded border border-border bg-panel px-3 py-1.5 text-xs font-semibold text-textMain transition hover:border-accent/40 hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
    >
      Copy Lean Code
    </button>
  );
}
