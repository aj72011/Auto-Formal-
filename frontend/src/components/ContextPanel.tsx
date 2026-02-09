import ReactMarkdown from "react-markdown";
import type { FormalizeResponse, VerificationRunState } from "../types";
import { LeanContextTab } from "./LeanContextTab";
import { ResearchContextSection } from "./ResearchContextSection";
import type { ResultTabKey } from "./ResultTabsController";
import { VerificationReportPanel } from "./VerificationReportPanel";

interface ContextPanelProps {
  activeTab: ResultTabKey;
  result: FormalizeResponse | null;
  runState: VerificationRunState;
  selectedKnowledgeId: string | null;
}

function markdownFromKnowledge(result: FormalizeResponse, selectedKnowledgeId: string | null): string {
  const selected =
    result.knowledge_entries.find((entry) => entry.id === selectedKnowledgeId) ??
    result.knowledge_entries[0] ??
    null;

  if (!selected) {
    return "Select an annotated Lean line to inspect theorem background and research context.";
  }

  return [
    `## ${selected.theorem_name}`,
    "",
    "**Summary**",
    selected.summary,
    "",
    "**Detailed Explanation**",
    selected.detailed_explanation,
    "",
    "**Research Context**",
    selected.research_context,
    "",
    "**Paper Notes**",
    selected.paper_notes,
    "",
    "**Related Theorems**",
    selected.related_theorems.length > 0
      ? selected.related_theorems.map((item) => `- ${item}`).join("\n")
      : "- None",
  ].join("\n");
}

function EmptyPanel({ text }: { text: string }) {
  return (
    <div className="rounded-md border border-border bg-panelAlt p-3 text-sm text-textMuted">
      {text}
    </div>
  );
}

export function ContextPanel({
  activeTab,
  result,
  runState,
  selectedKnowledgeId,
}: ContextPanelProps) {
  if (!result) {
    if (runState === "running") {
      return (
        <EmptyPanel text="Verification is running. This panel will populate with explanation, report, and research context as soon as output is available." />
      );
    }
    return <EmptyPanel text="Run formalization from the input workspace to populate this report." />;
  }

  if (activeTab === "proof_output") {
    return (
      <div className="space-y-3 text-sm text-textMuted">
        <p>
          Proof Output is the primary artifact. Use line annotations in the Lean viewer to inspect theorem-level context.
        </p>
        {result.verification.status === "unsupported" ? (
          <div className="rounded-md border border-amber-400/35 bg-amber-500/10 p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-200">Capability Boundary</p>
            <p className="mt-2 text-xs text-amber-100">
              This theorem is logically valid but exceeds the current automated proof capability.
            </p>
            <p className="mt-2 text-xs text-amber-100/90">{result.capability.reason}</p>
          </div>
        ) : null}
        {result.verification.errors.length > 0 ? (
          <div className="rounded-md border border-rose-400/35 bg-rose-500/10 p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-danger">Lean Error Excerpt</p>
            <ul className="mt-2 space-y-1 text-xs text-danger">
              {result.verification.errors.map((error, index) => (
                <li key={`${error.message}-${index}`}>
                  {error.line ? `line ${error.line}: ` : ""}
                  {error.message}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    );
  }

  if (activeTab === "explanation") {
    return (
      <div className="space-y-3">
        <div className="rounded-md border border-border bg-panelAlt p-3 text-sm text-textMuted">
          {result.explanation.summary}
        </div>
        <div className="space-y-2">
          {result.explanation.steps.map((step) => (
            <div
              key={`${step.line_number}-${step.tactic}`}
              className="rounded-md border border-border bg-panelAlt p-3"
            >
              <p className="font-mono text-xs text-accent">line {step.line_number} | {step.tactic}</p>
              <p className="mt-1 text-xs text-textMuted">{step.explanation}</p>
              <p className="mt-2 text-[11px] text-textMuted/80">
                Goal transformation: this step narrows the active goal using {step.tactic}.
              </p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeTab === "lean_context") {
    return <LeanContextTab result={result} />;
  }

  if (activeTab === "know_more") {
    return (
      <div className="space-y-3 text-sm leading-6 text-textMuted">
        <ReactMarkdown>{markdownFromKnowledge(result, selectedKnowledgeId)}</ReactMarkdown>
        <ResearchContextSection />
      </div>
    );
  }

  if (activeTab === "solution_walkthrough") {
    const walkthroughSummary =
      result.verification.status === "unsupported"
        ? "The theorem was classified as outside Tier 1/Tier 2 support. The system stopped before generation and repair to preserve honest capability boundaries."
        : "The statement is translated into Lean syntax, then Lean checks each logical step. If verification fails, the repair loop updates the proof and retries until success or retry budget exhaustion.";
    return (
      <div className="space-y-3 text-sm text-textMuted">
        <div className="rounded-md border border-border bg-panelAlt p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-textMuted">Plain Language Reasoning</p>
          <p className="mt-2">{walkthroughSummary}</p>
        </div>
        <div className="space-y-2">
          {result.explanation.steps.map((step, index) => (
            <div key={`${step.line_number}-${index}`} className="rounded border border-border bg-panelAlt p-2 text-xs">
              Step {index + 1}: {step.explanation}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return <VerificationReportPanel result={result} />;
}
