import type { FormalizeRequestPayload, FormalizeResponse } from "./types";

/**
 * Backend Discovery and Connection Manager
 * 
 * Features:
 * - Automatic port discovery (8000-8010)
 * - Structured diagnostics
 * - Automatic reconnection
 * - Detailed logging
 */

// Configurable base URL with fallback
let API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? null;
let discoveredBackendURL: string | null = null;

export interface StructuredError {
  status: "success" | "failure";
  stage: "parse" | "compile" | "verify" | "repair" | "model" | "network" | "internal";
  error_type: "none" | "timeout" | "model_failure" | "invalid_output" | "internal_error" | "parse_error" | "compile_error" | "verification_error";
  message: string;
  lean_output?: string;
  diagnostics?: string;
  traceback?: string;
}

export interface BackendDiagnostics {
  reachable: boolean;
  url: string | null;
  reason: 
    | "backend_running"
    | "port_mismatch"
    | "firewall_blocked"
    | "cors_failure"
    | "health_endpoint_unreachable"
    | "backend_process_not_running";
  detailedMessage: string;
  attemptsLog: string[];
}

/**
 * Scan for backend on common ports
 */
async function discoverBackend(): Promise<string | null> {
  console.log("[Backend Discovery] Starting port scan...");
  
  const hosts = ["http://localhost", "http://127.0.0.1"];
  const ports = [8001, 8000, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010];
  
  for (const host of hosts) {
    for (const port of ports) {
      const url = `${host}:${port}`;
      try {
        console.log(`[Backend Discovery] Trying ${url}/health...`);
        const response = await fetch(`${url}/health`, {
          method: "GET",
          mode: "cors",
          credentials: "omit",
          signal: AbortSignal.timeout(2000), // 2 second timeout per port
        });
        
        if (response.ok) {
          console.log(`[Backend Discovery] ✓ Found backend at ${url}`);
          return url;
        }
      } catch (error) {
        // Port not reachable, try next
        continue;
      }
    }
  }
  
  console.error("[Backend Discovery] ✗ No backend found on any port");
  return null;
}

/**
 * Get backend URL with automatic discovery
 */
async function getBackendURL(): Promise<string | null> {
  // If manually configured, try that first
  if (API_BASE_URL) {
    console.log(`[Backend] Using configured URL: ${API_BASE_URL}`);
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        signal: AbortSignal.timeout(3000),
      });
      
      if (response.ok) {
        console.log(`[Backend] ✓ Configured backend reachable`);
        discoveredBackendURL = API_BASE_URL;
        return API_BASE_URL;
      }
    } catch (error) {
      console.warn(`[Backend] Configured URL ${API_BASE_URL} unreachable, attempting discovery...`);
    }
  }
  
  // If already discovered, use that
  if (discoveredBackendURL) {
    console.log(`[Backend] Using previously discovered URL: ${discoveredBackendURL}`);
    return discoveredBackendURL;
  }
  
  // Attempt discovery
  discoveredBackendURL = await discoverBackend();
  return discoveredBackendURL;
}

/**
 * Perform comprehensive backend diagnostics
 */
export async function diagnoseBackendConnection(): Promise<BackendDiagnostics> {
  const attemptsLog: string[] = [];
  
  // Try to get backend URL
  const backendURL = await getBackendURL();
  
  if (backendURL) {
    attemptsLog.push(`✓ Backend found at ${backendURL}`);
    return {
      reachable: true,
      url: backendURL,
      reason: "backend_running",
      detailedMessage: `Backend is running on ${backendURL}`,
      attemptsLog,
    };
  }
  
  // Diagnostics for failure
  attemptsLog.push(`✗ No backend found on ports 8000-8010`);
  
  // Check if manually configured URL exists but is wrong
  if (API_BASE_URL) {
    attemptsLog.push(`✗ Configured URL ${API_BASE_URL} unreachable`);
    return {
      reachable: false,
      url: null,
      reason: "port_mismatch",
      detailedMessage: `Backend not found at configured URL ${API_BASE_URL}. Check if port is correct.`,
      attemptsLog,
    };
  }
  
  // No backend found at all
  return {
    reachable: false,
    url: null,
    reason: "backend_process_not_running",
    detailedMessage: 
      "No backend detected on ports 8000-8010.\n\n" +
      "Start backend using:\n" +
      "  cd AutoFormalAI/backend\n" +
      "  python -m uvicorn app.main:app --reload --port 8001\n\n" +
      "Or use PowerShell script:\n" +
      "  .\\AutoFormalAI\\scripts\\run_backend.ps1",
    attemptsLog,
  };
}

/**
 * Check backend health with retry logic
 */
export async function checkBackendHealth(): Promise<boolean> {
  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const backendURL = await getBackendURL();
    
    if (!backendURL) {
      if (attempt < maxRetries) {
        console.log(`[Health Check] Backend not found, retrying in ${retryDelay/1000}s (${attempt}/${maxRetries})...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        continue;
      }
      console.error("[Health Check] ✗ Backend unreachable after all retries");
      return false;
    }
    
    try {
      console.log(`[Health Check] Pinging ${backendURL}/health... (attempt ${attempt}/${maxRetries})`);
      const response = await fetch(`${backendURL}/health`, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log(`[Health Check] ✓ Backend online`, data);
        return true;
      }
    } catch (error) {
      console.warn(`[Health Check] Attempt ${attempt} failed:`, error);
      
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        continue;
      }
    }
  }
  
  return false;
}

/**
 * Formalize statement with automatic retry and recovery
 */
export async function formalizeStatement(
  payload: FormalizeRequestPayload,
): Promise<FormalizeResponse> {
  console.log(`[API] Formalize request initiated`);
  console.log(`[API] Payload:`, payload);
  
  // Get backend URL (with discovery if needed)
  const backendURL = await getBackendURL();
  
  if (!backendURL) {
    console.error(`[API] Backend not available`);
    const diagnostics = await diagnoseBackendConnection();
    const networkError: StructuredError = {
      status: "failure",
      stage: "network",
      error_type: "internal_error",
      message: "Backend not running",
      diagnostics: diagnostics.detailedMessage,
    };
    throw networkError;
  }
  
  console.log(`[API] Using backend URL: ${backendURL}`);
  
  // Try request with automatic retry
  const maxAttempts = 2;
  let lastError: StructuredError | Error | null = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    console.log(`[API] Attempt ${attempt}/${maxAttempts}`);
    try {
      const response = await fetch(`${backendURL}/formalize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000), // 60 second timeout
      });

      console.log(`[API] Response status: ${response.status}`);

      // Always try to parse JSON response
      const data = await response.json();
      console.log(`[API] Response data:`, data);

      // Check if this is a structured error response
      if (!response.ok || data.status === "failure") {
        const structuredError: StructuredError = {
          status: data.status || "failure",
          stage: data.stage || "internal",
          error_type: data.error_type || "internal_error",
          message: data.message || data.detail || "Formalization request failed.",
          lean_output: data.lean_output || "",
          diagnostics: data.diagnostics || "",
          traceback: data.traceback || "",
        };
        lastError = structuredError;

        console.error(`[API] Structured error received:`, structuredError);

        // Don't retry on certain error types
        if (data.error_type === "parse_error" || data.error_type === "invalid_output") {
          console.log(`[API] Not retrying ${data.error_type}`);
          throw structuredError;
        }

        // Retry on other errors
        if (attempt < maxAttempts) {
          console.log(`[API] Retrying in 1 second...`);
          await new Promise(resolve => setTimeout(resolve, 1000));
          continue;
        }

        throw structuredError;
      }

      // Success
      console.log(`[API] Request successful`);
      return data as FormalizeResponse;
    } catch (error) {
      if ((error as StructuredError).status === "failure") {
        // This is our structured error - rethrow it
        throw error;
      }

      // Network or parse error
      console.error(`[API] Network/fetch error:`, error);
      
      // Try to rediscover backend
      if (error instanceof TypeError && String(error).includes("fetch")) {
        console.log(`[API] Network error detected, attempting backend rediscovery...`);
        discoveredBackendURL = null; // Reset discovered URL
        const newBackendURL = await getBackendURL();
        if (newBackendURL && newBackendURL !== backendURL) {
          console.log(`[API] Backend rediscovered at ${newBackendURL}, retrying...`);
          // This will retry with the new URL on next attempt
        }
      }
      
      lastError = {
        status: "failure",
        stage: "network",
        error_type: "internal_error",
        message: error instanceof Error ? error.message : "Failed to fetch",
        diagnostics: "Network request failed. Backend may have restarted on a different port.",
      };

      if (attempt < maxAttempts) {
        console.log(`[API] Retrying due to network error...`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        continue;
      }
    }
  }

  throw lastError || new Error("Request failed after retries");
}

export async function fetchKnowledgeBase(): Promise<{ entries: unknown[] }> {
  const backendURL = await getBackendURL();
  
  if (!backendURL) {
    throw new Error("Backend not available. Cannot fetch knowledge base.");
  }
  
  const response = await fetch(`${backendURL}/knowledge`);
  if (!response.ok) {
    throw new Error("Failed to load knowledge base.");
  }
  return response.json();
}

// Initialize backend discovery on module load
console.log("[API] API module loaded, initializing backend connection...");
getBackendURL().then(url => {
  if (url) {
    console.log(`[API] Initial backend URL: ${url}`);
  } else {
    console.warn("[API] No backend found during initialization");
  }
}).catch(error => {
  console.error("[API] Error during initial backend discovery:", error);
});
