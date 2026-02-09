from __future__ import annotations

import logging
import socket
import subprocess
import time
import traceback as tb
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import BASE_DIR, settings
from app.pipeline.evaluator import run_research_evaluation
from app.pipeline.orchestrator import AutoFormalOrchestrator
from app.schemas import (
    ErrorStage,
    ErrorType,
    EvaluateRequest,
    EvaluateResponse,
    FormalizeRequest,
    FormalizeResponse,
    HealthResponse,
    StructuredErrorResponse,
    VerificationStatus,
)
from app.services.telemetry import TelemetryLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="AutoFormal+ API",
    version="1.0.0",
    description=(
        "Research-grade natural language to Lean 4 formal verification platform with "
        "modular reasoning pipeline, repair loops, explanations, and evaluation tooling."
    ),
)

# CORS Configuration - Allow all localhost origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler that ensures ALL exceptions are returned as structured JSON.
    Never allows HTTP 500 without JSON. Never lets requests die silently.
    """
    traceback_str = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception on {request.url}: {traceback_str}")
    
    error_response = StructuredErrorResponse(
        status="failure",
        stage=ErrorStage.internal,
        error_type=ErrorType.internal_error,
        message=f"Internal server error: {str(exc)}",
        lean_output="",
        diagnostics=str(exc),
        traceback=traceback_str,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


telemetry = TelemetryLogger(settings.telemetry_file)


@app.on_event("startup")
async def startup_event():
    """Print clear startup information and validate dependencies."""
    # Get local IP address
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "unknown"
    
    print("\n" + "=" * 70)
    print("         AutoFormal+ Backend Starting...")
    print("=" * 70)
    print()
    print("SERVER URLS:")
    print(f"   Local:    http://localhost:{settings.port}")
    print(f"   Network:  http://{local_ip}:{settings.port}")
    print(f"   Bind:     http://0.0.0.0:{settings.port}")
    print()
    print("API ENDPOINTS:")
    print(f"   Health:     http://localhost:{settings.port}/health")
    print(f"   Docs:       http://localhost:{settings.port}/docs")
    print(f"   Formalize:  http://localhost:{settings.port}/formalize")
    print(f"   Knowledge:  http://localhost:{settings.port}/knowledge")
    print()
    print("CONFIGURATION:")
    print(f"   Pipeline Mode:  {settings.pipeline_mode}")
    print(f"   Repair Loop:    {'enabled' if settings.enable_repair_loop else 'disabled'}")
    print(f"   CORS Origins:   {', '.join(settings.cors_origin_list)}")
    print(f"   HF API Key:     {'[OK] configured' if settings.hf_api_key else '[WARNING] NOT SET - model calls will fail'}")
    print()
    print("DEPENDENCY CHECKS:")
    
    # Check if Lean is available
    try:
        result = subprocess.run(
            [settings.lean_command, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lean_version = result.stdout.strip() or result.stderr.strip()
            print(f"   Lean 4:         [OK] {lean_version}")
        else:
            print(f"   Lean 4:         [FAIL] command failed: {settings.lean_command}")
            print(f"                   [WARNING] Proof verification will not work")
    except FileNotFoundError:
        print(f"   Lean 4:         [NOT FOUND] install from https://lean-lang.org")
        print(f"                   [WARNING] Proof verification will not work")
    except subprocess.TimeoutExpired:
        print(f"   Lean 4:         [WARNING] timed out - may be slow")
    
    # Check knowledge base file
    if settings.knowledge_base_file.exists():
       print(f"   Knowledge Base: [OK] loaded")
    else:
        print(f"   Knowledge Base: [WARNING] not found at {settings.knowledge_base_file}")
    
    print()
    print("=" * 70)
    print("[SUCCESS] Backend running on http://localhost:{}".format(settings.port))
    print("=" * 70)
    print()


def _build_orchestrator() -> AutoFormalOrchestrator:
    try:
        return AutoFormalOrchestrator(settings=settings, telemetry=telemetry)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize pipeline: {exc}") from exc


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        huggingface_configured=bool(settings.hf_api_key),
        pipeline_mode=settings.pipeline_mode,
        repair_loop_enabled=settings.enable_repair_loop,
    )


@app.get("/config")
def config() -> dict:
    """Return backend configuration for frontend auto-detection."""
    return {
        "backend_url": f"http://127.0.0.1:{settings.port}",
        "port": settings.port,
        "status": "online",
    }


@app.get("/knowledge")
def knowledge() -> dict:
    orchestrator = _build_orchestrator()
    entries = [orchestrator.knowledge_engine.to_dict(item) for item in orchestrator.knowledge_engine.all_entries()]
    return {"entries": [entry for entry in entries if entry is not None]}


@app.get("/telemetry")
def telemetry_events(limit: int = 2000) -> dict:
    return {"events": telemetry.read_all(limit=limit)}


@app.post("/formalize", response_model=FormalizeResponse)
def formalize(request: FormalizeRequest) -> FormalizeResponse | JSONResponse:
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    
    try:
        orchestrator = _build_orchestrator()
    except Exception as exc:
        traceback_str = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(f"Failed to build orchestrator: {traceback_str}")
        error_response = StructuredErrorResponse(
            status="failure",
            stage=ErrorStage.internal,
            error_type=ErrorType.internal_error,
            message=f"Failed to initialize pipeline: {str(exc)}",
            diagnostics="Pipeline initialization failed. Check backend configuration.",
            traceback=traceback_str,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    try:
        pipeline_result = orchestrator.run(
            statement=request.statement,
            request_id=request_id,
            mode=request.mode,
            repair_enabled=request.enable_repair_loop,
        )
    except TimeoutError as exc:
        traceback_str = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(f"Pipeline timeout for request {request_id}: {traceback_str}")
        error_response = StructuredErrorResponse(
            status="failure",
            stage=ErrorStage.verify,
            error_type=ErrorType.timeout,
            message="Verification timed out. Proof search exceeded resource limits.",
            diagnostics=str(exc),
            traceback=traceback_str,
        )
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content=error_response.model_dump(),
        )
    except Exception as exc:
        traceback_str = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(f"Pipeline execution failed for request {request_id}: {traceback_str}")
        
        # Determine stage and error type from exception
        error_stage = ErrorStage.internal
        error_type = ErrorType.internal_error
        
        if "parse" in str(exc).lower() or "semantic" in str(exc).lower():
            error_stage = ErrorStage.parse
            error_type = ErrorType.parse_error
        elif "compile" in str(exc).lower() or "ast" in str(exc).lower():
            error_stage = ErrorStage.compile
            error_type = ErrorType.compile_error
        elif "model" in str(exc).lower() or "generation" in str(exc).lower():
            error_stage = ErrorStage.model
            error_type = ErrorType.model_failure
        elif "verification" in str(exc).lower() or "lean" in str(exc).lower():
            error_stage = ErrorStage.verify
            error_type = ErrorType.verification_error
        
        error_response = StructuredErrorResponse(
            status="failure",
            stage=error_stage,
            error_type=error_type,
            message=f"Pipeline failed: {str(exc)}",
            diagnostics=str(exc),
            traceback=traceback_str,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=error_response.model_dump(),
        )

    total_latency_ms = int((time.perf_counter() - started) * 1000)
    verification_status = pipeline_result.verification.get("status", "failed")

    return FormalizeResponse(
        request_id=request_id,
        original_statement=request.statement,
        mode=pipeline_result.mode,
        ast=pipeline_result.ast.model_dump(),
        capability=pipeline_result.capability,
        model_response=pipeline_result.model_response,
        lean_code=pipeline_result.lean_code,
        verification={
            "status": VerificationStatus(verification_status),
            "errors": pipeline_result.verification.get("errors", []),
            "latency_ms": pipeline_result.verification.get("latency_ms", 0),
            "stdout": pipeline_result.verification.get("stdout", ""),
            "stderr": pipeline_result.verification.get("stderr", ""),
        },
        attempts_used=pipeline_result.attempts_used,
        repair_history=pipeline_result.attempts,
        explanation=pipeline_result.explanation,
        annotated_lines=pipeline_result.annotated_lines,
        knowledge_entries=pipeline_result.knowledge_entries,
        stage_traces=pipeline_result.stage_traces,
        total_latency_ms=total_latency_ms,
    )


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(payload: EvaluateRequest) -> EvaluateResponse:
    orchestrator = _build_orchestrator()
    dataset_path = Path(payload.dataset_path)
    if not dataset_path.is_absolute():
        dataset_path = BASE_DIR / dataset_path

    try:
        summary = run_research_evaluation(
            orchestrator=orchestrator,
            dataset_path=dataset_path,
            output_dir=settings.evaluation_output_dir,
            output_prefix=payload.output_prefix,
            limit=payload.limit,
            protocol=payload.protocol,
            seed=payload.seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc

    return EvaluateResponse(**summary)
