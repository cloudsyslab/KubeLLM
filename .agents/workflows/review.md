---
description: Orchestrate a multi-dimensional codebase audit using specialized roles, static tools, and evidence-based verification
---

# Repository Audit and Fix Workflow (Judge Orchestrator)

This workflow adopts an advanced "Judge and Specialist" pattern. Rather than using a single monolithic prompt, this workflow orchestrates targeted sub-tasks, pairs static analysis with LLM inference, and demands empirical verification before proposing changes.

## 0. Progressive Disclosure Commands

Listen for specific sub-commands to limit scope and increase depth:
- `/review security`: Act as a Security Specialist. Focus on injections, SAST errors, hardcoded secrets, and cryptography flaws.
- `/review performance`: Act as a Performance Specialist. Focus on N+1 queries, computational complexity, and memory leaks.
- `/review style`: Act as a Maintainability Specialist. Focus on DRY principles, architecture coupling, and cyclomatic complexity.
- `/review architecture`: Act as an Architecture Specialist. Focus on multi-agent messaging patterns, state management, and separation of concerns.
- `/review full`: Act as the **Judge Orchestrator**. Delegate and run all available specialized checks, synthesize the inputs, and provide the final report.

## 1. Context and Scoping

Before auditing, ground your reasoning in the repository's reality.
- **CRITICAL:** First, read the repository-specific context file at `.agents/review_context.md`. This contains vital domain rules (e.g., KubeLLM's Lab-only execution constraint).
- Determine the scope: Are we reviewing a specific module, a recent commit, or performing a high-level architectural scan?
  
## 2. Static Tooling & Pre-flight (Do Not Skip)

LLMs should analyze the output of code-analysis tools, not replace them entirely.
- Before blindly reading code files, attempt to execute available linters or static analysis tools (e.g., `flake8`, `mypy`, `bandit`, or equivalent SAST scanners) relevant to the codebase's languages.
- Feed the raw output of these tools into your context window. Let the LLM filter false positives and translate the raw warnings into human-actionable improvements.

## 3. Targeted Agentic Discovery

Based on the selected mode (Security, Performance, etc.), perform a thorough dive on the scoped files.
- **Avoid Context Dilution**: Do not attempt to stuff the entire repository into your context window. Utilize Graph RAG, AST tools (`ast-grep`), or semantic databases (like the `pgvector` KubeLLM RAG system) to pinpoint cross-file dependencies structurally.
- **Evidence-Based Verification**: When you suspect a bug, vulnerability, or inefficiency, you **MUST** attempt to verify it. Write a quick diagnostic script, grep command, or ast-grep search to prove the flaw exists and understand its blast radius before adding it to your final report. Eliminate hallucinations.

## 4. Synthesis (The Judge Report)

Once the specialized discovery is complete, aggregate the findings. Discard pedantic nitpicks. Group similar issues together and prioritize high-value impact.

Generate the audit report using the following markdown structure to enable seamless handoff to an action agent:
```markdown
## Orchestrator Summary
Brief overview of the module's health, the tools executed, and the top concerns.

## Verified Critical / High Priority Findings
### 1. [Title of Issue]
- **Location**: `path/to/file:line`
- **Evidence**: Explain how you empirically verified the issue (e.g., output of static analysis, test script proof).
- **Blast Radius**: What is the impact?
- **Action Ticket (Handoff)**: Provide crystal-clear instructions, exact files to modify, and the precise code logic required so an Actions Agent can implement this immediately without needing to re-audit.

## Medium / Low Priority Findings
...
```

## 5. Action and Handoff

- For straightforward and safe fixes (localized bugs, style corrections), you may offer to apply them directly if the user requests it.
- Otherwise, your primary goal is to **handoff** the synthesized report to the user or an Actions Agent.
- Ensure your "Action Ticket" in the report contains enough precision (exact file paths, target line ranges, and the verified context) that the next agent can jump straight into execution mode.
- Recommend native validation commands (e.g., `bash orchestrator/preflight.sh` or targeted test scripts) for the action agent to use after implementing the fix.

## Completion Check

Do not consider this `/review` cycle finished until you can answer:
- Did I leverage static analysis instead of just raw textual reading?
- Did I empirically verify my claims to filter out hallucinations?
- Is my judge report categorized clearly and prioritized for action?
