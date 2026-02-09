import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { ContextPanel } from "../components/ContextPanel";
import { FocusModeToggle } from "../components/FocusModeToggle";
import { MetricCard } from "../components/MetricCard";
import { ProofViewer } from "../components/ProofViewer";
import { ResultTabKey, ResultTabsController } from "../components/ResultTabsController";
import { StatusBanner } from "../components/StatusBanner";
import { ThemeMode, ThemeToggle } from "../components/ThemeToggle";
import { VerificationTimeline } from "../components/VerificationTimeline";
import type { AnnotatedLinePayload, FormalizeResponse, VerificationRunState } from "../types";
import { NavigationButtons } from "./NavigationButtons";

interface ResultWorkspaceProps {
  result: FormalizeResponse | null;
  runState: VerificationRunState;
  runDetail: string;
  selectedLine?: number;
  selectedKnowledgeId: string | null;
  theme: ThemeMode;
  onThemeToggle: () => void;
  onSelectLine: (line: AnnotatedLinePayload) => void;
  onBackToInput: () => void;
}

export function ResultWorkspace({
  result,
  runState,
  runDetail,
  selectedLine,
  selectedKnowledgeId,
  theme,
  onThemeToggle,
  onSelectLine,
  onBackToInput,
}: ResultWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<ResultTabKey>("proof_output");
  const [focusMode, setFocusMode] = useState(false);

  return (
    <div className="h-full w-full overflow-hidden bg-surface">
      <div className="mx-auto flex h-full min-h-0 w-full max-w-[1560px] flex-col gap-3 px-4 py-4 lg:px-6">
        <div className="flex items-center justify-between gap-3">
          <NavigationButtons
            page="result"
            canViewResults
            onViewResults={() => {}}
            onBackToInput={onBackToInput}
          />
          <div className="flex items-center gap-2">
            <ThemeToggle theme={theme} onToggle={onThemeToggle} />
            <FocusModeToggle enabled={focusMode} onToggle={() => setFocusMode((current) => !current)} />
          </div>
        </div>

        <StatusBanner
          context="result"
          runState={runState}
          detail={runDetail}
          verificationStatus={result?.verification.status}
        />

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:max-w-[760px]">
          <MetricCard label="Request ID" value={result?.request_id ?? "pending"} />
          <MetricCard label="Attempts" value={result ? `${result.attempts_used}` : "-"} />
        </div>

        <VerificationTimeline result={result} runState={runState} />

        <motion.div
          layout
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="min-h-0 flex-1"
        >
          <div className="grid h-full min-h-0 grid-cols-1 gap-4 xl:grid-cols-12">
            <motion.div
              initial={{ opacity: 0, scale: 0.985 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
              layout
              className={`${focusMode ? "xl:col-span-12" : "xl:col-span-8"} min-h-0`}
            >
              <ProofViewer
                result={result}
                runState={runState}
                selectedLine={selectedLine}
                onSelectLine={onSelectLine}
                focusMode={focusMode}
              />
            </motion.div>

            <AnimatePresence initial={false}>
              {!focusMode ? (
                <motion.aside
                  key="result-context-panel"
                  initial={{ opacity: 0, x: 22 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 16 }}
                  transition={{ duration: 0.22 }}
                  className="min-h-0 xl:col-span-4"
                >
                  <div className="flex h-full min-h-0 flex-col rounded-md border border-border bg-panel p-3">
                    <ResultTabsController activeTab={activeTab} onChange={setActiveTab} />
                    <div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-1">
                      <ContextPanel
                        activeTab={activeTab}
                        result={result}
                        runState={runState}
                        selectedKnowledgeId={selectedKnowledgeId}
                      />
                    </div>
                  </div>
                </motion.aside>
              ) : null}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
