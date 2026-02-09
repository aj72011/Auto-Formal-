import { AnimatePresence, motion } from "framer-motion";

interface InputHelperPanelProps {
  minimized: boolean;
}

export function InputHelperPanel({ minimized }: InputHelperPanelProps) {
  return (
    <AnimatePresence mode="wait">
      {!minimized ? (
        <motion.div
          key="expanded"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          className="rounded-lg border border-border bg-panelAlt p-3 text-xs text-textMuted"
        >
          <p>Try a quantified statement like "For every natural number n, n + 0 = n."</p>
          <p className="mt-1">Supports arithmetic, logic, implications, and equalities.</p>
          <p className="mt-1">Press Tab to browse examples and Enter to insert.</p>
        </motion.div>
      ) : (
        <motion.div
          key="collapsed"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="text-[11px] text-textMuted/80"
        >
          Custom input detected. Formalize when ready.
        </motion.div>
      )}
    </AnimatePresence>
  );
}
