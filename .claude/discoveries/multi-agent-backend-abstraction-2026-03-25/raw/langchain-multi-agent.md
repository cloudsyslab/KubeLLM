[Skip to main content](https://docs.langchain.com/oss/python/langchain/multi-agent/index#content-area)
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
Multi-agent
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
  * [Why multi-agent?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#why-multi-agent)
  * [Patterns](https://docs.langchain.com/oss/python/langchain/multi-agent/index#patterns)
  * [Choosing a pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/index#choosing-a-pattern)
  * [Visual overview](https://docs.langchain.com/oss/python/langchain/multi-agent/index#visual-overview)
  * [Performance comparison](https://docs.langchain.com/oss/python/langchain/multi-agent/index#performance-comparison)
  * [One-shot request](https://docs.langchain.com/oss/python/langchain/multi-agent/index#one-shot-request)
  * [Repeat request](https://docs.langchain.com/oss/python/langchain/multi-agent/index#repeat-request)
  * [Multi-domain](https://docs.langchain.com/oss/python/langchain/multi-agent/index#multi-domain)
  * [Summary](https://docs.langchain.com/oss/python/langchain/multi-agent/index#summary)


[Advanced usage](https://docs.langchain.com/oss/python/langchain/guardrails)
[Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent/index)
# Multi-agent
Copy page
Copy page
Multi-agent systems coordinate specialized components to tackle complex workflows. However, not every complex task requires this approach—a single agent with the right (sometimes dynamic) tools and prompt can often achieve similar results.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#why-multi-agent)
Why multi-agent?
When developers say they need “multi-agent,” they’re usually looking for one or more of these capabilities:
  * **Context management** : Provide specialized knowledge without overwhelming the model’s context window. If context were infinite and latency zero, you could dump all knowledge into a single prompt—but since it’s not, you need patterns to selectively surface relevant information.
  * **Distributed development** : Allow different teams to develop and maintain capabilities independently, composing them into a larger system with clear boundaries.
  * **Parallelization** : Spawn specialized workers for subtasks and execute them concurrently for faster results.

Multi-agent patterns are particularly valuable when a single agent has too many [tools](https://docs.langchain.com/oss/python/langchain/tools) and makes poor decisions about which to use, when tasks require specialized knowledge with extensive context (long prompts and domain-specific tools), or when you need to enforce sequential constraints that unlock capabilities only after certain conditions are met.
At the center of multi-agent design is **[context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering)** —deciding what information each agent sees. The quality of your system depends on ensuring each agent has access to the right data for its task.
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#patterns)
Patterns
Here are the main patterns for building multi-agent systems, each suited to different use cases:  
| Pattern  | How it works  |  
| --- | --- |  
| [**Subagents**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | A main agent coordinates subagents as tools. All routing passes through the main agent, which decides when and how to invoke each subagent.  |  
| [**Handoffs**](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | Behavior changes dynamically based on state. Tool calls update a state variable that triggers routing or configuration changes, switching agents or adjusting the current agent’s tools and prompt.  |  
| [**Skills**](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | Specialized prompts and knowledge loaded on-demand. A single agent stays in control while loading context from skills as needed.  |  
| [**Router**](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  | A routing step classifies input and directs it to one or more specialized agents. Results are synthesized into a combined response.  |  
| [**Custom workflow**](https://docs.langchain.com/oss/python/langchain/multi-agent/custom-workflow)  | Build bespoke execution flows with [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview), mixing deterministic logic and agentic behavior. Embed other patterns as nodes in your workflow.  |  
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#choosing-a-pattern)
Choosing a pattern
Use this table to match your requirements to the right pattern:  
| Pattern  | Distributed development  | Parallelization  | Multi-hop  | Direct user interaction  |  
| --- | --- | --- | --- | --- |  
| [**Subagents**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | ?????  | ?????  | ?????  | ?  |  
| [**Handoffs**](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | -  | -  | ?????  | ?????  |  
| [**Skills**](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | ?????  | ???  | ?????  | ?????  |  
| [**Router**](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  | ???  | ?????  | -  | ???  |  
  * **Distributed development** : Can different teams maintain components independently?
  * **Parallelization** : Can multiple agents execute concurrently?
  * **Multi-hop** : Does the pattern support calling multiple subagents in series?
  * **Direct user interaction** : Can subagents converse directly with the user?


You can mix patterns! For example, a **subagents** architecture can invoke tools that invoke custom workflows or router agents. Subagents can even use the **skills** pattern to load context on-demand. The possibilities are endless!
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#visual-overview)
Visual overview
  * Subagents
  * Handoffs
  * Skills
  * Router


A main agent coordinates subagents as tools. All routing passes through the main agent.
![Subagents pattern: main agent coordinates subagents as tools](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=f924dde09057820b08f0c577e08fcfe7)
Agents transfer control to each other via tool calls. Each agent can hand off to others or respond directly to the user.
![Handoffs pattern: agents transfer control via tool calls](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=57d935e6a8efab4afb3faa385113f4dd)
A single agent loads specialized prompts and knowledge on-demand while staying in control.
![Skills pattern: single agent loads specialized context on-demand](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=119131d1f19be1f0c6fb1e30f080b427)
A routing step classifies input and directs it to specialized agents. Results are synthesized.
![Router pattern: routing step classifies input to specialized agents](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=ceab32819240ba87f3a132357cc78b09)
## 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#performance-comparison)
Performance comparison
Different patterns have different performance characteristics. Understanding these tradeoffs helps you choose the right pattern for your latency and cost requirements. **Key metrics:**
  * **Model calls** : Number of LLM invocations. More calls = higher latency (especially if sequential) and higher per-request API costs.
  * **Tokens processed** : Total [context window](https://docs.langchain.com/oss/python/langchain/context-engineering) usage across all calls. More tokens = higher processing costs and potential context limits.


### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#one-shot-request)
One-shot request
> **User:** “Buy coffee”
A specialized coffee agent/skill can call a `buy_coffee` tool.  
| Pattern  | Model calls  | Best fit  |  
| --- | --- | --- |  
| [**Subagents**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | 4  |   |  
| [**Handoffs**](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | 3  | ?  |  
| [**Skills**](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | 3  | ?  |  
| [**Router**](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  | 3  | ?  |  
  * Subagents
  * Handoffs
  * Skills
  * Router


**4 model calls:**
![Subagents one-shot: 4 model calls for buy coffee request](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=bd4eeef41d8870bfa887dd0aa97d0b79)
**3 model calls:**
![Handoffs one-shot: 3 model calls for buy coffee request](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=42ec50519ff04f034050dc77cf869907)
**3 model calls:**
![Skills one-shot: 3 model calls for buy coffee request](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=c8dbf69ed4509e30e5280e7e8a391dab)
**3 model calls:**
![Router one-shot: 3 model calls for buy coffee request](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=be5707931d3e520e3ae66af544f2cf2f)
**Key insight:** Handoffs, Skills, and Router are most efficient for single tasks (3 calls each). Subagents adds one extra call because results flow back through the main agent—this overhead provides centralized control.
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#repeat-request)
Repeat request
> **Turn 1:** “Buy coffee” **Turn 2:** “Buy coffee again”
The user repeats the same request in the same conversation.  
| Pattern  | Turn 2 calls  | Total (both turns)  | Best fit  |  
| --- | --- | --- | --- |  
| [**Subagents**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | 4  | 8  |   |  
| [**Handoffs**](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | 2  | 5  | ?  |  
| [**Skills**](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | 2  | 5  | ?  |  
| [**Router**](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  | 3  | 6  |   |  
  * Subagents
  * Handoffs
  * Skills
  * Router


**4 calls again ? 8 total**
  * Subagents are **stateless by design** —each invocation follows the same flow
  * The main agent maintains conversation context, but subagents start fresh each time
  * This provides strong context isolation but repeats the full flow


**2 calls ? 5 total**
  * The coffee agent is **still active** from turn 1 (state persists)
  * No handoff needed—agent directly calls `buy_coffee` tool (call 1)
  * Agent responds to user (call 2)
  * **Saves 1 call by skipping the handoff**


**2 calls ? 5 total**
  * The skill context is **already loaded** in conversation history
  * No need to reload—agent directly calls `buy_coffee` tool (call 1)
  * Agent responds to user (call 2)
  * **Saves 1 call by reusing loaded skill**


**3 calls again ? 6 total**
  * Routers are **stateless** —each request requires an LLM routing call
  * Turn 2: Router LLM call (1) ? Milk agent calls buy_coffee (2) ? Milk agent responds (3)
  * Can be optimized by wrapping as a tool in a stateful agent


**Key insight:** Stateful patterns (Handoffs, Skills) save 40-50% of calls on repeat requests. Subagents maintain consistent cost per request—this stateless design provides strong context isolation but at the cost of repeated model calls.
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#multi-domain)
Multi-domain
> **User:** “Compare Python, JavaScript, and Rust for web development”
Each language agent/skill contains ~2000 tokens of documentation. All patterns can make parallel tool calls.  
| Pattern  | Model calls  | Total tokens  | Best fit  |  
| --- | --- | --- | --- |  
| [**Subagents**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | 5  | ~9K  | ?  |  
| [**Handoffs**](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | 7+  | ~14K+  |   |  
| [**Skills**](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | 3  | ~15K  |   |  
| [**Router**](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  | 5  | ~9K  | ?  |  
  * Subagents
  * Handoffs
  * Skills
  * Router


**5 calls, ~9K tokens**
![Subagents multi-domain: 5 calls with parallel execution](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=9cc5d2d46bfa98b7ceeacdc473512c94)
Each subagent works in **isolation** with only its relevant context. Total: **9K tokens**.
**7+ calls, ~14K+ tokens**
![Handoffs multi-domain: 7+ sequential calls](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=7ede44260515e49ff1d0217f0030d66d)
Handoffs executes **sequentially** —can’t research all three languages in parallel. Growing conversation history adds overhead. Total: **~14K+ tokens**.
**3 calls, ~15K tokens**
![Skills multi-domain: 3 calls with accumulated context](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=2162584b6076aee83396760bc6de4cf4)
After loading, **every subsequent call processes all 6K tokens of skill documentation**. Subagents processes 67% fewer tokens overall due to context isolation. Total: **15K tokens**.
**5 calls, ~9K tokens**
![Router multi-domain: 5 calls with parallel execution](https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=ef11573bc65e5a2996d671bb3030ca6b)
Router uses an **LLM for routing** , then invokes agents in parallel. Similar to Subagents but with explicit routing step. Total: **9K tokens**.
**Key insight:** For multi-domain tasks, patterns with parallel execution (Subagents, Router) are most efficient. Skills has fewer calls but high token usage due to context accumulation. Handoffs is inefficient here—it must execute sequentially and can’t leverage parallel tool calling for consulting multiple domains simultaneously.
### 
[?](https://docs.langchain.com/oss/python/langchain/multi-agent/index#summary)
Summary
Here’s how patterns compare across all three scenarios:  
| Pattern  | One-shot  | Repeat request  | Multi-domain  |  
| --- | --- | --- | --- |  
| [**Subagents**](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | 4 calls  | 8 calls (4+4)  | 5 calls, 9K tokens  |  
| [**Handoffs**](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | 3 calls  | 5 calls (3+2)  | 7+ calls, 14K+ tokens  |  
| [**Skills**](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | 3 calls  | 5 calls (3+2)  | 3 calls, 15K tokens  |  
| [**Router**](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  | 3 calls  | 6 calls (3+3)  | 5 calls, 9K tokens  |  
**Choosing a pattern:**  
| Optimize for  | [Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)  | [Handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  | [Skills](https://docs.langchain.com/oss/python/langchain/multi-agent/skills)  | [Router](https://docs.langchain.com/oss/python/langchain/multi-agent/router)  |  
| --- | --- | --- | --- | --- |  
| Single requests  |   | ?  | ?  | ?  |  
| Repeat requests  |   | ?  | ?  |   |  
| Parallel execution  | ?  |   |   | ?  |  
| Large-context domains  | ?  |   |   | ?  |  
| Simple, focused tasks  |   |   | ?  |   |  
* * *
[Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/multi-agent/index.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
[Connect these docs](https://docs.langchain.com/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
Was this page helpful?
YesNo
[ Human-in-the-loop Previous ](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)[ Subagents Next ](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)
Ctrl+I
[Docs by LangChain home page![light logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-dark-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=5babf1a1962208fd7eed942fa2432ecb)![dark logo](https://mintcdn.com/langchain-5e9cc07a/nQm-sjd_MByLhgeW/images/brand/langchain-docs-light-blue.png?fit=max&auto=format&n=nQm-sjd_MByLhgeW&q=85&s=0bcd2a1f2599ed228bcedf0f535b45b1)](https://docs.langchain.com/)
[github](https://github.com/langchain-ai)[x](https://x.com/LangChain)[linkedin](https://www.linkedin.com/company/langchain)[youtube](https://www.youtube.com/@LangChain)
Resources
[Forum](https://forum.langchain.com/)[Changelog](https://changelog.langchain.com/)[LangChain Academy](https://academy.langchain.com/)[Trust Center](https://trust.langchain.com/)
Company
[Home](https://langchain.com/)[About](https://langchain.com/about)[Careers](https://langchain.com/careers)[Blog](https://blog.langchain.com/)
[github](https://github.com/langchain-ai)[x](https://x.com/LangChain)[linkedin](https://www.linkedin.com/company/langchain)[youtube](https://www.youtube.com/@LangChain)

