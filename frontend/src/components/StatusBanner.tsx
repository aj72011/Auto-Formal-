import { AnimatePresence, motion } from "framer-motion";
import type { VerificationRunState, VerificationStatus } from "../types";

interface StatusBannerProps {
  context: "input" | "result";
  runState: VerificationRunState;
  detail?: string;
  verificationStatus?: VerificationStatus;
}

interface BannerModel {
  title: string;
  subtitle: string;
  tone: string;
  pulse?: boolean;
}

function modelFromState(
  context: "input" | "result",
  runState: VerificationRunState,
  detail?: string,
  verificationStatus?: VerificationStatus,
): BannerModel {
  const resolved =
    verificationStatus ??
    (runState === "verified" || runState === "failed" || runState === "unsupported"
      ? runState
      : undefined);

  if (context === "input") {
    if (runState === "running") {
      return {
        title: "Running Lean verification...",
        subtitle: detail ?? "Translating -> compiling -> verifying -> repairing if needed.",
        tone: "border-accent/45 bg-accent/10 text-accent",
        pulse: true,
      };
    }

    if (runState === "verified") {
      return {
        title: "Proof verified successfully. View results.",
        subtitle: detail ?? "The generated Lean proof compiled successfully.",
        tone: "border-emerald-400/45 bg-emerald-500/10 text-success",
      };
    }

    if (runState === "failed") {
      return {
        title: "Verification failed.",
        subtitle: detail ?? "The proof could not be repaired automatically.",
        tone: "border-rose-400/45 bg-rose-500/10 text-danger",
      };
    }

    if (runState === "unsupported") {
      return {
        title: "Capability boundary reached.",
        subtitle:
          detail ??
          "This theorem is logically valid but exceeds the current automated proof capability.",
        tone: "border-amber-400/45 bg-amber-500/10 text-amber-200",
      };
    }

    return {
      title: "Enter a statement to formalize.",
      subtitle: "The system will parse, compile, verify, and generate a proof report.",
      tone: "border-border bg-panelAlt text-textMuted",
    };
  }

  if (runState === "running") {
    return {
      title: "Verification in progress...",
      subtitle: detail ?? "Pipeline is currently executing and updating report artifacts.",
      tone: "border-accent/45 bg-accent/10 text-accent",
      pulse: true,
    };
  }

  if (resolved === "verified") {
    return {
      title: "VERIFIED | Lean proof compiled successfully.",
      subtitle: "Formalization completed and machine-checkable proof is available.",
      tone: "border-emerald-400/50 bg-emerald-500/10 text-success",
    };
  }

  if (resolved === "failed") {
    return {
      title: "VERIFICATION FAILED",
      subtitle: "Automatic repair attempts exhausted.",
      tone: "border-rose-400/50 bg-rose-500/10 text-danger",
    };
  }

  if (resolved === "unsupported") {
    return {
      title: "UNSUPPORTED | Outside Current Proof Subset",
      subtitle:
        detail ??
        "This theorem is logically valid but exceeds the current automated proof capability.",
      tone: "border-amber-400/50 bg-amber-500/10 text-amber-200",
    };
  }

  return {
    title: "No verification run yet.",
    subtitle: "Start a run from the input workspace to populate this report.",
    tone: "border-border bg-panelAlt text-textMuted",
  };
}

export function StatusBanner({
  context,
  runState,
  detail,
  verificationStatus,
}: StatusBannerProps) {
  const model = modelFromState(context, runState, detail, verificationStatus);

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={`${context}-${runState}-${verificationStatus ?? "none"}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.2 }}
        className={`rounded-lg border px-4 py-3 ${model.tone} ${context === "result" ? "shadow-sm" : ""}`}
      >
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 inline-flex h-2.5 w-2.5 rounded-full ${
              model.pulse ? "animate-pulse bg-current" : "bg-current/80"
            }`}
          />
          <div>
            <p className={`${context === "result" ? "text-sm font-semibold" : "text-sm font-medium"}`}>
              {model.title}
            </p>
            <p className="mt-1 text-xs text-current/85">{model.subtitle}</p>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
