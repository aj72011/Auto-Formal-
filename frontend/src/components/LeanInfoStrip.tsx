import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

export function LeanInfoStrip() {
  const [expanded, setExpanded] = useState(false);

  return (
    <section className="rounded-lg border border-border bg-panelAlt p-3">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-center justify-between text-left"
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
          What is Lean?
        </p>
        <span className="text-[11px] text-textMuted">
          {expanded ? "Hide" : "Show"}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {expanded ? (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.18 }}
            className="mt-2 space-y-2 text-xs text-textMuted"
          >
            <p>Lean is a theorem prover and a functional programming language.</p>
            <p>Proofs are machine-checked, so accepted proofs satisfy strict logical rules.</p>
            <p>AutoFormal+ compiles natural language statements into Lean 4 proof scripts.</p>
            <p>Verification means Lean accepted the formal proof as mathematically valid.</p>
            <a
              href="https://lean-lang.org/learn/"
              target="_blank"
              rel="noreferrer"
              className="inline-block text-accent hover:underline"
            >
              Learn Lean
            </a>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  );
}
