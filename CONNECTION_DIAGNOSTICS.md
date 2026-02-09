# Connection Diagnostics & Improvements

## Summary of Changes

### Backend Improvements

1. **Enhanced Startup Logging** (`app/main.py`)
   - Clear ASCII-based startup banner (Windows console compatible)
   - Displays server URLs (local, network, bind)
   - Shows all API endpoint paths
   - Configuration summary (pipeline mode, repair loop, CORS, HF API key)
   - Dependency checks with clear status indicators
   - Final "[SUCCESS] Backend running" message

2. **Improved CORS Configuration** (`app/config.py`, `.env`)
   - Added support for port 5175 (in addition to 5173, 5174)
   - Allows all localhost development ports
   - Enables credentials and standard headers

3. **Guaranteed Health Endpoint** (`app/main.py`)
   - `GET /health` never depends on Lean or model initialization
   - Returns JSON: `{"status": "ok", "huggingface_configured": bool, ...}`
   - Always responds even if other services aren't ready

### Frontend Improvements

1. **Fixed Default API URL** (`src/api.ts`)
   - Changed default from port 8000 to 8001 (matches backend)
   - Falls back to `http://localhost:8001` if `VITE_API_BASE_URL` not set
   - Logs configured backend URL on load

2. **Automatic Health Checks** (`src/workspace/AppWorkspaceController.tsx`)
   - Polls `/health` every 3 seconds automatically
   - Initial health check on component mount
   - Pauses during active requests to avoid interference
   - Updates connection state (`backendOnline`) in real-time

3. **Connection Status Banner** (`src/workspace/InputWorkspace.tsx`)
   - Shows "Backend Offline" banner when disconnected
   - Manual "Retry Connection" button
   - Disables "Formalize" button when backend offline
   - Red/rose color scheme for visibility

4. **Enhanced Diagnostics** (`src/api.ts`)
   - Detailed console logging for all health checks
   - Network error detection and classification
   - CORS mode and credentials properly configured
   - Timeout set to 5 seconds for health checks

5. **Error Classification**
   - Distinguishes: backend offline, timeout, server error, proof failure, unsupported theorem
   - Never shows generic "failure" messages
   - Clear user-facing messages for each error type

## Verification Checklist

### Backend Startup
```powershell
cd AutoFormalAI/backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Expected output:
```
======================================================================
         AutoFormal+ Backend Starting...
======================================================================

SERVER URLS:
   Local:    http://localhost:8001
   Network:  http://<your-ip>:8001
   Bind:     http://0.0.0.0:8001

API ENDPOINTS:
   Health:     http://localhost:8001/health
   Docs:       http://localhost:8001/docs
   Formalize:  http://localhost:8001/formalize
   Knowledge:  http://localhost:8001/knowledge

CONFIGURATION:
   Pipeline Mode:  ast
   Repair Loop:    enabled
   CORS Origins:   http://localhost:5173, http://localhost:5174, http://localhost:5175
   HF API Key:     [OK] configured

DEPENDENCY CHECKS:
   Lean 4:         [OK] Lean (version 4.x.x, ...)
   Knowledge Base: [OK] loaded

======================================================================
[SUCCESS] Backend running on http://localhost:8001
======================================================================
```

### Frontend Startup
```powershell
cd AutoFormalAI/frontend
npm install
npm run dev
```

Expected behavior:
- Opens on `http://localhost:5175` (or similar)
- Console shows: `[API] Configured backend URL: http://localhost:8001`
- Initial health check runs immediately
- Health checks repeat every 3 seconds
- If backend is running: no offline banner
- If backend is stopped: "Backend Offline" banner appears with retry button

### Manual Testing

1. **Backend Running**
   - Visit `http://localhost:5175`
   - No "Backend Offline" banner should appear
   - "Formalize" button should be enabled
   - Console shows: `[Health Check] ✓ Backend online`

2. **Backend Stopped**
   - Stop backend (Ctrl+C in terminal)
   - Within 3 seconds, UI shows "Backend Offline" banner
   - "Formalize" button becomes disabled
   - Click "Retry Connection" → shows "Checking..."
   - Console shows: `[Health Check] ✗ Failed to reach backend`

3. **Backend Restart**
   - Restart backend
   - Within 3 seconds, offline banner disappears automatically
   - "Formalize" button becomes enabled
   - Console shows: `[Health Check] ✓ Backend online`

4. **Manual Retry**
   - While backend is offline, click "Retry Connection"
   - Button shows "Checking..." state
   - If backend still offline, banner remains
   - If backend came online, banner disappears

## Environment Configuration

### Backend (`.env`)
```env
HF_API_KEY=your_key_here
HF_MODEL=HuggingFaceH4/zephyr-7b-beta
PIPELINE_MODE=ast
ENABLE_REPAIR_LOOP=true
LEAN_COMMAND=lean
PORT=8001
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175
```

### Frontend (`.env`)
```env
VITE_API_BASE_URL=http://localhost:8001
```

## Troubleshooting

### "Backend Offline" persists despite backend running

1. Check backend is on correct port:
   - Backend logs should show `[SUCCESS] Backend running on http://localhost:8001`
   - Test manually: `curl http://localhost:8001/health`

2. Check CORS configuration:
   - Frontend port must be in `CORS_ORIGINS`
   - Check browser console for CORS errors

3. Check frontend .env:
   - `VITE_API_BASE_URL` must point to backend
   - Restart frontend after .env changes

4. Check browser console:
   - Look for `[Health Check]` logs
   - Network tab should show `/health` requests

### Backend crashes on startup

1. **Unicode Error (Windows)**:
   - Fixed in main.py (removed emoji characters)
   - Uses ASCII-only characters

2. **Port Already in Use**:
   - Change PORT in backend/.env
   - Update VITE_API_BASE_URL in frontend/.env

3. **Lean Not Found**:
   - Backend will show `[WARNING]` but still start
   - Verification won't work without Lean
   - Install from https://lean-lang.org

## Success Indicators

✓ Backend shows clear startup banner with all URLs
✓ Backend `/health` endpoint responds with `{"status": "ok"}`
✓ Frontend console shows successful health checks
✓ No "Backend Offline" banner when both running
✓ "Formalize" button is enabled
✓ Automatic reconnection when backend restarts
✓ Manual "Retry Connection" button works
✓ Console logs show clear diagnostic information
