# Finding Output Template

Each finding from a review worker MUST use this exact structure.
Workers that deviate from this format will have their findings dropped.

## Single Finding Format

```
### [SEVERITY] [CATEGORY-NNN]: [Title]

**File**: `path/to/file.ext:line_number`
**Confidence**: [0.7-1.0]

**Problem**: [1-2 sentences describing what is wrong and why it matters.
Include the specific code pattern or line that triggers this finding.]

**Evidence**:
```[language]
// The problematic code, copied verbatim from the file
```

**Suggestion**: [Concrete fix direction. Not "consider improving" but
"replace X with Y because Z". Include a code sketch if possible.]

**Impact**: [What breaks, degrades, or becomes risky if this is not fixed?]
```

## Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| Severity | Yes | `critical`, `warning`, or `suggestion` |
| Category ID | Yes | Prefix + incrementing number: SEC-001, PERF-001, ARCH-001, STYLE-001, DEBT-001, TEST-001 |
| Title | Yes | Under 80 chars, describes the specific problem |
| File + line | Yes | Must be a real, existing file path with accurate line number |
| Confidence | Yes | 0.7 minimum to survive verification gate |
| Problem | Yes | Must explain WHY this is a problem, not just WHAT |
| Evidence | Yes | Verbatim code from the file, not paraphrased |
| Suggestion | Yes | Actionable fix direction with enough detail to implement |
| Impact | Yes | Concrete consequence of inaction |
| Verification | Auto | Added by Phase 3: `evidence_verified`, `structure_confirmed`, `line_corrected`, `confidence_adjusted` |

## Category Prefixes

| Section | Prefix |
|---------|--------|
| Security | SEC |
| Performance | PERF |
| Architecture | ARCH |
| Style | STYLE |
| Debt | DEBT |
| Tests | TEST |
