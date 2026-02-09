import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

export function ResearchContextSection() {
  const [expanded, setExpanded] = useState(false);

  return (
    <section className="rounded-md border border-border bg-panelAlt p-3">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-center justify-between text-left"
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">
          Research Context
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
            <p>
              AutoFormal+ is motivated by automated theorem formalization research in which natural
              language statements are transformed into formal proof assistant code.
            </p>
            <p>
              The system explores an end-to-end natural language to formal proof pipeline with
              deterministic parsing and verification feedback.
            </p>
            <p>
              Repair loops reflect iterative reasoning strategies used in modern neural-symbolic
              theorem proving systems.
            </p>
            <p>
              Explanation layers provide interpretable proof narratives, aligning with research
              directions focused on educational transparency and model auditing.
            </p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  );
}
