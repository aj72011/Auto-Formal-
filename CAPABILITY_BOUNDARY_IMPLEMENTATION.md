# Capability Boundary Enhancement - Implementation Guide

## Overview

This document outlines the complete implementation for transforming capability boundaries from hard failures into educational "Guided Manual Proof Mode" experiences.

## Architecture Changes

### Phase 1: Backend Schema & Types ✅ COMPLETED

**Files Modified:**
- [`app/schemas.py`](app/schemas.py)

**Changes:**
1. Added `capability_boundary` to `VerificationStatus` enum
2. Created `CapabilityBoundaryPayload` with:
   - `missing_lemmas: list[str]`
   - `proof_depth_estimate: int`
   - `recommended_topics: list[str]`
   - `subgoals: list[str]`
   - `lean_skeleton: str`
   - `human_explanation: str`
3. Extended `CapabilityPayload` with:
   - Status now includes `"capability_boundary"`
   - Added `boundary_info: CapabilityBoundaryPayload | None`

### Phase 2: Capability Classifier Enhancement

**File:** `app/pipeline/capability_classifier.py`

**Required Changes:**

```python
def _generate_boundary_guidance(
    self,
    tier: int,
    statement: str,
    ast: LogicalAST,
    signals: list[str]
) -> CapabilityBoundaryPayload:
    """
    Generate educational guidance for capability boundary cases.
    """
    from app.schemas import CapabilityBoundaryPayload
    
    missing_lemmas = []
    recommended_topics = []
    subgoals = []
    proof_depth = 0
    
    if tier == 4:  # Structured proof / induction
        missing_lemmas = [
            "Nat.add_zero",
            "Nat.zero_add",
            "Nat.succ_add",
            "Nat.add_succ"
        ]
        recommended_topics = [
            "Mathematical induction",
            "Well-founded recursion",
            "Inductive types in Lean"
        ]
       subgoals = [
            "Base case: Prove for n = 0",
            "Inductive step: Assume true for n, prove for n+1",
            "Apply induction tactic"
        ]
        proof_depth = 8
        human_explanation = (
            "This theorem requires mathematical induction or recursive reasoning. "
            "The automated system currently handles direct rewrites and single-step lemmas, "
            "but inductive proofs require manual tactic application. "
            "Study the Lean induction tactic and the structure of inductive proofs."
        )
    
    elif tier == 3:  # Multi-lemma reasoning
        missing_lemmas = [
            "Eq.trans",
            "Eq.symm",
            "And.intro",
            "And.left",
            "And.right"
        ]
        recommended_topics = [
            "Transitivity of equality",
            "Logical connectives",
            "Proof composition"
        ]
        subgoals = [
            "Prove intermediate equality using known lemmas",
            "Chain multiple lemmas together",
            "Apply transitivity"
        ]
        proof_depth = 4
        human_explanation = (
            "This theorem requires chaining multiple lemmas together. "
            "The automated system handles single-step proofs, but multi-step "
            "reasoning with intermediate goals requires manual guidance. "
            "Study how to compose proofs using transitivity and lemma application."
        )
    
    # Generate Lean skeleton
    lean_skeleton = self._generate_lean_skeleton(statement, ast, tier)
    
    return CapabilityBoundaryPayload(
        missing_lemmas=missing_lemmas,
        proof_depth_estimate=proof_depth,
        recommended_topics=recommended_topics,
        subgoals=subgoals,
        lean_skeleton=lean_skeleton,
        human_explanation=human_explanation
    )


def _generate_lean_skeleton(
    self,
    statement: str,
    ast: LogicalAST,
    tier: int
) -> str:
    """
    Generate a partial Lean theorem with sorry placeholders.
    """
    # Extract theorem name from statement (simplified)
    theorem_name = "manual_proof_theorem"
    
    # Build type signature from AST
    quantifiers_str = " ".join(
        f"({q.var} : {q.var_type})" for q in ast.quantifiers
    )
    
    # Simplified - in reality, would use AST to build proper Lean syntax
    skeleton = f"""theorem {theorem_name} {quantifiers_str} :
  -- Statement: {statement}
  sorry  -- Complete this proof manually
  
  -- Recommended approach:
  -- 1. Start with 'intro' to introduce variables
  -- 2. Apply relevant lemmas from the list
  -- 3. Use 'exact' or 'rfl' to close goals
"""
    
    return skeleton


# Update classify() method
def classify(self, statement: str, ast: LogicalAST) -> CapabilityClassification:
    lowered = statement.strip().lower()
    signals: list[str] = []

    if self._is_tier4(lowered, ast, signals):
        boundary_info = self._generate_boundary_guidance(4, statement, ast, signals)
        return CapabilityClassification(
            tier=4,
            tier_label="structured_proof",
            status="capability_boundary",  # Changed from "unsupported"
            supported=False,
            reason="Requires inductive reasoning beyond current automation",
            signals=signals,
            boundary_info=boundary_info  # Add guidance
        )

    if self._is_tier3(lowered, ast, signals):
        boundary_info = self._generate_boundary_guidance(3, statement, ast, signals)
        return CapabilityClassification(
            tier=3,
            tier_label="multi_lemma_reasoning",
            status="capability_boundary",  # Changed from "unsupported"
            supported=False,
            reason="Requires multi-step reasoning beyond current automation",
            signals=signals,
            boundary_info=boundary_info  # Add guidance
        )

    # Tier 1 and 2 remain unchanged (supported)
    ...
```

### Phase 3: Orchestrator Updates

**File:** `app/pipeline/orchestrator.py`

**Key Changes:**

1. Handle `capability_boundary` as a success case (not a failure)
2. Still generate AST, Lean skeleton, and explanations
3. Set verification status to `capability_boundary`
4. Include boundary_info in capability payload
5. Log as INFO level, not ERROR

```python
# In run() method:
if capability.status == "capability_boundary":
    logger.info(
        f"Capability boundary reached for request {request_id}: "
        f"{capability.reason}"
    )
    # Still proceed to generate partial artifacts
    # Generate Lean skeleton
    # Generate educational explanation
    # Return structured response with boundary_info
```

### Phase 4: Main API Handler

**File:** `app/main.py`

**Changes in `/formalize` endpoint:**

```python
# After pipeline execution:
verification_status = pipeline_result.verification.get("status", "failed")

# Log capability boundaries as INFO, not ERROR
if verification_status == "capability_boundary":
    logger.info(
        f"Request {request_id} hit capability boundary: "
        f"{pipeline_result.capability.get('reason', 'Unknown')}"
    )
else:
    # Existing logging for verified/failed
    ...

return FormalizeResponse(
    # ... existing fields ...
    verification={
        "status": VerificationStatus(verification_status),
        # ... rest of verification data ...
    },
    # capability field now includes boundary_info when applicable
)
```

### Phase 5: Frontend Types

**File:** `frontend/src/types.ts`

```typescript
export interface CapabilityBoundaryInfo {
  missing_lemmas: string[];
  proof_depth_estimate: number;
  recommended_topics: string[];
  subgoals: string[];
  lean_skeleton: string;
  human_explanation: string;
}

export interface CapabilityInfo {
  tier: number;
  tier_label: string;
  status: "supported" | "unsupported" | "capability_boundary";
  supported: boolean;
  reason: string;
  signals: string[];
  boundary_info?: CapabilityBoundaryInfo;
}

export type VerificationStatus = 
  | "verified" 
  | "failed" 
  | "unsupported" 
  | "capability_boundary";

export type VerificationRunState = 
  | "idle" 
  | "running" 
  | "verified" 
  | "failed" 
  | "unsupported"
  | "capability_boundary";
```

### Phase 6: Frontend StatusBanner Enhancement

**File:** `frontend/src/components/StatusBanner.tsx`

```typescript
// Add to modelFromState():
if (resolved === "capability_boundary") {
  return {
    title: "CAPABILITY BOUNDARY | Guided Manual Proof Mode",
    subtitle: 
      detail ||
      "Automated proof reached its limit. Partial artifacts and guidance provided for manual completion.",
    tone: "border-blue-400/50 bg-blue-500/10 text-blue-200",
  };
}
```

### Phase 7: Guided Manual Proof Mode UI

**New File:** `frontend/src/components/GuidedManualProofPanel.tsx`

```typescript
import { CapabilityBoundaryInfo } from "../types";

interface GuidedManualProofPanelProps {
  boundaryInfo: CapabilityBoundaryInfo;
  leanSkeleton: string;
}

export function GuidedManualProofPanel({
  boundaryInfo,
  leanSkeleton
}: GuidedManualProofPanelProps) {
  return (
    <div className="space-y-4">
      {/* Human Explanation Section */}
      <section className="rounded-lg border border-blue-400/40 bg-blue-500/10 p-4">
        <h3 className="text-sm font-semibold text-blue-200">
          Why Automation Stopped
        </h3>
        <p className="mt-2 text-xs text-blue-200/85">
          {boundaryInfo.human_explanation}
        </p>
      </section>

      {/* Lean Skeleton Section */}
      <section className="rounded-lg border border-border bg-panel p-4">
        <h3 className="text-sm font-semibold text-textMain">
          Lean Proof Skeleton
        </h3>
        <pre className="mt-2 overflow-x-auto rounded bg-surface/60 p-3 text-xs text-textMain">
          <code>{boundaryInfo.lean_skeleton || leanSkeleton}</code>
        </pre>
      </section>

      {/* Subgoals Section */}
      {boundaryInfo.subgoals.length > 0 && (
        <section className="rounded-lg border border-border bg-panel p-4">
          <h3 className="text-sm font-semibold text-textMain">
            Proof Subgoals
          </h3>
          <ul className="mt-2 space-y-1">
            {boundaryInfo.subgoals.map((goal, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-textMuted">
                <span className="text-accent">{i + 1}.</span>
                <span>{goal}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Missing Lemmas Section */}
      {boundaryInfo.missing_lemmas.length > 0 && (
        <section className="rounded-lg border border-border bg-panel p-4">
          <h3 className="text-sm font-semibold text-textMain">
            Required Lemmas
          </h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {boundaryInfo.missing_lemmas.map((lemma, i) => (
              <code key={i} className="rounded bg-surface/60 px-2 py-1 text-xs text-accent">
                {lemma}
              </code>
            ))}
          </div>
        </section>
      )}

      {/* Recommended Topics Section */}
      {boundaryInfo.recommended_topics.length > 0 && (
        <section className="rounded-lg border border-border bg-panel p-4">
          <h3 className="text-sm font-semibold text-textMain">
            Study Topics
          </h3>
          <ul className="mt-2 space-y-1">
            {boundaryInfo.recommended_topics.map((topic, i) => (
              <li key={i} className="text-xs text-textMuted">
                • {topic}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Proof Complexity Indicator */}
      <section className="rounded-lg border border-border bg-panelAlt p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-textMuted">
            EstimatedComplexity
          </span>
          <span className="text-xs text-textMain">
            {boundaryInfo.proof_depth_estimate || "N/A"} steps
          </span>
        </div>
      </section>
    </div>
  );
}
```

### Phase 8: Result Workspace Integration

**File:** `frontend/src/workspace/ResultWorkspace.tsx`

Add conditional rendering:

```typescript
{result.verification.status === "capability_boundary" && result.capability?.boundary_info && (
  <GuidedManualProofPanel
    boundaryInfo={result.capability.boundary_info}
    leanSkeleton={result.lean_code}
  />
)}
```

### Phase 9: App Workspace Controller

**File:** `frontend/src/workspace/AppWorkspaceController.tsx`

```typescript
// Handle capabil capability_boundary as a special success case
if (payload.verification.status === "capability_boundary") {
  setResult(payload);
  setCapabilityBoundary(
    payload.capability?.boundary_info?.human_explanation ||
    "Automation reached capability limit. Guidance provided for manual completion."
  );
  // Don't show error banner -- show capability boundary info
  return;
}
```

## Testing Plan

### Test Case 1: Tier 4 (Induction)
**Input:** "For every natural number n, the sum from 0 to n equals n*(n+1)/2."
**Expected:**
- Status: `capability_boundary`
- Logged as INFO
- `missing_lemmas` includes induction-related lemmas
- `recommended_topics` includes "Mathematical induction"
- `lean_skeleton` provided with `sorry` placeholders
- UI shows "Guided Manual Proof Mode" banner (blue)
- All educational sections populated

### Test Case 2: Tier 3 (Multi-lemma)
**Input:** "For all integers a b c, if a = b and b = c then a = c."
**Expected:**
- Status: `capability_boundary`
- Logged as INFO
- `missing_lemmas` includes `Eq.trans`
- `recommended_topics` includes "Transitivity of equality"
- UI shows guidance panel

### Test Case 3: Tier 2 (Supported)
**Input:** "For every natural number n, 0 + n = n."
**Expected:**
- Status: `verified` or `failed` (not `capability_boundary`)
- Normal verification flow
- No boundary_info

## Benefits

1. **Education over Error**: Users learn WHY automation stopped
2. **Partial Value**: Even unsupported theorems get useful artifacts
3. **Clear Boundaries**: System explicitly identifies its limits
4. **Guided Learning**: Specific lemmas and topics to study
5. **Professional UX**: No generic "failed" messages
6. **Research Value**: Capability boundaries are INFO logs, not errors

## Implementation Priority

1. ✅ Backend schemas (completed)
2. Backend capability classifier enhancements
3. Backend orchestrator& main.py updates
4. Frontend types
5. Frontend UI components
6. End-to-end testing

## Next Steps

1. Complete capability_classifier.py with guidance generation
2. Update orchestrator.py to handle capability_boundary
3. Modify main.py logging levels
4. Implement frontend types and components
5. Test with sample theorems from each tier
