import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { checkBackendHealth, formalizeStatement, StructuredError } from "../api";
import { ThemeMode } from "../components/ThemeToggle";
import { useVerificationState } from "../state/VerificationStateManager";
import type { AnnotatedLinePayload, FormalizeResponse } from "../types";
import { InputWorkspace } from "./InputWorkspace";
import { PageTransitionContainer } from "./PageTransitionContainer";
import { ResultWorkspace } from "./ResultWorkspace";

const EXAMPLES = [
  "For every natural number n, n + 0 = n.",
  "For every natural number n, 0 + n = n.",
  "For propositions P and Q, if P and Q then P.",
  "For all integers a b c, if a = b and b = c then a = c.",
];

const THEME_STORAGE_KEY = "autoformal_theme";
const HEALTH_CHECK_INTERVAL = 3000; // 3 seconds

type WorkspacePage = "input" | "result";

function readInitialTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "dark";
  }
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
  return saved === "light" ? "light" : "dark";
}

export function AppWorkspaceController() {
  const [page, setPage] = useState<WorkspacePage>("input");
  const [direction, setDirection] = useState<1 | -1>(1);

  const [statement, setStatement] = useState(EXAMPLES[0]);
  const [mode, setMode] = useState<"ast" | "direct">("ast");
  const [repairEnabled, setRepairEnabled] = useState(true);
  const [result, setResult] = useState<FormalizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [structuredError, setStructuredError] = useState<StructuredError | null>(null);
  const [selectedKnowledgeId, setSelectedKnowledgeId] = useState<string | null>(null);
  const [selectedLine, setSelectedLine] = useState<number |undefined>(undefined);
  const [theme, setTheme] = useState<ThemeMode>(readInitialTheme);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [checkingConnection, setCheckingConnection] = useState(false);

  const {
    state: runState,
    detail,
    setIdle,
    setRunning,
    setVerified,
    setFailed,
    setUnsupported,
  } = useVerificationState();

  // Check backend health
  const checkHealth = useCallback(async () => {
    const isHealthy = await checkBackendHealth();
    setBackendOnline(isHealthy);
    return isHealthy;
  }, []);

  // Initial health check on mount
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Periodic health check
  useEffect(() => {
    const interval = setInterval(() => {
      // Only auto-check if not currently loading
      if (!loading) {
        checkHealth();
      }
    }, HEALTH_CHECK_INTERVAL);

    return () => clearInterval(interval);
  }, [checkHealth, loading]);

  // Manual retry connection
  async function retryConnection() {
    setCheckingConnection(true);
    await checkHealth();
    setCheckingConnection(false);
  }

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("theme-light", theme === "light");
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const canViewResults = useMemo(
    () =>
      Boolean(result) &&
      (runState === "verified" || runState === "failed" || runState === "unsupported"),
    [result, runState],
  );

  function onStatementChange(value: string) {
    setStatement(value);
    setError("");
    setStructuredError(null);

    if (!loading) {
      setIdle(value.trim() ? "Statement ready. Press Formalize to run Lean verification." : undefined);
    }

    if (result && value.trim() !== result.original_statement.trim()) {
      setResult(null);
      setSelectedKnowledgeId(null);
      setSelectedLine(undefined);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!statement.trim()) {
      setError("Please enter a statement.");
      setIdle();
      return;
    }

    setLoading(true);
    setError("");
    setStructuredError(null);
    setResult(null);
    setSelectedKnowledgeId(null);
    setSelectedLine(undefined);
    setRunning();

    try {
      const payload = await formalizeStatement({
        statement: statement.trim(),
        mode,
        enable_repair_loop: repairEnabled,
      });

      setResult(payload);
      if (payload.capability?.status === "unsupported" || payload.verification.status === "unsupported") {
        const message =
          payload.capability?.reason ||
          "This theorem is logically valid but exceeds the current automated proof capability.";
        setError(message);
        setUnsupported(
          "This theorem is logically valid but exceeds the current automated proof capability.",
        );
        return;
      }

      const modelStatus = payload.model_response?.status;
      if (modelStatus === "failure" || modelStatus === "unsupported") {
        const message =
          payload.model_response?.error_message ||
          payload.model_response?.reason ||
          "Model did not produce usable Lean output.";
        setError(message);
        setFailed(message);
        return;
      }

      const firstKnowledge = payload.knowledge_entries[0];
      if (firstKnowledge) {
        setSelectedKnowledgeId(firstKnowledge.id);
      }

      if (payload.verification.status === "verified") {
        setVerified();
      } else {
        setFailed();
      }
    } catch (err) {
      // Handle structured errors from backend
      if ((err as StructuredError).status === "failure") {
        const structErr = err as StructuredError;
        setStructuredError(structErr);
        
        // Set appropriate user-facing message based on error type
        let userMessage = structErr.message;
        
        if (structErr.stage === "network") {
          userMessage = "Backend offline. Cannot reach verification server.";
          setError(userMessage);
          setFailed(userMessage);
        } else if (structErr.error_type === "timeout") {
          userMessage = "Verification timed out. Proof search exceeded resource limits.";
          setError(userMessage);
          setFailed(userMessage);
        } else if (structErr.stage === "parse") {
          userMessage = `Parse error: ${structErr.message}`;
          setError(userMessage);
          setFailed(userMessage);
        } else if (structErr.stage === "model") {
          userMessage = `Model failure: ${structErr.message}`;
          setError(userMessage);
          setFailed(userMessage);
        } else {
          setError(structErr.message);
          setFailed(structErr.message);
        }
      } else {
        // Fallback for non-structured errors
        const message = err instanceof Error ? err.message : "Unexpected request failure.";
        setError(message);
        setFailed("Verification could not complete due to a request failure.");
      }
    } finally {
      setLoading(false);
    }
  }

  function goToResults() {
    if (!canViewResults) return;
    setDirection(1);
    setPage("result");
  }

  function goToInput() {
    setDirection(-1);
    setPage("input");
  }

  function onSelectLine(line: AnnotatedLinePayload) {
    setSelectedLine(line.line_number);
    if (line.knowledge_id) {
      setSelectedKnowledgeId(line.knowledge_id);
    }
  }

  return (
    <div className="h-screen w-screen overflow-hidden">
      <PageTransitionContainer pageKey={page} direction={direction}>
        {page === "input" ? (
          <InputWorkspace
            statement={statement}
            mode={mode}
            repairEnabled={repairEnabled}
            loading={loading}
            error={error}
            structuredError={structuredError}
            runState={runState}
            runDetail={detail}
            canViewResults={canViewResults}
            viewLabel={
              runState === "unsupported"
                ? "View Capability Report ->"
                : runState === "failed"
                  ? "View Failure Report ->"
                  : "View Results ->"
            }
            examples={EXAMPLES}
            theme={theme}
            backendOnline={backendOnline}
            checkingConnection={checkingConnection}
            onRetryConnection={retryConnection}
            onThemeToggle={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            onStatementChange={onStatementChange}
            onModeChange={setMode}
            onRepairEnabledChange={setRepairEnabled}
            onSubmit={onSubmit}
            onViewResults={goToResults}
          />
        ) : (
          <ResultWorkspace
            result={result}
            runState={runState}
            runDetail={detail}
            selectedLine={selectedLine}
            selectedKnowledgeId={selectedKnowledgeId}
            theme={theme}
            onThemeToggle={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            onSelectLine={onSelectLine}
            onBackToInput={goToInput}
          />
        )}
      </PageTransitionContainer>
    </div>
  );
}
