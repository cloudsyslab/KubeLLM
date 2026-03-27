[Skip to main content](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#content-area)
Join us May 13th & May 14th at Interrupt, the Agent Conference by LangChain. [Buy tickets >](https://interrupt.langchain.com/)
[Docs by LangChain home page![light logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-dark-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=5babf1a1962208fd7eed942fa2432ecb)![dark logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-light-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=0bcd2a1f2599ed228bcedf0f535b45b1)](https://docs.langchain.com/)![https://mintlify.s3.us-west-1.amazonaws.com/langchain-5e9cc07a/images/brand/langchain-icon.png](https://mintlify.s3.us-west-1.amazonaws.com/langchain-5e9cc07a/images/brand/langchain-icon.png)Open source
Search...
Ctrl K
  * [](https://chat.langchain.com/)
  * [](https://github.com/langchain-ai)
  * [Try LangSmith](https://smith.langchain.com/)
  * [Try LangSmith](https://smith.langchain.com/)


Search...
Navigation
Multi-agent
Handoffs
[Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview)[LangChain](https://docs.langchain.com/oss/python/langchain/overview)[LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)[Integrations](https://docs.langchain.com/oss/python/integrations/providers/overview)[Learn](https://docs.langchain.com/oss/python/learn)[Reference](https://docs.langchain.com/oss/python/reference/overview)[Contribute](https://docs.langchain.com/oss/python/contributing/overview)
Python
  * [Overview](https://docs.langchain.com/oss/python/langchain/overview)


##### Get started
  * [Install](https://docs.langchain.com/oss/python/langchain/install)
  * [Quickstart](https://docs.langchain.com/oss/python/langchain/quickstart)
  * [Changelog](https://docs.langchain.com/oss/python/releases/changelog)
  * [Philosophy](https://docs.langchain.com/oss/python/langchain/philosophy)


##### Core components
  * [Agents](https://docs.langchain.com/oss/python/langchain/agents)
  * [Models](https://docs.langchain.com/oss/python/langchain/models)
  * [Messages](https://docs.langchain.com/oss/python/langchain/messages)
  * [Tools](https://docs.langchain.com/oss/python/langchain/tools)
  * [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)
  * [Streaming](https://docs.langchain.com/oss/python/langchain/streaming)
  * [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)


##### Middleware
  * [Overview](https://docs.langchain.com/oss/python/langchain/middleware/overview)
  * [Prebuilt middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in)
  * [Custom middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom)


##### Frontend
  * [Overview](https://docs.langchain.com/oss/python/langchain/frontend/overview)
  * Patterns
  * Integrations


##### Advanced usage
  * [Guardrails](https://docs.langchain.com/oss/python/langchain/guardrails)
  * [Runtime](https://docs.langchain.com/oss/python/langchain/runtime)
  * [Context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering)
  * [Model Context Protocol (MCP)](https://docs.langchain.com/oss/python/langchain/mcp)
  * [Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
  * Multi-agent
    * [Overview](https://docs.langchain.com/oss/python/langchain/multi-agent)
    * [Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)
    * [Handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)
    * [Skills](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)
    * [Router](https://docs.langchain.com/oss/python/langchain/multi-agent/router)
    * [Custom workflow](https://docs.langchain.com/oss/python/langchain/multi-agent/custom-workflow)
  * [Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
  * [Long-term memory](https://docs.langchain.com/oss/python/langchain/long-term-memory)


##### Agent development
  * [LangSmith Studio](https://docs.langchain.com/oss/python/langchain/studio)
  * Test
  * [Agent Chat UI](https://docs.langchain.com/oss/python/langchain/ui)


##### Deploy with LangSmith
  * [Deployment](https://docs.langchain.com/oss/python/langchain/deploy)
  * [Observability](https://docs.langchain.com/oss/python/langchain/observability)


On this page
  * [Key characteristics](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#key-characteristics)
  * [When to use](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#when-to-use)
  * [Basic implementation](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#basic-implementation)
  * [Implementation approaches](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#implementation-approaches)
  * [Single agent with middleware](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#single-agent-with-middleware)
  * [Multiple agent subgraphs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#multiple-agent-subgraphs)
  * [Context engineering](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#context-engineering)
  * [Implementation considerations](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#implementation-considerations)


[Advanced usage](https://docs.langchain.com/oss/python/langchain/guardrails)
[Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent/index)
# Handoffs
Copy page
Copy page
In the **handoffs** architecture, behavior changes dynamically based on state. The core mechanism: [tools](https://docs.langchain.com/oss/python/langchain/tools) update a state variable (e.g., `current_step` or `active_agent`) that persists across turns, and the system reads this variable to adjust behavior—either applying different configuration (system prompt, tools) or routing to a different [agent](https://docs.langchain.com/oss/python/langchain/agents). This pattern supports both handoffs between distinct agents and dynamic configuration changes within a single agent.
The term **handoffs** was coined by [OpenAI](https://openai.github.io/openai-agents-python/handoffs/) for using tool calls (e.g., `transfer_to_sales_agent`) to transfer control between agents or states.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#key-characteristics)
Key characteristics
  * State-driven behavior: Behavior changes based on a state variable (e.g., `current_step` or `active_agent`)
  * Tool-based transitions: Tools update the state variable to move between states
  * Direct user interaction: Each state’s configuration handles user messages directly
  * Persistent state: State survives across conversation turns


## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#when-to-use)
When to use
Use the handoffs pattern when you need to enforce sequential constraints (unlock capabilities only after preconditions are met), the agent needs to converse directly with the user across different states, or you’re building multi-stage conversational flows. This pattern is particularly valuable for customer support scenarios where you need to collect information in a specific sequence—for example, collecting a warranty ID before processing a refund.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#basic-implementation)
Basic implementation
The core mechanism is a [tool](https://docs.langchain.com/oss/python/langchain/tools) that returns a [`Command`](https://docs.langchain.com/oss/python/langgraph/graph-api#command) to update state, triggering a transition to a new step or agent:
Copy

```
from langchain.tools import tool
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def transfer_to_specialist(runtime) -> Command:
    """Transfer to the specialist agent."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="Transferred to specialist",
                    tool_call_id=runtime.tool_call_id  
                )
            ],
            "current_step": "specialist"  # Triggers behavior change
        }
    )

```

**Why include a`ToolMessage`?** When an LLM calls a tool, it expects a response. The `ToolMessage` with matching `tool_call_id` completes this request-response cycle—without it, the conversation history becomes malformed. This is required whenever your handoff tool updates messages.
For a complete implementation, see the tutorial below.
## [Tutorial: Build customer support with handoffs Learn how to build a customer support agent using the handoffs pattern, where a single agent transitions between different configurations. Learn more ](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs-customer-support)
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#implementation-approaches)
Implementation approaches
There are two ways to implement handoffs: **[single agent with middleware](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#single-agent-with-middleware)** (one agent with dynamic configuration) or **[multiple agent subgraphs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#multiple-agent-subgraphs)** (distinct agents as graph nodes).
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#single-agent-with-middleware)
Single agent with middleware
A single agent changes its behavior based on state. Middleware intercepts each model call and dynamically adjusts the system prompt and available tools. Tools update the state variable to trigger transitions:
Copy

```
from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def record_warranty_status(
    status: str,
    runtime: ToolRuntime[None, SupportState]
) -> Command:
    """Record warranty status and transition to next step."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Warranty status recorded: {status}",
                    tool_call_id=runtime.tool_call_id
                )
            ],
            "warranty_status": status,
            "current_step": "specialist"  # Update state to trigger transition
        }
    )

```

Complete example: Customer support with middleware
Copy

```
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Callable

# 1. Define state with current_step tracker
class SupportState(AgentState):
    """Track which step is currently active."""
    current_step: str = "triage"
    warranty_status: str | None = None

# 2. Tools update current_step via Command
@tool
def record_warranty_status(
    status: str,
    runtime: ToolRuntime[None, SupportState]
) -> Command:
    """Record warranty status and transition to next step."""
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"Warranty status recorded: {status}",
                tool_call_id=runtime.tool_call_id
            )
        ],
        "warranty_status": status,
        # Transition to next step
        "current_step": "specialist"
    })

# 3. Middleware applies dynamic configuration based on current_step
@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Configure agent behavior based on current_step."""
    step = request.state.get("current_step", "triage")

    # Map steps to their configurations
    configs = {
        "triage": {
            "prompt": "Collect warranty information...",
            "tools": [record_warranty_status]
        },
        "specialist": {
            "prompt": "Provide solutions based on warranty: {warranty_status}",
            "tools": [provide_solution, escalate]
        }
    }

    config = configs[step]
    request = request.override(
        system_prompt=config["prompt"].format(**request.state),
        tools=config["tools"]
    )
    return handler(request)

# 4. Create agent with middleware
agent = create_agent(
    model,
    tools=[record_warranty_status, provide_solution, escalate],
    state_schema=SupportState,
    middleware=[apply_step_config],
    checkpointer=InMemorySaver()  # Persist state across turns  #
)

```

### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#multiple-agent-subgraphs)
Multiple agent subgraphs
Multiple distinct agents exist as separate nodes in a graph. Handoff tools navigate between agent nodes using `Command.PARENT` to specify which node to execute next.
Subgraph handoffs require careful **[context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering)**. Unlike single-agent middleware (where message history flows naturally), you must explicitly decide what messages pass between agents. Get this wrong and agents receive malformed conversation history or bloated context. See [Context engineering](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#context-engineering) below.
Copy

```
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command

@tool
def transfer_to_sales(
    runtime: ToolRuntime,
) -> Command:
    """Transfer to the sales agent."""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="Transferred to sales agent",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT
    )

```

Complete example: Sales and support with handoffs
This example shows a multi-agent system with separate sales and support agents. Each agent is a separate graph node, and handoff tools allow agents to transfer conversations to each other.
Copy

```
from typing import Literal

from langchain.agents import AgentState, create_agent
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing_extensions import NotRequired


# 1. Define state with active_agent tracker
class MultiAgentState(AgentState):
    active_agent: NotRequired[str]


# 2. Create handoff tools
@tool
def transfer_to_sales(
    runtime: ToolRuntime,
) -> Command:
    """Transfer to the sales agent."""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="Transferred to sales agent from support agent",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )


@tool
def transfer_to_support(
    runtime: ToolRuntime,
) -> Command:
    """Transfer to the support agent."""
    last_ai_message = next(
        msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)
    )
    transfer_message = ToolMessage(
        content="Transferred to support agent from sales agent",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="support_agent",
        update={
            "active_agent": "support_agent",
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )


# 3. Create agents with handoff tools
sales_agent = create_agent(
    model="anthropic:claude-sonnet-4-20250514",
    tools=[transfer_to_support],
    system_prompt="You are a sales agent. Help with sales inquiries. If asked about technical issues or support, transfer to the support agent.",
)

support_agent = create_agent(
    model="anthropic:claude-sonnet-4-20250514",
    tools=[transfer_to_sales],
    system_prompt="You are a support agent. Help with technical issues. If asked about pricing or purchasing, transfer to the sales agent.",
)


# 4. Create agent nodes that invoke the agents
def call_sales_agent(state: MultiAgentState) -> Command:
    """Node that calls the sales agent."""
    response = sales_agent.invoke(state)
    return response


def call_support_agent(state: MultiAgentState) -> Command:
    """Node that calls the support agent."""
    response = support_agent.invoke(state)
    return response


# 5. Create router that checks if we should end or continue
def route_after_agent(
    state: MultiAgentState,
) -> Literal["sales_agent", "support_agent", "__end__"]:
    """Route based on active_agent, or END if the agent finished without handoff."""
    messages = state.get("messages", [])

    # Check the last message - if it's an AIMessage without tool calls, we're done
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
            return "__end__"

    # Otherwise route to the active agent
    active = state.get("active_agent", "sales_agent")
    return active if active else "sales_agent"


def route_initial(
    state: MultiAgentState,
) -> Literal["sales_agent", "support_agent"]:
    """Route to the active agent based on state, default to sales agent."""
    return state.get("active_agent") or "sales_agent"


# 6. Build the graph
builder = StateGraph(MultiAgentState)
builder.add_node("sales_agent", call_sales_agent)
builder.add_node("support_agent", call_support_agent)

# Start with conditional routing based on initial active_agent
builder.add_conditional_edges(START, route_initial, ["sales_agent", "support_agent"])

# After each agent, check if we should end or route to another agent
builder.add_conditional_edges(
    "sales_agent", route_after_agent, ["sales_agent", "support_agent", END]
)
builder.add_conditional_edges(
    "support_agent", route_after_agent, ["sales_agent", "support_agent", END]
)

graph = builder.compile()
result = graph.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Hi, I'm having trouble with my account login. Can you help?",
            }
        ]
    }
)

for msg in result["messages"]:
    msg.pretty_print()

```

Use **single agent with middleware** for most handoffs use cases—it’s simpler. Only use **multiple agent subgraphs** when you need bespoke agent implementations (e.g., a node that’s itself a complex graph with reflection or retrieval steps).
#### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#context-engineering)
Context engineering
With subgraph handoffs, you control exactly what messages flow between agents. This precision is essential for maintaining valid conversation history and avoiding context bloat that could confuse downstream agents. For more on this topic, see [context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering). **Handling context during handoffs** When handing off between agents, you need to ensure the conversation history remains valid. LLMs expect tool calls to be paired with their responses, so when using `Command.PARENT` to hand off to another agent, you must include both:
  1. **The`AIMessage` containing the tool call** (the message that triggered the handoff)
  2. **A`ToolMessage` acknowledging the handoff** (the artificial response to that tool call)

Without this pairing, the receiving agent will see an incomplete conversation and may produce errors or unexpected behavior. The example below assumes only the handoff tool was called (no parallel tool calls):
Copy

```
@tool
def transfer_to_sales(runtime: ToolRuntime) -> Command:
    # Get the AI message that triggered this handoff
    last_ai_message = runtime.state["messages"][-1]

    # Create an artificial tool response to complete the pair
    transfer_message = ToolMessage(
        content="Transferred to sales agent",
        tool_call_id=runtime.tool_call_id,
    )

    return Command(
        goto="sales_agent",
        update={
            "active_agent": "sales_agent",
            # Pass only these two messages, not the full subagent history
            "messages": [last_ai_message, transfer_message],
        },
        graph=Command.PARENT,
    )

```

**Why not pass all subagent messages?** While you could include the full subagent conversation in the handoff, this often creates problems. The receiving agent may become confused by irrelevant internal reasoning, and token costs increase unnecessarily. By passing only the handoff pair, you keep the parent graph’s context focused on high-level coordination. If the receiving agent needs additional context, consider summarizing the subagent’s work in the ToolMessage content instead of passing raw message history.
**Returning control to the user** When returning control to the user (ending the agent’s turn), ensure the final message is an `AIMessage`. This maintains valid conversation history and signals to the user interface that the agent has finished its work.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs#implementation-considerations)
Implementation considerations
As you design your multi-agent system, consider:
  * **Context filtering strategy** : Will each agent receive full conversation history, filtered portions, or summaries? Different agents may need different context depending on their role.
  * **Tool semantics** : Clarify whether handoff tools only update routing state or also perform side effects. For example, should `transfer_to_sales()` also create a support ticket, or should that be a separate action?
  * **Token efficiency** : Balance context completeness against token costs. Summarization and selective context passing become more important as conversations grow longer.


* * *
[Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/multi-agent/handoffs.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
[Connect these docs](https://docs.langchain.com/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
Was this page helpful?
YesNo
[ Subagents Previous ](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)[ Skills Next ](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)
Ctrl+I
[Docs by LangChain home page![light logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-dark-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=5babf1a1962208fd7eed942fa2432ecb)![dark logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-light-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=0bcd2a1f2599ed228bcedf0f535b45b1)](https://docs.langchain.com/)
[github](https://github.com/langchain-ai)[x](https://x.com/LangChain)[linkedin](https://www.linkedin.com/company/langchain)[youtube](https://www.youtube.com/@LangChain)
Resources
[Forum](https://forum.langchain.com/)[Changelog](https://changelog.langchain.com/)[LangChain Academy](https://academy.langchain.com/)[Trust Center](https://trust.langchain.com/)
Company
[Home](https://langchain.com/)[About](https://langchain.com/about)[Careers](https://langchain.com/careers)[Blog](https://blog.langchain.com/)
[github](https://github.com/langchain-ai)[x](https://x.com/LangChain)[linkedin](https://www.linkedin.com/company/langchain)[youtube](https://www.youtube.com/@LangChain)

