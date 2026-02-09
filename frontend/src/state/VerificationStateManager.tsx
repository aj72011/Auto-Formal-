import { createContext, ReactNode, useContext, useMemo, useState } from "react";
import type { VerificationRunState } from "../types";

interface VerificationStateContextValue {
  state: VerificationRunState;
  detail: string;
  setIdle: (detail?: string) => void;
  setRunning: (detail?: string) => void;
  setVerified: (detail?: string) => void;
  setFailed: (detail?: string) => void;
  setUnsupported: (detail?: string) => void;
}

const VerificationStateContext = createContext<VerificationStateContextValue | null>(null);

export function VerificationStateManager({ children }: { children: ReactNode }) {
  const [state, setState] = useState<VerificationRunState>("idle");
  const [detail, setDetail] = useState("Enter a statement to formalize.");

  const value = useMemo<VerificationStateContextValue>(
    () => ({
      state,
      detail,
      setIdle: (nextDetail?: string) => {
        setState("idle");
        setDetail(nextDetail ?? "Enter a statement to formalize.");
      },
      setRunning: (nextDetail?: string) => {
        setState("running");
        setDetail(
          nextDetail ??
            "Translating -> compiling -> verifying -> repairing if needed.",
        );
      },
      setVerified: (nextDetail?: string) => {
        setState("verified");
        setDetail(nextDetail ?? "Proof verified successfully. View results.");
      },
      setFailed: (nextDetail?: string) => {
        setState("failed");
        setDetail(
          nextDetail ??
            "The proof could not be repaired automatically.",
        );
      },
      setUnsupported: (nextDetail?: string) => {
        setState("unsupported");
        setDetail(
          nextDetail ??
            "This theorem is logically valid but exceeds the current automated proof capability.",
        );
      },
    }),
    [detail, state],
  );

  return (
    <VerificationStateContext.Provider value={value}>
      {children}
    </VerificationStateContext.Provider>
  );
}

export function useVerificationState() {
  const context = useContext(VerificationStateContext);
  if (!context) {
    throw new Error("useVerificationState must be used inside VerificationStateManager.");
  }
  return context;
}
