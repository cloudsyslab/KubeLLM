# Agent System Documentation

## Overview

The KubeLLM-Minh system uses a multi-agent architecture where specialized agents collaborate to troubleshoot Kubernetes issues. This document provides detailed information about each agent type, their interactions, and implementation details.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Collaboration Flow                     │
└─────────────────────────────────────────────────────────────────┘

1. KNOWLEDGE PHASE (AgentAPI)
   ┌─────────────────────────────────┐
   │   AgentAPI (Knowledge Agent)    │
   │                                  │
   │  • Receives problem description  │
   │  • Queries RAG knowledge base    │
   │  • Analyzes relevant files       │
   │  • Generates troubleshooting     │
   │    steps in structured format    │
   └──────────────┬──────────────────┘
                  │
                  │ Response with steps
                  ↓
2. EXECUTION PHASE (AgentDebug)
   ┌─────────────────────────────────┐
   │    AgentDebug (Action Agent)    │
   │                                  │
   │  • Receives troubleshooting      │
   │    steps from Knowledge Agent    │
   │  • Executes kubectl commands     │
   │  • Modifies configuration files  │
   │  • Rebuilds containers           │
   │  • Reports status tokens         │
   └──────────────┬──────────────────┘
                  │
                  │ Execution results
                  ↓
3. VERIFICATION PHASE (AgentVerification)
   ┌─────────────────────────────────┐
   │  AgentVerification (Validator)  │
   │                                  │
   │  • Independently verifies fixes  │
   │  • Checks actual cluster state   │
   │  • Validates file changes        │
   │  • Tests service endpoints       │
   │  • Returns verification token    │
   └──────────────────────────────────┘
```

## Agent Classes

### Base Agent Class

**Location**: `debug_assistant_latest/agents.py:44-66`

**Purpose**: Abstract base class for all agents

**Key Methods**:
- `prepareAgent()`: Initialize LLM, tools, and agent configuration
- `preparePrompt()`: Build context-aware prompts with file contents
- `askQuestion()`: Execute the agent's primary task
- `setupAgent()`: Convenience method calling prepare methods

**Pattern**: Template Method Pattern - subclasses override specific methods

---

## 1. AgentAPI (Knowledge Agent)

**Location**: `debug_assistant_latest/agents.py:67-114`

**Purpose**: Analyzes Kubernetes problems using RAG and provides troubleshooting guidance

### Configuration

```json
{
  "api-agent": {
    "model": "llama3.1:70b",
    "embedder": "nomic-embed-text",
    "clear-knowledge": true,
    "new-run": true,
    "init-agent": true,
    "knowledge": [
      "https://learnk8s.io/troubleshooting-deployments"
    ]
  }
}
```

### Key Attributes

- `response`: Stores the RAG assistant's response
- `prompt`: Built from problem description + relevant files
- `agentProperties`: Configuration from config.json

### Workflow

1. **Initialization** (`prepareAgent()`):
   - Starts new run if configured
   - Initializes RAG assistant via API
   - Clears knowledge base if configured
   - Loads documentation URLs into vector DB

2. **Prompt Construction** (`preparePrompt()`):
   - Adds problem description
   - Adds system prompt
   - Traverses relevant files (deployment, application, service, dockerfile)
   - Injects file contents into prompt

3. **Question Execution** (`askQuestion()`):
   - Sends prompt to RAG API
   - Receives structured troubleshooting steps
   - Stores response for debug agent

### API Dependencies

Uses functions from `rag_api.py`:
- `start_new_run()`: Start fresh session
- `initialize_assistant()`: Setup RAG with model/embedder
- `clear_knowledge_base()`: Clear vector DB
- `add_url()`: Load documentation
- `ask_question()`: Query RAG assistant

### Output Format

Returns troubleshooting steps in format:
```markdown
1. Check the logs
```bash
kubectl logs <pod-name>
```

2. Delete the deployment
```bash
kubectl delete -f <yaml-file>
```

3. Modify the Dockerfile...
```

---

## 2. AgentDebug (Execution Agent)

**Location**: `debug_assistant_latest/agents.py:116-219`

**Purpose**: Executes troubleshooting steps suggested by Knowledge Agent

### Configuration

```json
{
  "debug-agent": {
    "model": "gpt-4o",
    "instructions": [
      "Execute the provided troubleshooting steps",
      "Modify files as needed",
      "Rebuild containers when necessary"
    ],
    "guidelines": [
      "Always verify commands succeeded",
      "Use real resource names",
      "Report final status with tokens"
    ]
  }
}
```

### Key Attributes

- `agentAPIResponse`: Stores Knowledge Agent's response
- `debugStatus`: Boolean indicating success/failure (self-reported)
- `response`: Full execution transcript
- `agent`: Phi Agent instance with BetterShellTools

### Model Selection Logic

```python
model_name = self.agentProperties["model"]
if any(token in model_name for token in ['gpt', 'o3', 'o4', 'o1']):
    model = OpenAIChat(id=model_name)
elif 'llama' in model_name:
    model = Ollama(id=model_name)
elif 'gemini' in model_name:
    model = Gemini(id=model_name)
```

### Workflow

1. **Agent Preparation** (`prepareAgent()`):
   - Selects appropriate LLM based on model name
   - Initializes with BetterShellTools
   - Loads instructions and guidelines
   - Enables debug mode and tool call visibility

2. **Prompt Building** (`preparePrompt()`):
   - Includes relevant file contents
   - Adds Knowledge Agent's response
   - Adds additional directions from config

3. **Execution** (`askQuestion()`):
   - **Timeout**: 480 seconds (8 minutes)
   - Receives knowledge agent's steps
   - Executes kubectl commands
   - Modifies files (YAML, Dockerfile, Python)
   - Rebuilds containers if needed
   - Deletes and reapplies configurations
   - Returns status token

### Status Tokens

- `<|SOLVED|>`: Successfully fixed the issue
- `<|FAILED|>`: Could not fix the issue
- `<|ERROR|>`: Encountered errors during execution

### Tool Usage Rules

Enforced via prompt:
```python
"### Tool Usage Rules\n"
"- Do not attempt many commands in one tool call.\n"
"- Never repeat a tool call that has already been executed successfully.\n"
"- If you need the result of a previous tool call, use the provided output.\n"
"- Keep the tool call as simple as possible to avoid errors.\n"
```

### Metrics Collected

```python
metrics_entry = {
    "test_case": self.config['test-name'],
    "model": model_name,
    "agent_type": "debug",
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "total_tokens": total_tokens,
    "task_status": int(self.debugStatus)
}
```

### Important Notes

- **Self-reporting**: Status is based on agent's own assessment (may be inaccurate)
- **Verification needed**: Verification agent validates actual success
- **Timeout protection**: Will abort after 480 seconds
- **File modifications**: Can edit YAML, Dockerfile, Python files
- **Container rebuilds**: Can trigger Docker image rebuilds

---

## 3. AgentDebugStepByStep

**Location**: `debug_assistant_latest/agents.py:221-336`

**Purpose**: Executes troubleshooting steps incrementally with recovery attempts

### Differences from AgentDebug

1. **Step Formation** (`formProblemSolvingSteps()`):
   - Extracts bash commands from knowledge agent response
   - Creates list of individual steps
   - Uses regex to parse code blocks

2. **Incremental Execution** (`executeProblemSteps()`):
   - Executes one step at a time
   - Provides context: "This is step X out of Y"
   - Attempts recovery if a step fails
   - Can use `kubectl replace --force` for updates

### When to Use

- Complex multi-step fixes
- Cases where steps may fail and need recovery
- Debugging step-by-step execution
- Testing incremental problem-solving

### Limitations

- No metrics collection implemented
- Regex parsing may miss complex command formats
- Step boundaries may not be clear

---

## 4. SingleAgent

**Location**: `debug_assistant_latest/agents.py:337-439`

**Purpose**: Combined reasoning and action in one agent with embedded RAG

### Unique Architecture

- **No separation**: Single agent does analysis and execution
- **Embedded RAG**: Knowledge base built into agent
- **Direct access**: Uses phi.knowledge.WebsiteKnowledgeBase

### Configuration

```python
knowledge_base = WebsiteKnowledgeBase(
    urls=self.config["api-agent"].get("knowledge", []),
    max_links=10,
    vector_db=PgVector(
        table_name="ai.local_rag_documents_singleAgent",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)
```

### Advantages

- Simpler architecture (one agent vs. three)
- Potentially faster (no agent handoffs)
- Direct reasoning-to-action connection

### Disadvantages

- Less modular
- Harder to debug specific phases
- No independent verification
- Cannot compare different analysis vs. execution models

### When to Use

- Experimental comparison with multi-agent approach
- Simplified deployment scenarios
- Research on agent architecture effectiveness

---

## 5. AgentVerification_v1 (File-Based Verification)

**Location**: `debug_assistant_latest/agents.py:647-844`

**Purpose**: Verifies fixes by checking file contents and pod status

### Verification Strategy

1. **File Content Verification**:
   - Uses `cat`, `grep` to check file changes
   - Validates YAML modifications
   - Confirms Dockerfile changes

2. **Pod Status Check**:
   - Runs `kubectl get pods`
   - Checks for Running state
   - Verifies container readiness

3. **Log Verification** (secondary):
   - Attempts `kubectl logs` (with retries)
   - Acceptable if logs temporarily unavailable
   - Primary focus is files + pod status

### Instructions

```python
default_instructions = [
    "You are a verification agent tasked with verifying whether the debug agent successfully resolved the Kubernetes issue.",
    "Run diagnostic commands to check the current state of the cluster.",
    "Verify that the fixes claimed by the debug agent were actually applied.",
    "Always check the actual file contents using commands like 'cat' or 'grep'",
    "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
    "If kubectl logs fails, wait 5-10 seconds and try again up to 3 times",
    "Use <|VERIFIED|> if the YAML file has the correct changes AND pod is Running",
]
```

### Verification Tokens

- `<|VERIFIED|>`: Issue completely resolved
- `<|FAILED|>`: Issue NOT fixed
- `<|VERIFICATION_ERROR|>`: Cannot verify (system errors)

### Prompt Structure

```
=== ORIGINAL PROBLEM ===
{problem description}

=== DEBUG AGENT'S RESPONSE ===
{what debug agent claimed to do}

=== YOUR VERIFICATION TASK ===
1. Read the debug agent's response carefully
2. Identify what changes it claims to have made
3. Verify each claimed change is actually present in the system
4. Check if the original problem is actually resolved
5. Use kubectl commands and file inspection to verify the actual state
```

---

## 6. AgentVerification_v2 (State-Based Verification)

**Location**: `debug_assistant_latest/agents.py:441-645`

**Purpose**: Verifies fixes by checking actual cluster state and service accessibility

### Verification Strategy (More Robust)

1. **Problem-Centric Verification**:
   - Focuses on whether original problem is resolved
   - Not dependent on debug agent's claims
   - Checks actual observed behavior

2. **Comprehensive State Checks**:
   - Pod status and readiness
   - Service endpoints
   - Actual HTTP accessibility (via minikube service)
   - Event logs for errors

3. **Service Testing**:
   ```bash
   minikube -p lamap service <service-name> --url
   curl -v <url>
   ```

### Step-by-Step Procedure

```python
### STEP-BY-STEP VERIFICATION PROCEDURE (follow exactly in order)
1. Run `kubectl get pods` → confirm all expected pods exist and are in Running state
2. For each expected pod, run `kubectl describe pod <pod-name>` → check Events for errors
3. If relevant service YAML exists, run `kubectl get service <service-name>` → confirm Service exists
4. If a Service is running:
   - Run: `minikube -p {profile} service <service-name> --url`
   - Take the URL(s) returned and test with `curl -v <url>`
5. If Ingress exists, get the ingress address and test the hostname/path
```

### Key Differences from v1

| Aspect | v1 | v2 |
|--------|----|----|
| Focus | File changes + pod status | Actual service functionality |
| Testing | Static verification | Dynamic testing (curl) |
| Service checks | Basic existence | Full accessibility test |
| Minikube usage | Not used | Uses minikube service command |
| Claim dependency | Checks debug agent claims | Independent of claims |

### When to Use v1 vs v2

**Use v1 when**:
- Focus on configuration correctness
- File changes are the primary concern
- No services to test (pod-only issues)
- Faster verification needed

**Use v2 when**:
- Service accessibility is critical
- End-to-end functionality matters
- More robust verification needed
- Research comparing verification strategies

---

## Agent Interaction Patterns

### Pattern 1: Sequential Pipeline (allStepsAtOnce)

```python
# 1. Knowledge Agent
apiAgent = AgentAPI("api-agent", config)
apiAgent.setupAgent()
apiAgent.askQuestion()

# 2. Debug Agent
debugAgent = AgentDebug("debug-agent", config)
debugAgent.agentAPIResponse = apiAgent.response  # Pass knowledge to debug
debugAgent.setupAgent()
debug_metrics = debugAgent.askQuestion()

# 3. Verification Agent
verificationAgent = AgentVerification_v2("verification-agent", config)
verificationAgent.debugAgentResponse = debugAgent.response  # Pass debug response
verificationAgent.setupAgent()
verification_metrics = verificationAgent.askQuestion()
```

### Pattern 2: Independent Agent (singleAgent)

```python
# Single agent with embedded knowledge
agent = SingleAgent("single-agent", config)
agent.setupAgent()  # Includes RAG setup
agent.askQuestion()  # Does both reasoning and action
```

---

## Tool Integration: BetterShellTools

**Location**: `better_shell.py`

**Purpose**: Custom wrapper around phi.tools.ShellTools with enhancements

### Why Custom Tool?

Standard shell tools may have limitations:
- Timeout handling
- Output formatting
- Error reporting
- Command safety checks

### Integration in Agents

```python
self.agent = llmAgent(
    model=model,
    tools=[BetterShellTools()],  # Custom shell tool
    debug_mode=True,
    show_tool_calls=True,
)
```

---

## Configuration Best Practices

### Model Selection

**For Knowledge Agent (RAG queries)**:
- Llama3.1:70b - Good balance, local
- GPT-4o - High quality, paid
- Gemini-1.5-flash - Fast, low cost

**For Debug Agent (Command execution)**:
- GPT-4o - Most reliable
- o3-mini - Good reasoning, higher cost
- Gemini-1.5-flash - Fast, budget-friendly

**For Verification Agent**:
- GPT-4o - Reliable verification
- Temperature: 0.3 (more deterministic)

### Instructions Guidelines

**DO include**:
- Clear task description
- Specific command patterns to use
- Output format requirements
- Safety constraints

**DON'T include**:
- Contradictory instructions
- Vague directions ("try your best")
- Assumptions about environment

### Example Good Configuration

```json
{
  "debug-agent": {
    "model": "gpt-4o",
    "instructions": [
      "Execute kubectl commands to diagnose and fix the issue",
      "Modify configuration files only when necessary",
      "Always delete and reapply after modifying YAML files",
      "Use <|SOLVED|> when the pod is running and ready"
    ],
    "guidelines": [
      "Use real resource names from kubectl output",
      "Do not use kubectl edit or interactive commands",
      "Rebuild containers after modifying Dockerfile",
      "Verify each command succeeded before proceeding"
    ]
  }
}
```

---

## Debugging Agent Issues

### Common Problems

1. **Agent hangs indefinitely**
   - Likely using `kubectl logs -f` or similar blocking command
   - Check tool usage rules enforcement
   - Timeout will trigger after 480s

2. **Agent reports success but verification fails**
   - Agent misinterpreted command output
   - Verification agent is correct (trust verification)
   - Common with complex multi-step fixes

3. **Agent repeats same failed command**
   - Tool call limit not enforced
   - Instructions may need strengthening
   - Consider adding explicit "do not repeat" in guidelines

4. **Agent uses placeholder names**
   - Not running diagnostic commands first
   - Add explicit instruction to get resource names
   - Example: "Run `kubectl get pods` before describing a pod"

### Logging and Debugging

**Enable detailed logging**:
```python
self.agent = llmAgent(
    model=model,
    tools=[BetterShellTools()],
    debug_mode=True,  # Enables detailed logging
    show_tool_calls=True,  # Shows tool invocations
)
```

**Check agent response**:
```python
print(f"Agent response: {agent.response}")
print(f"Agent status: {agent.debugStatus}")
```

**Review metrics**:
```python
print(f"Tokens used: {metrics['total_tokens']}")
print(f"Cost: ${metrics['cost']}")
print(f"Duration: {metrics['duration_s']}s")
```

---

## Performance Optimization

### Reducing Token Usage

1. **Limit file contents in prompts**:
   - Only include relevant sections
   - Summarize large files

2. **Optimize knowledge base**:
   - Fewer documents
   - More focused documentation
   - Adjust `num_documents` in knowledge config

3. **Shorter instructions**:
   - Remove redundant guidelines
   - Use concise language

### Reducing Execution Time

1. **Use faster models**:
   - Gemini-1.5-flash (fastest)
   - Local Ollama models (no API latency)

2. **Optimize RAG**:
   - Fewer knowledge sources
   - Smaller max_links value
   - Cache embeddings

3. **Parallel operations**:
   - Currently sequential (extension opportunity)

---

## Extension: Adding Custom Agents

### Template

```python
class CustomAgent(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.custom_attribute = None

    def prepareAgent(self):
        """Initialize your LLM and tools"""
        model_name = self.agentProperties["model"]
        # Model selection logic

        self.agent = llmAgent(
            model=model,
            tools=[BetterShellTools()],
            instructions=self.agentProperties.get("instructions", []),
            guidelines=self.agentProperties.get("guidelines", [])
        )

    def preparePrompt(self):
        """Build your prompt"""
        self.prompt = f"Custom prompt: {self.config['custom-field']}"
        # Add file contents if needed
        for fileType in ["deployment", "application"]:
            self.prompt = traverseRelevantFiles(self.config, fileType, self.prompt)

    def askQuestion(self):
        """Execute your agent logic"""
        response = self.agent.run(self.prompt)
        # Process response
        return metrics_entry
```

### Integration

1. Add to `agents.py`
2. Import in `main.py`
3. Create test function in `main.py`
4. Add configuration section to config.json

---

## Summary: Agent Selection Guide

| Use Case | Agent Choice | Rationale |
|----------|-------------|-----------|
| Standard testing | AgentAPI + AgentDebug + AgentVerification_v2 | Most robust, well-tested |
| Quick iteration | AgentAPI + AgentDebug + AgentVerification_v1 | Faster verification |
| Complex multi-step | AgentDebugStepByStep | Better recovery handling |
| Architectural research | SingleAgent | Compare with multi-agent |
| Service testing focus | AgentVerification_v2 | Tests actual accessibility |
| File configuration focus | AgentVerification_v1 | Faster for config issues |
