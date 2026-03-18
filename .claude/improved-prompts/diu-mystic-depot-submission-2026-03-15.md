# Prompt Improvement Report

**Original Source**: Inline (user request)
**Prompt Type**: Task Prompt (one-time document generation)
**Evaluation Date**: 2026-03-15
**Score Improvement**: 13/22 -> 21/22 (+8)

---

## Original Prompt

```markdown
# DIU MYSTIC DEPOT Submission Generator

Generate a DIU-compliant Solution Brief for **AfterQuery** targeting LOE1 (Evaluation Harness) + LOE2 (Benchmark Methodology).

**Key Framing**: AfterQuery is the company. Axiom is AfterQuery's evaluation harness product. Present as one integrated offering from a single vendor, not two distinct solutions.

---

## Output
Create file: `MYSTIC_DEPOT_Submission_Draft.md`

---

## Hard Constraints (DIU CSO Section 3.2)

| Constraint | Requirement |
|------------|-------------|
| Page limit | 5 written pages, 12-point font |
| Title page | Does not count against limit |
| Format | Markdown (PDF conversion is separate step) |
| File naming | Prefix with "LOE1&2_" |
| Deadline context | 2026-03-24 submission |
| Tone | Professional, specific, problem-first |
| Language | Warfighter, mission-critical, analytic tradecraft, IC-appropriate |
| Avoid | "Customer," "end-user," "market disruption," "unnecessarily elaborate brochures" |

---

## Document Structure

### Title Page (does not count against 5 pages)

[... extensive content specification follows ...]

---

## Source Documents (for reference during generation)

Primary source (contains most content):
- `C:\Users\minhl\OneDrive\Desktop\llmsandbox\mystic\MYSTIC_DEPOT_Solution_Brief_v2.md`

Supporting context:
- `C:\Users\minhl\OneDrive\Desktop\llmsandbox\mystic\mystic\submission-requirements.txt` - DIU MYSTIC DEPOT requirements
- [... 5 additional files ...]

---

## Quality Checklist (verify before finalizing)

- [ ] Every LOE1 requirement mapped with evidence and status
- [ ] Every LOE2 requirement mapped with evidence
- [ ] "Exists" vs "Development" clearly marked (DDIL and Adversarial AI = Development)
- [ ] Differentiation vs HELM, AgentDojo, Inspect explicitly stated
- [ ] All capability claims have quantified evidence
- [ ] Tables used for capability mapping
- [ ] Total length does not exceed 5 pages
- [ ] Title page complete with both POCs
- [ ] File prefixed with "LOE1&2_" for submission

---

## Execution Instructions

1. Read the primary source (v2.md) to understand existing content
2. Restructure into the exact section format above
3. Ensure tables are properly formatted for Markdown
4. Keep prose tight - prefer bullets and tables over paragraphs
5. Output to: `MYSTIC_DEPOT_Submission_Draft.md`
```

---

## Improved Prompt

```markdown
# DIU MYSTIC DEPOT Submission Generator

Generate a DIU-compliant Solution Brief for **AfterQuery** targeting LOE1 (Evaluation Harness) + LOE2 (Benchmark Methodology).

---

## Tool Control

**Required reads** (in order):
1. Primary source: `C:\Users\minhl\OneDrive\Desktop\llmsandbox\mystic\MYSTIC_DEPOT_Solution_Brief_v2.md` - Contains all substantive content
2. DIU requirements: `C:\Users\minhl\OneDrive\Desktop\llmsandbox\mystic\mystic\submission-requirements.txt` - Use to verify LOE coverage

**Optional reads** (only if primary source lacks detail):
- `mystic\mystic\cso-requirements.txt` - DIU CSO general requirements
- `mystic\mystic\diu-brief-guidance.md` - DIU best practices
- `mystic\axiom-docs\ARCHITECTURE.md` - Technical architecture
- `mystic\axiom-docs\mcp\MCP_ARCHITECTURE.md` - MCP details
- `C:\Users\minhl\OneDrive\Desktop\aqforllm\Company Context\AfterQuery - Master Company Handbook.md` - Company info

**Write exactly one file**: `MYSTIC_DEPOT_Submission_Draft.md` in working directory.

**Do not**:
- Create intermediate files
- Modify source documents
- Generate multiple drafts

---

## Framing Rule

AfterQuery is the vendor. Axiom is AfterQuery's product for LOE1.

Throughout the document:
- LOE1 capabilities: Attribute to "AfterQuery's Axiom harness" or "Axiom" (never just "AfterQuery" for harness features)
- LOE2 capabilities: Attribute to "AfterQuery's benchmark methodology" or "AfterQuery" (never "Axiom" for methodology)
- Company viability: AfterQuery (the company) with Axiom mentioned as the flagship product

This is NOT two separate solutions. It is one company (AfterQuery) offering integrated LOE1+LOE2 coverage through its product (Axiom) and methodology.

---

## Hard Constraints (DIU CSO Section 3.2)

| Constraint | Requirement |
|------------|-------------|
| Page limit | 5 written pages, 12-point font |
| Title page | Does not count against limit |
| Format | Markdown (PDF conversion is separate step) |
| File naming | Prefix with "LOE1&2_" |
| Deadline context | 2026-03-24 submission |
| Tone | Professional, specific, problem-first |
| Language | Warfighter, mission-critical, analytic tradecraft, IC-appropriate |
| Avoid | "Customer," "end-user," "market disruption," "unnecessarily elaborate brochures" |

---

## Execution Workflow

### Stage 1: Information Gathering
Read the primary source document. Note any gaps in required content.
Do not begin writing until this stage completes.

### Stage 2: Synthesis Planning
Map source content to each required section. Identify:
- Content that transfers directly
- Content requiring restructuring
- Gaps requiring inference or placeholder notes

### Stage 3: Document Generation
Write the complete document in one pass, following the structure exactly.
Prioritize source content over the template examples (examples are illustrative, not prescriptive).

### Stage 4: Validation
Execute the Verification Gate. If any item fails:
- For page overflow: tighten prose, reduce redundancy, prioritize tables over paragraphs
- For missing evidence: add placeholder with "[NEEDS EVIDENCE]" marker
- For formatting errors: correct immediately

Output the final document only after validation passes.

---

## Document Structure

### Title Page (does not count against 5 pages)

```
MYSTIC DEPOT Solution Brief
LOE1: Evaluation Harness + LOE2: Benchmark Methodology

Company: AfterQuery
Legal Entity: Cronus Technologies, Inc. (DBA AfterQuery)
Date: March 2026

Technical Point of Contact:
Sam Jung
samj@afterquery.com
+1 (404) 376-1911

Administrative Point of Contact:
Spencer Mateega
spencer@afterquery.com
+1 (612) 805-9887

Address: 311 California Street, Suite 750, San Francisco, CA 94104
```

---

### Page 1: Executive Summary

**Structure:**
1. **The Problem** (DoD perspective, 2-3 sentences)
   - AI deployed faster than verified
   - Synthetic benchmarks divorced from operations
   - No infrastructure for agentic assessment with tool-use
   - Human-team measurement missing

2. **Our Solution** (2-3 sentences)
   - **AfterQuery** provides a full-stack AI evaluation capability through **Axiom**, our MCP-native evaluation harness with typed tool-use and artifact-centric scoring, combined with expert-driven benchmark methodology featuring contamination resistance and oracle validation.
   - Together, these deliver a closed-loop evaluation-diagnosis-improvement-measurement cycle.

3. **Key Differentiators** (4 bullets max)
   - End-to-end lifecycle (authoring -> QC -> execution -> scoring -> visualization -> regrading)
   - Typed tool-use producing real artifacts (Excel, PowerPoint, analysis reports)
   - Pass@k reliability measurement across multiple identical trials
   - Docker/OCI/Kubernetes architecture aligned with DoD DevSecOps for IL5/air-gapped deployment

4. **Credibility line**
   - AfterQuery currently powers evaluation environments for OpenAI, Google DeepMind, and Meta Superintelligence Labs

---

### Pages 2-3: Technology Concept (LOE1)

**Opening paragraph**: AfterQuery's Axiom evaluation harness vs. existing frameworks (HELM, AgentDojo, Inspect). Position Axiom as AfterQuery's product for LOE1, with AfterQuery's benchmark methodology for LOE2.

**LOE1 Capability Mapping Table (AfterQuery Axiom Harness):**

| DIU Requirement | AfterQuery Capability | Evidence | Status |
|-----------------|------------------|----------|--------|
| Model Interface | MCP-native architecture, pluggable adapters (Claude Code, OpenHands). Standardized interface via SHTTP, SSE, stdio transports. | 43 MCP tool servers: 14 offline + 29 internet | **Exists** |
| Execution Engine | Daytona cloud VMs, parallel pass@k trials. Each trial gets identical environment snapshots. | 365+ tasks across 6 categories | **Exists** |
| Measurement & Scoring | Weighted dual scoring: 60% deterministic + 40% LLM-as-judge. Per-test configuration. | Oracle validation (golden solution = 1.0) | **Exists** |
| Human Evaluation Integration | Expert-in-the-loop review interfaces, rubric-based evaluation, multi-stage QA | QC case study: 90+ experts, 20,000 test cases | **Exists** |
| Output & Reporting | Next.js dashboard, per-trial drill-down, file rendering (Excel, PowerPoint). Export JSON, CSV. API access. | Git snapshots preserve trial state | **Exists** |
| Continuous Monitoring | Regrade without re-execution, trend tracking, version-controlled results | Automated model ingestion via CLI | **Exists** |
| Configuration Management | Harbor format: task.toml, instruction.md, environment/, solution/, tests/. QC Checker validates before deployment. | 18 deterministic + runtime + MCP checks | **Exists** |
| DDIL Simulation | Kubernetes + Istio (app-layer fault injection) + Chaos Mesh (network-layer: latency, partition, bandwidth) | Docker isolation supports offline execution | **Development** |
| Agentic Evaluation | MCP tool discovery, multi-step execution, comprehensive audit trails. Data isolation prevents oracle leakage. | MCP Universe, Finance Dataroom, Excel Gym | **Exists** |
| Adversarial AI | Integration layer for Garak + Promptfoo (scanner-style probing, config-driven red-teaming) | VADER benchmark demonstrates security evaluation | **Development** |
| Multimodal | Chart/table reasoning, document QA, long-context evaluation. Vision-language with structured outputs. | UI-Bench, App-Bench, multimodal catalog | **Exists** |

**Architectural Compliance section:**
- Modular: Independent scoring, execution, visualization components
- Containerized: OCI base images (mcp-base, mcp-internet)
- Multi-environment deployment path table (same as source)

---

### Page 4: Technology Concept (LOE2)

**LOE2 Methodology Mapping Table:**

| DIU Requirement | AfterQuery Methodology | Evidence |
|-----------------|------------------------|----------|
| Requirements Elicitation | Diagnosis-first: identify model failures before building data | FinanceQA, LeetBench research |
| Task Decomposition | Harbor format: instruction.md, environment/, solution/, tests/ | 365+ structured tasks |
| Input Design | Expert-sourced scenarios, contamination checks, novelty filtering | QC case study: 3,000 rows, 90+ experts |
| Scoring Criteria | Rubric construction with weighted deterministic + LLM hybrid | Per-test config: {id, name, weight, enabled, is_llm, llm_prompt} |
| Baseline Establishment | Multi-model head-to-head under identical conditions | Same scoring, same envs, same trial count |
| Validation | Oracle validation (golden solution must score 1.0), QC Checker | 18 deterministic + runtime checks |
| Gaming Resistance | Novel question generation, proprietary contamination filtering | Expert-authored, not web-scraped |
| Maintenance | Regrade capability, version-controlled benchmarks | Update tests without re-execution |

**Training Materials Deliverable:**
- Written methodology guide (Harbor format documentation)
- Worked examples (existing catalog items as templates)
- QA checklist (QC Checker process, common pitfalls)
- Training curriculum for government evaluators

---

### Page 5: Company Viability

**AfterQuery Overview:**
- Applied research lab: diagnose AI capability gaps, build expert-curated training data, evaluation assets, and RL environments
- **Axiom** is AfterQuery's evaluation harness product, powering assessments for frontier AI labs
- Legal entity: Cronus Technologies, Inc. (DBA AfterQuery)
- HQ: San Francisco, CA
- Founded: 2024
- Accelerator: Y Combinator W25 founding cohort
- Funding: $30M Series A at $300M valuation

**Origin Story (1-2 sentences):**
AfterQuery began as Cronus, an AI agent for private-equity and finance workflows. The founders pivoted after discovering that even strong models failed badly on realistic finance tasks--revealing that data quality, not architecture, was the core constraint.

**Commercial Traction:**
- Named clients: OpenAI, Google DeepMind, Meta Superintelligence Labs
- 100,000+ expert network spanning 40+ professional domains
- 56+ catalog items across agentic, coding, STEM, reasoning, multimodal categories

**Published Benchmarks Table:**

| Benchmark | Domain | Result/Purpose |
|-----------|--------|----------------|
| FinanceQA | Finance reasoning | 45% overall improvement; 690% on incomplete-information tasks |
| LeetBench | Novel coding | Contamination-resistant competitive programming |
| VADER | Security | Human-evaluated adversarial failure analysis |
| UI-Bench | Multimodal | UI understanding for computer-use agents |
| App-Bench | Software | End-to-end application generation |
| IDE-Bench | Coding agents | Multi-file software engineering tasks |
| Market-Bench | Finance/trading | Strategy quality, noise handling |

**Team Credentials:**
- **Sam Jung, Principal Investigator**: Leads environments at AfterQuery for OpenAI, Google DeepMind, and Meta Superintelligence Labs. Designed and deployed MCP-native evaluation infrastructure.
- **Spencer Mateega, Administrative Lead**: Oversees operations, partnerships, and government engagement.
- Personnel with documented clearability available for classified extensions.

**Go-to-Market:**
- Research-first: Publish benchmarks to diagnose gaps, monetize supervision to close them
- Expert-grade: Verified professionals design tasks, not generic annotators
- Full-stack: Evaluation, training data, and environments from same methodology

---

## Edge Case Handling

**Page overflow**: If content exceeds 5 pages:
1. Convert any paragraph prose to bullet points
2. Merge redundant table rows
3. Remove least-critical differentiators (keep top 3)
4. Reduce executive summary to minimum viable form
Never truncate capability mapping tables--these are required evidence.

**Source conflict**: If primary source contradicts this prompt's structure:
- Structure wins (this prompt defines required format)
- Content from source wins (source has accurate facts)
- When both conflict, flag with "[RECONCILE: source says X, prompt says Y]"

**Missing content**: If source lacks required information:
- Mark with "[SOURCE GAP]" and continue
- Do not fabricate evidence or statistics

---

## Output Style

- Do not narrate your process ("First, I will...", "Let me now...")
- Do not explain formatting choices
- Output only the final document
- Use the exact section headers specified
- Prefer tables over prose where structure is provided

---

## Verification Gate (MANDATORY)

Before finalizing output, verify each requirement. Mark PASS or FAIL internally:

| Requirement | Verification |
|-------------|--------------|
| Every LOE1 requirement has: evidence, status (Exists/Development) | Check table completeness |
| Every LOE2 requirement has: methodology, evidence | Check table completeness |
| DDIL and Adversarial AI marked as "Development" | Exact match required |
| Differentiation vs HELM/AgentDojo/Inspect stated explicitly | Must appear in Technology Concept |
| All claims have quantified evidence (numbers, not adjectives) | No "many" or "significant" |
| Tables used for all capability mappings | Structure enforced |
| Title page complete with both POCs | Check both contacts present |
| File named correctly | Must include "LOE1&2_" prefix pattern |

**Page count verification**: Markdown approximation = 400 words per page. Document body (excluding title page) should not exceed 2,000 words. If exceeded, apply overflow rules.

If ANY requirement fails, fix before output.
```

---

## Evaluation Summary

| # | Criterion | Original | Improved | Delta |
|---|-----------|----------|----------|-------|
| 1 | Decision-complete (autonomy encoded) | 1 | 2 | +1 |
| 2 | Scope explicitly bounded | 2 | 2 | 0 |
| 3 | Tool behavior controlled | 0 | 2 | +2 |
| 4 | Structured syntax used | 2 | 2 | 0 |
| 5 | Anti-verbose (no redundant narration) | 1 | 2 | +1 |
| 6 | Self-contained (if delegation) | 1 | 1 | 0 |
| 7 | Stage separation (if complex) | 0 | 2 | +2 |
| 8 | Non-conflicting instructions | 1 | 2 | +1 |
| 9 | Clear success criteria | 1 | 2 | +1 |
| 10 | Focused expertise (not overly broad) | 2 | 2 | 0 |
| 11 | Format enforcement (output structure) | 2 | 2 | 0 |
| **Total** | **13/22** | **21/22** | **+8** |

---

## Change Log

### Change 1: Added Explicit Tool Control Section
- **Before**: Absent
- **After**: Detailed specification of required reads, optional reads, single write target, and prohibited operations
- **Rationale**: Criterion #3 (Tool behavior controlled). Eliminates ambiguity about which files to read and in what order.

### Change 2: Added Stage Separation (Execution Workflow)
- **Before**: Five undifferentiated execution steps
- **After**: Four distinct stages: Information Gathering -> Synthesis Planning -> Document Generation -> Validation
- **Rationale**: Criterion #7 (Stage separation). Prevents interleaved read/write that causes inconsistent synthesis.

### Change 3: Added Framing Rule Section
- **Before**: Conflicting guidance about company/product attribution
- **After**: Explicit attribution rules for LOE1 (Axiom), LOE2 (AfterQuery methodology), and company viability
- **Rationale**: Criterion #8 (Non-conflicting instructions). Resolves cognitive dissonance.

### Change 4: Added Edge Case Handling Section
- **Before**: Absent
- **After**: Decision rules for page overflow, source conflicts, and missing content
- **Rationale**: Criterion #1 (Decision-complete). Enables autonomous completion without clarification requests.

### Change 5: Converted Checklist to Verification Gate
- **Before**: Checkbox list without enforcement
- **After**: Mandatory verification table with pass/fail tracking and page count formula
- **Rationale**: Criterion #9 (Clear success criteria). Makes validation actionable and enforceable.

### Change 6: Added Output Style Section
- **Before**: Absent
- **After**: Explicit prohibition on process narration and formatting commentary
- **Rationale**: Criterion #5 (Anti-verbose). Ensures clean document output without wrapper text.

---

## Validation Notes

**Residual Gap - Criterion 6 (Self-contained): Score 1**

This is an acceptable limitation for the prompt type. Task prompts that operate on external source documents cannot be fully self-contained without embedding all source content inline. The file reference pattern used here is appropriate:
- Clear hierarchy (primary vs. optional sources)
- Absolute paths provided
- No ambiguous relative references

Full self-containment would require embedding 185+ lines of source content, which would make the prompt unwieldy and defeat the purpose of source documents.

**Further Opportunities**

1. Could add example output snippets for each section to calibrate quality expectations
2. Could add word count targets per section (not just overall)
3. Could add explicit "success looks like" statement at the top

These are diminishing returns given the +8 point improvement already achieved.
