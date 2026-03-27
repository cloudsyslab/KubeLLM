# Multi-Agent Backend Abstraction for Review Workflow

Date: 2026-03-25

## Framing

- Subject: how to abstract multi-agent task delegation so the review workflow is not locked to Codex CLI.
- Current repo context: the review skill delegates Phase 2 work through `/codex` and explicitly launches `codex exec --full-auto --json`, while a local design note already calls for an "input prompt + output schema" abstraction.
- Decision this research should support: whether to standardize around a minimal worker execution adapter, or move toward a fuller framework/runtime abstraction.
- Assumptions:
  - The current review workflow should keep its core shape: router/supervisor locally, isolated workers in parallel, local verification and synthesis.
  - The first portability target is backend swapping, not replacing the whole workflow with a new framework.
  - Structured worker output matters more than preserving any one vendor's handoff model.

## Executive Summary

The current workflow is closer to the "supervisor with isolated subagents" pattern than to conversational handoff systems. That matters because most frameworks split into two families: supervisor/tool patterns that fit review workers, and handoff/team patterns that are designed for ongoing conversational transfer or peer coordination. The smallest portable abstraction is not "agent" or "handoff"; it is a repo-owned worker execution contract with static worker profiles and dynamic task invocations. Backends differ too much on typed output, state carry-over, and permission semantics to treat their native interfaces as portable.

## Current State in This Repo

- `skills/review/SKILL.md`
  - Phase 2 is explicitly "Parallel Analysis (via /codex)".
  - Workers are launched via `codex exec --full-auto --json -c "search=true"`.
- `codex-prompts/review-skill/review-skill-2026-03-25.md`
  - The repo already identifies platform lock-in as a gap.
  - The stated better direction is "Abstract worker interface (input prompt + output schema)."
- `codex-prompts/worker-response-schema.json`
  - The current worker result is already a useful normalized contract:
    - `status`
    - `summary`
    - `findings`
    - `artifacts`
    - `gaps`
    - `escalations`

## Pattern Comparison

| Pattern / runtime | Native execution idea | Best fit for this review workflow | Why it helps | Why it should not become the core abstraction |
| --- | --- | --- | --- | --- |
| Codex CLI style worker | Supervisor spawns isolated worker process with prompt + schema | Very high | Closest to current design, easy parallel fan-out, easy local verification | Ties orchestration to one CLI and one response format |
| Anthropic subagents | Main session delegates to isolated subagents with their own context/tools/permissions | High | Maps cleanly to "specialized review worker" | Native docs focus on agent config, not typed worker output contracts |
| Anthropic agent teams | Multiple full Claude instances with direct teammate communication | Medium | Useful when workers must challenge each other or coordinate directly | Higher token cost and coordination overhead than needed for Phase 2 review workers |
| LangChain subagents | Supervisor calls stateless subagents as tools | High | Strong conceptual match for isolated review workers | It is a framework pattern, not a backend-neutral runtime contract |
| CrewAI tasks | Task object binds `description`, `expected_output`, `agent`, `context`, output schema, and guardrails | Medium | Good example of task contract fields and validation hooks | Pulls in framework lifecycle even if you only need worker execution |
| OpenAI Agents handoffs / LangChain handoffs / AG2 handoffs | Agent-to-agent state transfer with optional filters/metadata | Low to medium | Useful for customer-support style flows and multi-turn routing | Too stateful and conversational for review workers that should return one structured payload |
| OpenAI Swarm | Minimal `Agent` + `handoff` primitives, stateless between runs | Medium | Shows the smallest handoff-first model | Still handoff-centric, not a typed worker-task contract |
| Ollama structured outputs | Local model runner with JSON-schema-constrained responses | High as a backend | Good local execution target for prompt + schema -> structured result | No native delegation semantics; orchestration must stay outside |
| OpenCode agents | CLI agent runtime with subagents, provider/model indirection, task permissions | Medium to high | Good example of a backend with configurable subagents and provider portability | Docs expose agent config, not a native portable worker result schema |
| A2A protocol | Inter-agent protocol with Agent Cards, tasks, messages, artifacts, streaming | Medium as a future integration layer | Strong standard for remote agent interoperability | Heavier than needed for in-process/backend swapping today |

## Evidence by Framework

### Anthropic

- Subagents:
  - Each subagent runs in its own context window, with custom prompt, tool access, and permissions.
  - Background subagents can run concurrently.
  - Subagents cannot spawn other subagents, which limits recursive delegation.
- Agent teams:
  - Team lead + teammates with direct inter-agent communication.
  - Better when workers need to coordinate with each other, not just report back.

Why this matters:
- Anthropic exposes two distinct abstractions:
  - isolated helper workers
  - communicating peer team
- The current review workflow matches the first one, not the second.

### CrewAI

- `Task` carries:
  - `description`
  - `expected_output`
  - `agent`
  - `context`
  - `output_json` / `output_pydantic`
  - `guardrail` / `guardrails`
  - `guardrail_max_retries`
- `TaskOutput` can expose `raw`, JSON, or Pydantic output depending on task configuration.

Why this matters:
- CrewAI shows a production-style split between:
  - static agent definition
  - dynamic task invocation
  - output validation
- That split is a useful model for a repo-owned adapter.

### AG2

- Handoffs are attached to agents via a `handoffs` attribute.
- Transition targets include agents, functions, user return, terminate, and nested chat.
- Tool functions can return `ReplyResult(message, target, context_variables)`.
- AG2 explicitly recommends function targets for validation and dynamic routing.

Why this matters:
- AG2 treats routing and validation as part of a conversational transition graph.
- That is more expressive than this workflow needs, but it clarifies the fields a richer adapter may eventually want: next target, context updates, and validation hooks.

### LangChain / LangGraph

- Multi-agent docs separate:
  - subagents
  - handoffs
  - skills
  - router
  - custom workflow
- Subagents are stateless, invoked as tools, and run in clean context windows.
- Handoffs update state such as `active_agent` or `current_step`.
- LangChain explicitly notes that subagents add an extra call because results flow back through the main agent, and that the overhead buys centralized control.

Why this matters:
- LangChain's naming maps almost exactly onto the architectural choice here:
  - choose subagents if you want isolated workers and centralized synthesis
  - choose handoffs if you want user-facing multi-turn state transitions

### OpenAI Agents SDK and Swarm

- Agents SDK handoffs:
  - `handoff()` lets you specify destination, `input_type`, `on_handoff`, and `input_filter`.
  - `input_type` is metadata for the handoff tool call, not the next agent's main input.
  - docs say to use `Agent.as_tool(parameters=...)` for structured nested specialists without transferring the conversation.
- Swarm:
  - reduces the model to `Agent` + `handoff`.
  - is explicitly stateless between calls.
  - converts functions into JSON Schema for tools automatically.

Why this matters:
- OpenAI's docs strongly distinguish:
  - nested specialist as tool
  - conversational transfer as handoff
- For this repo, the nested specialist model is the better match.

### Local / Alternative CLI Runtimes

- Ollama:
  - accepts JSON Schema through the `format` field.
  - supports OpenAI-compatible `response_format`.
- OpenCode:
  - agents have configurable prompt, model, and permissions.
  - model IDs use `provider/model-id`.
  - `permission.task` controls which subagents can be invoked.
- Claude Code headless automation:
  - `claude -p ... --output-format json`
  - `claude -p ... --output-format stream-json`

Why this matters:
- Local runners and alternative CLIs can satisfy the worker-execution role.
- But most do not provide a portable typed result contract by themselves.
- That contract should live in this repo, with client-side validation.

## Recommendation

### Use a Two-Layer Contract

1. Static worker profile

Represents reusable capability, roughly analogous to:
- Anthropic subagent frontmatter
- OpenCode agent config
- CrewAI Agent
- Swarm Agent

Suggested fields:

```ts
type WorkerProfile = {
  id: string
  description: string
  systemPrompt?: string
  model?: string
  tools?: string[]
  permissions?: Record<string, string>
  backendHints?: {
    runtime?: string
    effort?: "low" | "medium" | "high"
    background?: boolean
  }
}
```

2. Dynamic worker invocation

Represents a single delegated task.

```ts
type WorkerRequest = {
  workerProfileId: string
  prompt: string
  outputSchema: object
  contextFiles?: string[]
  attachments?: string[]
  timeoutMs?: number
  metadata?: Record<string, unknown>
}
```

3. Normalized result

```ts
type WorkerResult<T = unknown> = {
  status: "complete" | "partial" | "failed"
  structured: T | null
  rawText: string
  events?: unknown[]
  usage?: {
    inputTokens?: number
    outputTokens?: number
    durationMs?: number
    costUsd?: number
  }
  error?: {
    code: string
    message: string
    retryable: boolean
  }
}
```

### Why this beat the alternatives

- Better than a generic "Agent" abstraction:
  - Most frameworks overload "agent" to mean both static persona and live execution node.
  - The review workflow needs a narrower boundary.
- Better than adopting a handoff graph as the base model:
  - Review workers should produce findings and return.
  - They should not carry user-facing conversational state.
- Better than adopting a full framework now:
  - The workflow already exists.
  - The immediate problem is backend portability, not orchestration expressiveness.

## Backend Interface

```ts
interface WorkerBackend {
  name: string
  capabilities(): {
    nativeSchema: boolean
    streaming: boolean
    background: boolean
    isolatedContext: boolean
    toolsConfigurable: boolean
    permissionsConfigurable: boolean
  }

  execute<T>(request: WorkerRequest): Promise<WorkerResult<T>>
}
```

### Important design choice

Always validate `WorkerResult.structured` locally against `outputSchema`, even when the backend claims native schema support.

Why:
- CrewAI, Ollama, and Codex-style runners can shape outputs natively.
- Claude Code and OpenCode docs emphasize prompts, tools, and permissions more than typed output guarantees.
- A repo-owned validation step is the only portable trust boundary.

## Suggested Backends

### 1. `CodexCliBackend`

- Keep current behavior.
- Native fit for prompt + output schema.
- Baseline implementation.

### 2. `ClaudeCodeBackend`

Two modes:
- in-session subagent mode for interactive use
- headless CLI mode using `claude -p ... --output-format json` or `stream-json`

Important note:
- treat Anthropic JSON output as transport data
- still coerce/validate into the repo schema locally

### 3. `OpenCodeBackend`

- Use subagents where available.
- Resolve `provider/model-id` dynamically.
- Enforce allowed subagents and tools from backend config.

### 4. `OllamaBackend`

- Best local runner option for strict structured output.
- No native delegation, so the adapter only executes isolated workers.

## Work to Avoid

- Do not make handoffs the universal internal model.
  - It is the wrong default for a review workflow with isolated workers.
- Do not hide backend capability differences.
  - Expose them as explicit `capabilities()`.
- Do not make the output contract backend-native.
  - The repo should own the normalized result schema.
- Do not adopt A2A or another inter-agent protocol yet.
  - That is a future interoperability layer, not the smallest useful change.

## Quick Wins

1. Extract a `WorkerBackend` interface and move the current Codex launch logic behind it.
2. Rename the existing worker schema to a runtime-neutral name such as `review-worker-result.schema.json`.
3. Separate static worker profile data from dynamic delegated prompt generation.
4. Add local schema validation after every backend call, even for native-schema backends.
5. Add a capability matrix so the router can decide which features are safe to use per backend.

## Strategic Investments

1. Add `ClaudeCodeBackend` using headless `--output-format json`.
2. Add `OllamaBackend` for local structured workers.
3. Add explicit fallback rules:
   - if native schema unsupported, request JSON and validate locally
   - if streaming unsupported, wait for terminal output
   - if background unsupported, keep orchestration synchronous
4. Consider A2A only if you later need remote worker services, agent discovery, or cross-org agent interoperability.

## Disregard List

- Replacing the review workflow with CrewAI, AG2, LangGraph, or Swarm right now.
  - They are good reference points, but adopting a framework does not solve backend portability by itself.
- Building a universal inter-agent protocol first.
  - Too much ceremony for the current problem.
- Treating "subagent", "handoff", and "task" as synonyms.
  - The docs show they are materially different execution models.

## Sources

- Anthropic subagents: https://code.claude.com/docs/en/sub-agents
- Anthropic agent teams: https://code.claude.com/docs/en/agent-teams
- Anthropic CLI automation patterns: https://code.claude.com/docs/en/common-workflows
- CrewAI tasks: https://docs.crewai.com/en/concepts/tasks
- AG2 handoffs: https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/orchestration/group-chat/handoffs/
- LangChain multi-agent overview: https://docs.langchain.com/oss/python/langchain/multi-agent/index
- LangChain subagents: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
- LangChain handoffs: https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs
- OpenAI Agents SDK handoffs: https://openai.github.io/openai-agents-python/handoffs/
- OpenAI Swarm: https://github.com/openai/swarm
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- OpenCode agents: https://opencode.ai/docs/agents/
- A2A protocol overview: https://a2a-protocol.org/latest/topics/what-is-a2a/
- A2A specification: https://a2a-protocol.org/latest/specification/
