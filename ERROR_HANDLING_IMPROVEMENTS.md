# Error Handling Improvements - Documentation

## Overview

This document describes the comprehensive error handling redesign implemented to ensure the UI always shows structured failure reports instead of generic "Failed to fetch" messages.

## Backend Changes

### 1. Structured Error Schema (`app/schemas.py`)

Added new error-related enums and response model:

- **`ErrorStage`**: Identifies where the error occurred (parse, compile, verify, repair, model, network, internal)
- **`ErrorType`**: Classifies the type of error (timeout, model_failure, invalid_output, internal_error, etc.)
- **`StructuredErrorResponse`**: Always-returned JSON schema containing:
  - `status`: "success" or "failure"
  - `stage`: Pipeline stage where error occurred
  - `error_type`: Classification of error
  - `message`: Human-readable explanation
  - `lean_output`: Optional Lean code if available
  - `diagnostics`: Optional debug trace
  - `traceback`: Full server-side traceback for debugging

### 2. Global Exception Handler (`app/main.py`)

Implemented a FastAPI global exception handler that:
- Catches ALL unhandled exceptions
- Logs full traceback server-side
- Returns structured JSON error (never plain text or HTTP 500 without JSON)
- Never lets requests die silently

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Logs traceback, returns StructuredErrorResponse
```

### 3. Enhanced /formalize Endpoint (`app/main.py`)

The `/formalize` endpoint now:
- Wraps orchestrator initialization in try-catch
- Handles `TimeoutError` specifically with structured timeout response
- Categorizes exceptions by stage (parse/compile/model/verify)
- Returns appropriate HTTP status codes with structured JSON
- Never returns empty responses or plain text errors

### 4. Timeout Handling

Added timeout detection for:
- Lean verification operations
- Model API calls
- Returns specific error message: "Verification timed out. Proof search exceeded resource limits."

## Frontend Changes

### 1. API Client Enhancements (`frontend/src/api.ts`)

Added comprehensive error handling:

- **`StructuredError` interface**: TypeScript type matching backend schema
- **`checkBackendHealth()`**: Pings `/health` endpoint before requests
- **Automatic retry logic**: Retries once on network/transient errors
- **Structured error parsing**: Always parses JSON error responses
- **Network failure detection**: Separate handling for "Backend offline" vs other errors

### 2. Workspace Controller Updates (`workspace/AppWorkspaceController.tsx`)

Enhanced error state management:
- Added `structuredError` state variable
- Parse structured errors from API
- Set appropriate user-facing messages based on error type
- Pass structured error to UI components

### 3. Debug Panel Component (`components/DebugPanel.tsx`)

New collapsible debug panel showing:
- Error status, stage, and type badges
- Human-readable error message
- Diagnostics information
- Lean output (if available)
- Full server traceback (expandable)
- Raw JSON response

Features:
- Hidden by default (expandable)
- Color-coded error badges
- Syntax-preserved code blocks
- Scrollable content areas

### 4. UI Integration (`workspace/InputWorkspace.tsx`)

Integrated debug panel into error display:
- Shows user-friendly error message in red banner
- Expandable technical diagnostics below
- Both displayed only when errors occur

## Error Flow

### Success Flow
1. User submits statement
2. Backend health check passes
3. Request sent to `/formalize`
4. Backend processes successfully
5. Returns `FormalizeResponse` with results

### Error Flow
1. User submits statement
2. Backend health check (if fails → network error)
3. Request sent to `/formalize`
4. Backend catches exception (any stage)
5. Returns `StructuredErrorResponse` with:
   - Stage where error occurred
   - Error classification
   - User-friendly message
   - Technical diagnostics
6. Frontend parses structured error
7. Sets appropriate UI state
8. Displays error banner + debug panel
9. Retries automatically once if applicable

## Error Types and Handling

| Error Type | Stage | User Message | Auto-Retry |
|------------|-------|-------------|------------|
| Network | network | "Backend offline. Cannot reach verification server." | No |
| Timeout | verify | "Verification timed out. Proof search exceeded resource limits." | No |
| Parse Error | parse | "Parse error: [details]" | No |
| Model Failure | model | "Model failure: [details]" | Yes |
| Compile Error | compile | "Compilation failed: [details]" | No |
| Internal Error | internal | "Internal server error: [details]" | Yes |

## Testing

### Backend Tests (`backend/tests/test_sanity.py`)

Sanity check tests for simple valid statements:
- Arithmetic identity: `n + 0 = n`
- Commutative addition: `0 + n = n`
- Transitivity of equality: `a = b ∧ b = c → a = c`
- Implication logic: `P ∧ Q → P`

Run tests:
```bash
cd backend
pytest tests/test_sanity.py -v
```

## Benefits

1. **No more "Failed to fetch"**: Users always see meaningful error messages
2. **Structured debugging**: Technical details available via expandable panel
3. **Stage identification**: Know exactly where pipeline failed
4. **Automatic recovery**: Retry logic handles transient failures
5. **Health monitoring**: Pre-flight check prevents wasted requests
6. **Complete traceability**: Full server logs for debugging
7. **Better UX**: Clear, actionable error messages

## Configuration

No additional configuration required. Error handling is built into the core pipeline.

Optional: Review backend logs for detailed tracebacks (logged server-side automatically).

## Future Enhancements

Potential improvements:
- Error analytics/telemetry
- User feedback on error messages
- Suggested fixes for common errors
- Rate limiting on retries
- Circuit breaker pattern for repeated failures
