[Skip to main content](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#content-area)
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
Subagents
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
  * [Key characteristics](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#key-characteristics)
  * [When to use](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#when-to-use)
  * [Basic implementation](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#basic-implementation)
  * [Design decisions](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#design-decisions)
  * [Sync vs. async](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#sync-vs-async)
  * [Synchronous (default)](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#synchronous-default)
  * [Asynchronous](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#asynchronous)
  * [Tool patterns](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-patterns)
  * [Tool per agent](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-per-agent)
  * [Single dispatch tool](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#single-dispatch-tool)
  * [Context engineering](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#context-engineering)
  * [Subagent specs](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-specs)
  * [System prompt enumeration](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#system-prompt-enumeration)
  * [Enum constraint on dispatch tool](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#enum-constraint-on-dispatch-tool)
  * [Tool-based discovery](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-based-discovery)
  * [Subagent inputs](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-inputs)
  * [Subagent outputs](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-outputs)
  * [Checkpointing and state inspection](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#checkpointing-and-state-inspection)


[Advanced usage](https://docs.langchain.com/oss/python/langchain/guardrails)
[Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent/index)
# Subagents
Copy page
Copy page
In the **subagents** architecture, a central main [agent](https://docs.langchain.com/oss/python/langchain/agents) (often referred to as a **supervisor**) coordinates subagents by calling them as [tools](https://docs.langchain.com/oss/python/langchain/tools). The main agent decides which subagent to invoke, what input to provide, and how to combine results. Subagents are stateless—they don’t remember past interactions, with all conversation memory maintained by the main agent. This provides [context](https://docs.langchain.com/oss/python/langchain/context-engineering) isolation: each subagent invocation works in a clean context window, preventing context bloat in the main conversation.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#key-characteristics)
Key characteristics
  * Centralized control: All routing passes through the main agent
  * No direct user interaction: Subagents return results to the main agent, not the user (though you can use [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts#pause-using-interrupt) within a subagent to allow user interaction)
  * Subagents via tools: Subagents are invoked via tools
  * Parallel execution: The main agent can invoke multiple subagents in a single turn


**Supervisor vs. Router** : A supervisor agent (this pattern) is different from a [router](https://docs.langchain.com/oss/python/langchain/multi-agent/router). The supervisor is a full agent that maintains conversation context and dynamically decides which subagents to call across multiple turns. A router is typically a single classification step that dispatches to agents without maintaining ongoing conversation state.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#when-to-use)
When to use
Use the subagents pattern when you have multiple distinct domains (e.g., calendar, email, CRM, database), subagents don’t need to converse directly with users, or you want centralized workflow control. For simpler cases with just a few [tools](https://docs.langchain.com/oss/python/langchain/tools), use a [single agent](https://docs.langchain.com/oss/python/langchain/agents).
**Need user interaction within a subagent?** While subagents typically return results to the main agent rather than conversing directly with users, you can use [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts#pause-using-interrupt) within a subagent to pause execution and gather user input. This is useful when a subagent needs clarification or approval before proceeding. The main agent remains the orchestrator, but the subagent can collect information from the user mid-task.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#basic-implementation)
Basic implementation
The core mechanism wraps a subagent as a tool that the main agent can call:
Copy

```
from langchain.tools import tool
from langchain.agents import create_agent

# Create a subagent
subagent = create_agent(model="anthropic:claude-sonnet-4-20250514", tools=[...])

# Wrap it as a tool
@tool("research", description="Research a topic and return findings")
def call_research_agent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Main agent with subagent as a tool
main_agent = create_agent(model="anthropic:claude-sonnet-4-20250514", tools=[call_research_agent])

```

## [Tutorial: Build a personal assistant with subagents Learn how to build a personal assistant using the subagents pattern, where a central main agent (supervisor) coordinates specialized worker agents. Learn more ](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant)
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#design-decisions)
Design decisions
When implementing the subagents pattern, you’ll make several key design choices. This table summarizes the options—each is covered in detail in the sections below.  
| Decision  | Options  |  
| --- | --- |  
| [**Sync vs. async**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#sync-vs-async)  | Sync (blocking) vs. async (background)  |  
| [**Tool patterns**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-patterns)  | Tool per agent vs. single dispatch tool  |  
| [**Subagent specs**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-specs)  | System prompt vs. enum constraint vs. tool-based discovery (single dispatch tool only)  |  
| [**Subagent inputs**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-inputs)  | Query only vs. full context  |  
| [**Subagent outputs**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-outputs)  | Subagent result vs full conversation history  |  
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#sync-vs-async)
Sync vs. async
Subagent execution can be **synchronous** (blocking) or **asynchronous** (background). Your choice depends on whether the main agent needs the result to continue.  
| Mode  | Main agent behavior  | Best for  | Tradeoff  |  
| --- | --- | --- | --- |  
| **Sync**  | Waits for subagent to complete  | Main agent needs result to continue  | Simple, but blocks the conversation  |  
| **Async**  | Continues while subagent runs in background  | Independent tasks, user shouldn’t wait  | Responsive, but more complex  |  
Not to be confused with Python’s `async`/`await`. Here, “async” means the main agent kicks off a background job (typically in a separate process or service) and continues without blocking.
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#synchronous-default)
Synchronous (default)
By default, subagent calls are **synchronous** : the main agent waits for each subagent to complete before continuing. Use sync when the main agent’s next action depends on the subagent’s result. **When to use sync:**
  * Main agent needs the subagent’s result to formulate its response
  * Tasks have order dependencies (e.g., fetch data ? analyze ? respond)
  * Subagent failures should block the main agent’s response

**Tradeoffs:**
  * Simple implementation—just call and wait
  * User sees no response until all subagents complete
  * Long-running tasks freeze the conversation


### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#asynchronous)
Asynchronous
Use **asynchronous execution** when the subagent’s work is independent—the main agent doesn’t need the result to continue conversing with the user. The main agent kicks off a background job and remains responsive. **When to use async:**
  * Subagent work is independent of the main conversation flow
  * Users should be able to continue chatting while work happens
  * You want to run multiple independent tasks in parallel

**Three-tool pattern:**
  1. **Start job** : Kicks off the background task, returns a job ID
  2. **Check status** : Returns current state (pending, running, completed, failed)
  3. **Get result** : Retrieves the completed result

**Handling job completion:** When a job finishes, your application needs to notify the user. One approach: surface a notification that, when clicked, sends a `HumanMessage` like “Check job_123 and summarize the results.”
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-patterns)
Tool patterns
There are two main ways to expose subagents as tools:  
| Pattern  | Best for  | Trade-off  |  
| --- | --- | --- |  
| [**Tool per agent**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-per-agent)  | Fine-grained control over each subagent’s input/output  | More setup, but more customization  |  
| [**Single dispatch tool**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#single-dispatch-tool)  | Many agents, distributed teams, convention over configuration  | Simpler composition, less per-agent customization  |  
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-per-agent)
Tool per agent
The key idea is wrapping subagents as tools that the main agent can call:
Copy

```
from langchain.tools import tool
from langchain.agents import create_agent

# Create a sub-agent
subagent = create_agent(model="...", tools=[...])

# Wrap it as a tool  #
@tool("subagent_name", description="subagent_description")
def call_subagent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Main agent with subagent as a tool  #
main_agent = create_agent(model="...", tools=[call_subagent])

```

The main agent invokes the subagent tool when it decides the task matches the subagent’s description, receives the result, and continues orchestration. See [Context engineering](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#context-engineering) for fine-grained control.
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#single-dispatch-tool)
Single dispatch tool
An alternative approach uses a single parameterized tool to invoke ephemeral sub-agents for independent tasks. Unlike the [tool per agent](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-per-agent) approach where each sub-agent is wrapped as a separate tool, this uses a convention-based approach with a single `task` tool: the task description is passed as a human message to the sub-agent, and the sub-agent’s final message is returned as the tool result. Use this approach when you want to distribute agent development across multiple teams, need to isolate complex tasks into separate context windows, need a scalable way to add new agents without modifying the coordinator, or prefer convention over customization. This approach trades flexibility in context engineering for simplicity in agent composition and strong context isolation. **Key characteristics:**
  * Single task tool: One parameterized tool that can invoke any registered sub-agent by name
  * Convention-based invocation: Agent selected by name, task passed as human message, final message returned as tool result
  * Team distribution: Different teams can develop and deploy agents independently
  * Agent discovery: Sub-agents can be discovered via system prompt (listing available agents) or through [progressive disclosure](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant) (loading agent information on-demand via tools)


An interesting aspect of this approach is that sub-agents may have the exact same capabilities as the main agent. In such cases, invoking a sub-agent is **really about context isolation** as the primary reason—allowing complex, multi-step tasks to run in isolated context windows without bloating the main agent’s conversation history. The sub-agent completes its work autonomously and returns only a concise summary, keeping the main thread focused and efficient.
Agent registry with task dispatcher
Copy

```
from langchain.tools import tool
from langchain.agents import create_agent

# Sub-agents developed by different teams
research_agent = create_agent(
    model="gpt-4.1",
    prompt="You are a research specialist..."
)

writer_agent = create_agent(
    model="gpt-4.1",
    prompt="You are a writing specialist..."
)

# Registry of available sub-agents
SUBAGENTS = {
    "research": research_agent,
    "writer": writer_agent,
}

@tool
def task(
    agent_name: str,
    description: str
) -> str:
    """Launch an ephemeral subagent for a task.

    Available agents:
    - research: Research and fact-finding
    - writer: Content creation and editing
    """
    agent = SUBAGENTS[agent_name]
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": description}
        ]
    })
    return result["messages"][-1].content

# Main coordinator agent
main_agent = create_agent(
    model="gpt-4.1",
    tools=[task],
    system_prompt=(
        "You coordinate specialized sub-agents. "
        "Available: research (fact-finding), "
        "writer (content creation). "
        "Use the task tool to delegate work."
    ),
)

```

## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#context-engineering)
Context engineering
Control how context flows between the main agent and its subagents:  
| Category  | Purpose  | Impacts  |  
| --- | --- | --- |  
| [**Subagent specs**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-specs)  | Ensure subagents are invoked when they should be  | Main agent routing decisions  |  
| [**Subagent inputs**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-inputs)  | Ensure subagents can execute well with optimized context  | Subagent performance  |  
| [**Subagent outputs**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-outputs)  | Ensure the supervisor can act on subagent results  | Main agent performance  |  
See also our comprehensive guide on [context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering) for agents.
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-specs)
Subagent specs
The **names** and **descriptions** associated with subagents are the primary way the main agent knows which subagents to invoke. These are prompting levers—choose them carefully.
  * **Name** : How the main agent refers to the sub-agent. Keep it clear and action-oriented (e.g., `research_agent`, `code_reviewer`).
  * **Description** : What the main agent knows about the sub-agent’s capabilities. Be specific about what tasks it handles and when to use it.

For the [single dispatch tool](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#single-dispatch-tool) design, you must additionally provide the main agent with information about the subagents it can invoke. You can provide this information in different ways based on the number of agents and whether your registry is static or dynamic:  
| Method  | Best for  | Tradeoff  |  
| --- | --- | --- |  
| **System prompt enumeration**  | Small, static agent lists (< 10 agents)  | Simple, but requires prompt updates when agents change  |  
| **Enum constraint**  | Small, static agent lists (< 10 agents)  | Type-safe and explicit, but requires code changes when agents change  |  
| **Tool-based discovery**  | Large or dynamic agent registries  | Flexible and scalable, but adds complexity  |  
#### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#system-prompt-enumeration)
System prompt enumeration
List available agents directly in the main agent’s system prompt. The main agent sees the list of agents and their descriptions as part of its instructions. **When to use:**
  * You have a small, fixed set of agents (< 10)
  * Agent registry rarely changes
  * You want the simplest implementation

**Example:**
Copy

```
main_agent = create_agent(
    model="...",
    tools=[task],
    system_prompt=(
        "You coordinate specialized sub-agents. "
        "Available agents:\n"
        "- research: Research and fact-finding\n"
        "- writer: Content creation and editing\n"
        "- reviewer: Code and document review\n"
        "Use the task tool to delegate work."
    ),
)

```

#### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#enum-constraint-on-dispatch-tool)
Enum constraint on dispatch tool
Add an enum constraint to the `agent_name` parameter in your dispatch tool. This provides type safety and makes available agents explicit in the tool schema. **When to use:**
  * You have a small, fixed set of agents (< 10)
  * You want type safety and explicit agent names
  * You prefer schema-based validation over prompt-based guidance

**Example:**
Copy

```
from enum import Enum

class AgentName(str, Enum):
    RESEARCH = "research"
    WRITER = "writer"
    REVIEWER = "reviewer"

@tool
def task(
    agent_name: AgentName,  # Enum constraint
    description: str
) -> str:
    """Launch an ephemeral subagent for a task."""
    # ...

```

#### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#tool-based-discovery)
Tool-based discovery
Provide a separate tool (e.g., `list_agents` or `search_agents`) that the main agent can call to discover available agents on-demand. This enables progressive disclosure and supports dynamic registries. **When to use:**
  * You have many agents (> 10) or a growing registry
  * Agent registry changes frequently or is dynamic
  * You want to reduce prompt size and token usage
  * Different teams manage different agents independently

**Example:**
Copy

```
@tool
def list_agents(query: str = "") -> str:
    """List available subagents, optionally filtered by query."""
    agents = search_agent_registry(query)
    return format_agent_list(agents)

@tool
def task(agent_name: str, description: str) -> str:
    """Launch an ephemeral subagent for a task."""
    # ...

main_agent = create_agent(
    model="...",
    tools=[task, list_agents],
    system_prompt="Use list_agents to discover available subagents, then use task to invoke them."
)

```

### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-inputs)
Subagent inputs
Customize what context the subagent receives to execute its task. Add input that isn’t practical to capture in a static prompt—full message history, prior results, or task metadata—by pulling from the agent’s state.
Subagent inputs example
Copy

```
from langchain.agents import AgentState
from langchain.tools import tool, ToolRuntime

class CustomState(AgentState):
    example_state_key: str

@tool(
    "subagent1_name",
    description="subagent1_description"
)
def call_subagent1(query: str, runtime: ToolRuntime[None, CustomState]):
    # Apply any logic needed to transform the messages into a suitable input
    subagent_input = some_logic(query, runtime.state["messages"])
    result = subagent1.invoke({
        "messages": subagent_input,
        # You could also pass other state keys here as needed.
        # Make sure to define these in both the main and subagent's
        # state schemas.
        "example_state_key": runtime.state["example_state_key"]
    })
    return result["messages"][-1].content

```

### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#subagent-outputs)
Subagent outputs
Customize what the main agent receives back so it can make good decisions. Two strategies:
  1. **Prompt the sub-agent** : Specify exactly what should be returned. A common failure mode is that the sub-agent performs tool calls or reasoning but doesn’t include results in its final message—remind it that the supervisor only sees the final output.
  2. **Format in code** : Adjust or enrich the response before returning it. For example, pass specific state keys back in addition to the final text using a [`Command`](https://docs.langchain.com/oss/python/langgraph/graph-api#command).


Subagent outputs example
Copy

```
from typing import Annotated
from langchain.agents import AgentState
from langchain.tools import InjectedToolCallId
from langgraph.types import Command


@tool(
    "subagent1_name",
    description="subagent1_description"
)
def call_subagent1(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    result = subagent1.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return Command(update={
        # Pass back additional state from the subagent
        "example_state_key": result["example_state_key"],
        "messages": [
            ToolMessage(
                content=result["messages"][-1].content,
                tool_call_id=tool_call_id
            )
        ]
    })

```

## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents#checkpointing-and-state-inspection)
Checkpointing and state inspection
By default, subagents use the **inherited checkpointer** mode—each invocation starts with fresh state, supports [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts#pause-using-interrupt), and runs safely in parallel. If you need a subagent to maintain its own persistent conversation history across invocations, compile it with `checkpointer=True` (continuations mode). See [subgraph persistence](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#subgraph-persistence) for a full comparison of modes. Because subagents are called inside tool functions, LangGraph cannot [statically discover](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#view-subgraph-state) them. This means [`get_state` with `subgraphs`](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#view-subgraph-state) will not return subagent state. If you need to read nested graph state (e.g., during an [interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts#pause-using-interrupt)), invoke the subagent from a [node function](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#call-a-subgraph-inside-a-node) in a custom graph instead. See [subgraph persistence](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#subgraph-persistence) for details on how each mode affects state visibility.
* * *
[Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/multi-agent/subagents.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
[Connect these docs](https://docs.langchain.com/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
Was this page helpful?
YesNo
[ Multi-agent Previous ](https://docs.langchain.com/oss/python/langchain/multi-agent)[ Handoffs Next ](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)
Ctrl+I
[Docs by LangChain home page![light logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-dark-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=5babf1a1962208fd7eed942fa2432ecb)![dark logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-light-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=0bcd2a1f2599ed228bcedf0f535b45b1)](https://docs.langchain.com/)
[github](https://github.com/langchain-ai)[x](https://x.com/LangChain)[linkedin](https://www.linkedin.com/company/langchain)[youtube](https://www.youtube.com/@LangChain)
Resources
[Forum](https://forum.langchain.com/)[Changelog](https://changelog.langchain.com/)[LangChain Academy](https://academy.langchain.com/)[Trust Center](https://trust.langchain.com/)
Company
[Home](https://langchain.com/)[About](https://langchain.com/about)[Careers](https://langchain.com/careers)[Blog](https://blog.langchain.com/)
[github](https://github.com/langchain-ai)[x](https://x.com/LangChain)[linkedin](https://www.linkedin.com/company/langchain)[youtube](https://www.youtube.com/@LangChain)

