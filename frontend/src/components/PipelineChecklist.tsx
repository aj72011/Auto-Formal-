import type { StageTracePayload } from "../types";

interface PipelineChecklistProps {
  stageTraces: StageTracePayload[];
  mode: "ast" | "direct";
}

interface StageItem {
  key: string;
  label: string;
}

const AST_STAGES: StageItem[] = [
  { key: "semantic_parser", label: "Semantic Parser" },
  { key: "capability_classifier", label: "Capability Classifier" },
  { key: "ast_to_lean_compiler", label: "Lean Compiler" },
  { key: "verification_and_repair_loop", label: "Repair Loop + Verification" },
  { key: "explanation_generator", label: "Explanation Generator" },
  { key: "knowledge_mapping_and_annotation", label: "Knowledge Mapping" },
];

const DIRECT_STAGES: StageItem[] = [
  { key: "semantic_parser", label: "Semantic Parser" },
  { key: "capability_classifier", label: "Capability Classifier" },
  { key: "direct_generator", label: "Direct Proof Generator" },
  { key: "verification_and_repair_loop", label: "Repair Loop + Verification" },
  { key: "explanation_generator", label: "Explanation Generator" },
  { key: "knowledge_mapping_and_annotation", label: "Knowledge Mapping" },
];

export function PipelineChecklist({ stageTraces, mode }: PipelineChecklistProps) {
  const completed = new Set(stageTraces.map((trace) => trace.stage));
  const stages = mode === "direct" ? DIRECT_STAGES : AST_STAGES;

  return (
    <section className="rounded-md border border-border bg-panel p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-textMuted">
        Pipeline Checklist
      </h3>
      <ol className="mt-3 space-y-2">
        {stages.map((stage, index) => {
          const done = completed.has(stage.key);
          return (
            <li
              key={stage.key}
              className={`flex items-center gap-3 rounded border px-3 py-2 text-sm ${
                done
                  ? "border-emerald-400/35 bg-emerald-500/10 text-textMain"
                  : "border-border bg-panelAlt text-textMuted"
              }`}
            >
              <span
                className={`inline-flex h-5 w-5 items-center justify-center rounded-full border text-[10px] ${
                  done ? "border-emerald-400/60 text-success" : "border-border text-textMuted"
                }`}
              >
                {done ? "OK" : index + 1}
              </span>
              <span>{stage.label}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
