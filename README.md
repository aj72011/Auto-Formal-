# AutoFormal+

AutoFormal+ is a research-grade natural language to Lean 4 formal verification platform.  
It implements a modular pipeline with deterministic semantic parsing, AST compilation, Lean verification, automated repair, proof explanation, knowledge mapping, and evaluation ablations.

## Core Pipeline

1. Natural Language Input
2. Semantic Parser (deterministic AST JSON)
3. Logical AST
4. AST to Lean Compiler (pure deterministic)
5. Lean Verification Engine
6. Error Analyzer
7. Automatic Repair Loop
8. Explanation Generator
9. Knowledge Mapping + Annotated Code
10. UI Rendering (IDE-style research interface)

## Architecture

```text
AutoFormalAI/
  backend/
    app/
      main.py
      config.py
      schemas.py
      pipeline/
        ast_schema.py
        semantic_parser.py
        ast_to_lean_compiler.py
        lean_verification_engine.py
        error_analyzer.py
        proof_generator.py
        repair_loop.py
        explanation_generator.py
        knowledge_mapping.py
        annotator.py
        evaluator.py
        orchestrator.py
      services/
        telemetry.py
    data/
      benchmark_tiered.json
      dataset_seed.json
      knowledge_base.json
      telemetry.jsonl
      evaluation/
    scripts/
      evaluate_dataset.py
    .env.example
    requirements.txt
  frontend/
    src/
      components/
    tailwind.config.ts
    postcss.config.js
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Lean 4 installed and available on PATH (`lean --version`)
- Hugging Face API token (for model-based generation and repair)

## Backend Setup

```powershell
cd "c:\Excuse Generator\AutoFormalAI\backend"
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

Set `backend/.env`:

```env
HF_API_KEY=your_huggingface_api_key_here
HF_MODEL=HuggingFaceH4/zephyr-7b-beta
HF_TIMEOUT_SECONDS=60
PIPELINE_MODE=ast
ENABLE_REPAIR_LOOP=true
MAX_REPAIR_ATTEMPTS=2
LEAN_COMMAND=lean
LEAN_TIMEOUT_SECONDS=60
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175
```

**Important**: The backend URL must match what the frontend expects. By default, the frontend is configured to connect to `http://localhost:8001`.

Run backend:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The backend will display:
- Server URLs (local, network, bind)
- API endpoint paths
- Configuration details
- Dependency checks (Lean 4, knowledge base)
- A clear "[SUCCESS] Backend running" message when ready

## Frontend Setup

```powershell
cd "c:\Excuse Generator\AutoFormalAI\frontend"
copy .env.example .env
```

Set `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8001
```

**Note**: The frontend includes automatic health checks that verify backend connectivity every 3 seconds. If the backend is unreachable, the UI will display an "Backend Offline" banner with a "Retry Connection" button.

Run frontend:

```powershell
& "C:\Program Files\nodejs\npm.cmd" install
& "C:\Program Files\nodejs\npm.cmd" run dev -- --host 0.0.0.0 --port 5174
```

Open `http://localhost:5174` (or the port shown in the Vite output).

**Connection Features:**
- ✓ Automatic health checks every 3 seconds
- ✓ Offline detection with clear error messaging
- ✓ Manual "Retry Connection" button
- ✓ Formalize button disabled when backend is offline
- ✓ All requests include health check before execution

## API

- `GET /health`
- `POST /formalize`
- `POST /evaluate`
- `GET /knowledge`
- `GET /telemetry`

### `POST /formalize` request

```json
{
  "statement": "For every natural number n, n + 0 = n.",
  "mode": "ast",
  "enable_repair_loop": true
}
```

### `POST /formalize` response highlights

- `ast`: deterministic logical AST snapshot
- `lean_code`: final Lean code after repair loop (if needed)
- `verification`: `{ status, errors[], latency_ms, stdout, stderr }`
- `repair_history`: full attempt history with code diffs and error classes
- `explanation`: tactic-level teaching explanation
- `annotated_lines`: line-level code annotations with tooltip metadata
- `knowledge_entries`: research context + paper notes for mapped concepts
- `stage_traces`: per-stage latency and trace payloads

## Evaluation + Ablations

Run local batch evaluation:

```powershell
cd "c:\Excuse Generator\AutoFormalAI\backend"
.\.venv\Scripts\python scripts\evaluate_dataset.py --dataset data\benchmark_tiered.json --protocol both --seed 1729
```

Evaluation protocols:

- `baseline`: direct generation, repair loop off
- `upgraded`: AST compiler + repair loop on
- `both`: runs baseline and upgraded for before/after comparison

Exports:

- CSV row-level report (per theorem with parse/compile/verify/repair/unsupported fields)
- JSON research summary (metrics + protocol comparison + full logs)
- Markdown summary (tables for tier breakdown, failures, capability boundaries)

All outputs are saved under `backend/data/evaluation/`.

Dataset contract (`backend/data/benchmark_tiered.json`):

```json
{
  "id": "S001",
  "statement": "For every natural number n, n + 0 = n.",
  "tier": 1
}
```

Tier definitions:

- Tier 1: trivial rewrite
- Tier 2: single lemma reasoning
- Tier 3: multi-lemma reasoning
- Tier 4: structured proof (induction/complex tactics)

Computed research metrics include:

- success rate per tier
- overall success rate
- unsupported detection accuracy
- repair loop success rate
- average attempts per theorem
- failure distribution
- capability boundary statistics (TP/TN/FP/FN)

## Research Reproducibility

- Telemetry events are appended to `backend/data/telemetry.jsonl`
- Stage logs capture parser, compiler, verification, repair, explanation, and knowledge mapping latencies
- AST snapshots and pipeline completion events are logged for replay and analysis
