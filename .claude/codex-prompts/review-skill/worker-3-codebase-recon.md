## Summary
- Current AI code assistants mostly use hybrid retrieval, not a single technique: they start with local context around the location, then expand with repo search, semantic indexing, or a precomputed code graph.
- For 1-2 level dependency tracing, the most portable primitives are symbol-based navigation APIs: definition, implementation, references, and call hierarchy. These are cheaper and easier to operationalize than full-program analysis.
- Test discovery is framework-specific. The reliable pattern is: read framework config first, use native “related tests” commands when they exist, and fall back to naming/import heuristics plus collection validation.
- Precomputed indices are the recurring scalability pattern. GitHub, Cursor, and Sourcegraph all describe some form of background indexing or code-graph generation to avoid re-parsing the repo at review time.
- Recent research suggests Phase 2 should not stop at structural edges: combining shallow dependency traces with repository history or co-change data is likely more useful for review reconnaissance than AST/LSP alone.

## Detailed Findings

### Finding 1: Repo-Wide Semantic Indexing Is a First-Class Retrieval Strategy
- **Claim**: GitHub Copilot answers repository-context questions by consulting a maintained semantic code-search index, which shifts reconnaissance from ad hoc scanning to reusable repo indexing.
- **Source**: [Indexing repositories for GitHub Copilot Chat](https://docs.github.com/en/enterprise-cloud%40latest/copilot/using-github-copilot/copilot-chat/indexing-repositories-for-copilot-chat) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: Initial indexing for a large repo is described as taking up to 60 seconds, with later updates typically visible within seconds. **Relevance**: For Phase 2, repeated review-comment lookups justify a persistent index instead of fresh repo walks. **Limitation**: Quality depends on index freshness and exclusion policy.

### Finding 2: Assistants Mix Explicit Local Context with Retrieved Repo Context
- **Claim**: GitHub Copilot and Cursor both combine local context near the focal location with workspace-level signals before or alongside repo-scale retrieval.
- **Source**: [GitHub Copilot feature page](https://github.com/features/copilot); [Cursor Security](https://cursor.com/security) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: GitHub says chat uses the active file, selection, and workspace information; Cursor says requests may include recently viewed files and code selected using language-server information. **Relevance**: A review tool should start with the commented line, enclosing symbol, and nearby file context before expanding outward. **Limitation**: Vendors do not document the ranking/fusion logic.

### Finding 3: Cursor Uses Incremental Semantic Indexing with File and Line Metadata
- **Claim**: Cursor’s documented indexing pipeline is concrete: hash the workspace, upload only changed files, chunk and embed files, then retrieve nearest neighbors with file-path and line-range metadata.
- **Source**: [Cursor Security](https://cursor.com/security) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: Cursor describes a Merkle tree over all files, 10-minute mismatch checks, vector storage keyed with obfuscated relative paths, and stored line ranges for each chunk. **Relevance**: This is a strong template for CLI reconnaissance over large repos: incremental indexing plus line-aware retrieval. **Limitation**: Cursor also notes privacy leakage risk from embeddings/path metadata and indexing load failures.

### Finding 4: Cody Uses Layered Retrieval Rather Than One Search Mechanism
- **Claim**: Sourcegraph Cody explicitly combines keyword search, rewritten queries, Sourcegraph Search, and code-graph relations to gather context.
- **Source**: [Cody Context](https://sourcegraph.com/docs/cody/core-concepts/context) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: The documented context sources are keyword search, Sourcegraph Search, and Code Graph, with automatic query rewriting when needed. **Relevance**: For a review-comment tool, hybrid retrieval is the dominant pattern: symbolic lookup first, lexical search second, structural graph expansion alongside both. **Limitation**: Sourcegraph does not publish the weighting or reranking algorithm.

### Finding 5: Search-First Retrieval Is Now Competing with Embeddings-First Designs
- **Claim**: Sourcegraph’s official docs indicate a shift toward search-first retrieval, backed by local keyword indexing and an agentic refinement pass, rather than pure embeddings.
- **Source**: [Cody FAQ](https://sourcegraph.com/docs/cody/faq); [Local Indexing](https://sourcegraph.com/docs/cody/core-concepts/local-indexing); [Agentic context gathering available in Cody](https://sourcegraph.com/changelog/agentic-context-gathering-available-in-cody) | **Source Type**: official docs | **Date**: May 28, 2025 for the changelog; others undated | **Confidence**: high
- **Raw Evidence**: Sourcegraph says Search is the primary context provider, local indexing uses `symf`, and the 2025 rollout added an automatic review/refinement step before prompting. **Relevance**: A practical CLI design can stay cheap and precise by using local search/symbol indices first, then an iterative retrieval loop only when needed. **Limitation**: This tradeoff may miss semantically related code that embedding search finds more easily.

### Finding 6: Position-Based Symbol Navigation Is the Most Portable Entry Point from a Review Comment
- **Claim**: LSP’s `definition`, `typeDefinition`, `implementation`, and `references` requests are the cleanest standards-based way to expand outward from a file+line location.
- **Source**: [Language Server Protocol 3.17 Specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: The spec defines `textDocument/definition`, `textDocument/typeDefinition`, `textDocument/implementation`, and project-wide `textDocument/references`, with `includeDeclaration` as a control. **Relevance**: This directly fits a review comment workflow: resolve enclosing symbol, jump to definition/implementation, then gather 1-hop references. **Limitation**: Completeness varies by language server and language features like reflection or generated code.

### Finding 7: LSP Call Hierarchy Is a Good Fit for 1-2 Level Dependency Tracing
- **Claim**: LSP’s call hierarchy is explicitly a two-step protocol that maps well onto “show me direct callers/callees, then one more hop.”
- **Source**: [Language Server Protocol 3.17 Specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: The spec says call hierarchy is executed in two steps: prepare an item at the position, then resolve incoming or outgoing calls. **Relevance**: This is almost exactly the 1-2 level trace depth you asked for, and it avoids the cost of whole-program call-graph construction at review time. **Limitation**: Dynamic dispatch, reflection, and framework magic can make results incomplete.

### Finding 8: Precomputed Code Graph Data Is the Main Alternative to On-Demand AST/LSP Traversal
- **Claim**: Sourcegraph’s code-graph and auto-indexing docs describe a precomputed symbol graph containing semantic elements like definitions and references, generated either in-platform or in CI.
- **Source**: [Code Graph](https://sourcegraph.com/docs/cody/core-concepts/code-graph); [Auto-indexing](https://sourcegraph.com/docs/code_navigation/explanations/auto_indexing) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: Code graph data includes definitions, references, symbols, and doc comments; auto-indexing can trigger dependency index jobs for better cross-repo navigation. **Relevance**: For Phase 2, this suggests a strong architecture: use prebuilt code-intel when available, and fall back to LSP or parsing only when it is not. **Limitation**: It requires language-specific indexers, supported ecosystems, and background infrastructure.

### Finding 9: Jest Offers Both Discovery Heuristics and a Native Source-to-Test Mapping Primitive
- **Claim**: Jest exposes two useful patterns: config-driven file discovery via `testMatch`/`testRegex`, and a first-party `--findRelatedTests` command that maps source files to covering tests.
- **Source**: [Jest Configuration](https://jestjs.io/docs/configuration); [Jest CLI](https://jestjs.io/docs/cli) | **Source Type**: official docs | **Date**: June 10, 2025 for CLI; configuration page undated | **Confidence**: high
- **Raw Evidence**: Defaults include `__tests__` and `.test`/`.spec` patterns; `--findRelatedTests` is documented as running the tests that cover a provided list of source files. **Relevance**: For JS/TS code review, a tool should inspect Jest config first, then prefer `--findRelatedTests` over filename guessing. **Limitation**: `testRegex` matches absolute paths, so directory names can produce false positives if you rely on heuristics alone.

### Finding 10: Pytest Discovery Is Highly Configurable but Not Source-to-Test Aware
- **Claim**: Pytest’s built-in model is filesystem and naming based: start at `testpaths` or cwd, recurse unless excluded, discover `test_*.py` and `*_test.py`, and let users inspect or customize collection.
- **Source**: [Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html); [Changing standard (Python) test discovery](https://docs.pytest.org/en/stable/example/pythoncollection.html) | **Source Type**: official docs | **Date**: undated | **Confidence**: high
- **Raw Evidence**: The docs describe discovery from `testpaths`/cwd, `norecursedirs`, `python_files`, `--ignore`, `collect_ignore`, and `--collect-only`. **Relevance**: In Python, associated-test discovery usually needs a layered heuristic: config inspection, file-name conventions, import-based matching, and collection verification. **Limitation**: Pytest has no first-party equivalent of Jest’s `--findRelatedTests` for arbitrary source files.

### Finding 11: Recent Research Favors Hybrid Change Impact Analysis for Review Reconnaissance
- **Claim**: The 2024 CHID paper argues that PR-level change impact analysis is strongest when it combines repository history with call-graph dependency analysis, not when it relies on structure alone.
- **Source**: [Enhanced code reviews using pull request based change impact analysis](https://link.springer.com/article/10.1007/s10664-024-10600-2) | **Source Type**: research paper | **Date**: 2024 | **Confidence**: medium
- **Raw Evidence**: The paper combines MSR with call-graph dependency analysis and uses a project-wide function call graph to identify potentially impacted functions. **Relevance**: For Phase 2, this is the clearest research-backed extension beyond LSP: add co-change/history signals after shallow structural tracing. **Limitation**: It is a research prototype and heavier than a lightweight 1-2 hop CLI workflow.

## Patterns Observed
- Start from a precise anchor: file, line, and ideally enclosing symbol. Every strong approach assumes a concrete location first.
- Expand context in rings: local window around the line, same-symbol navigation, 1-hop references/calls, then repo-wide retrieval only if needed.
- Prefer precomputed indices when available: semantic repo index, local keyword index, or code graph. Current assistants optimize for reuse, not repeated parsing.
- Use graph primitives for shallow dependency tracing: definition, implementation, references, incoming calls, outgoing calls. Full call graphs are usually overkill for the first pass.
- Treat tests as framework-specific reconnaissance, not generic search. Read config, use native related-test commands when they exist, then validate candidates with collection/listing commands.
- Raw AST traversal is mostly an implementation substrate, not the public interface. In product docs, AST shows up indirectly through language servers, code-intel indexers, or research tools.

## Contradictions & Debates
- Embeddings-first versus search-first: Cursor documents a vector-index pipeline, while Sourcegraph explicitly says Search became the primary context provider after embeddings were removed.
- Automatic retrieval versus explicit control: all vendors auto-gather context, but they also document ignore/exclusion controls because privacy and predictability remain open problems.
- Structural relevance versus behavioral relevance: symbol graphs find nearby code, but impacted tests are often better selected via coverage or history than via code navigation alone.
- Server-side indexing versus local indexing: Cursor’s design is server/vector-store heavy, while Cody also documents a local keyword index. The tradeoff is latency and privacy versus centralized capability.

## Gaps
- I did not find an official vendor document that fully explains snippet ranking, fusion, or stopping criteria for context retrieval.
- I did not find a cross-language, first-party algorithm from major assistants for mapping arbitrary review-comment locations to associated test files.
- Pytest exposes excellent discovery customization, but not first-party source-to-test tracing; that gap has to be filled by heuristics, coverage, or history.
- Most assistant documentation is IDE or web centered. The CLI-applicable patterns are inferential but still usable: LSP, search, code graphs, config inspection, and framework-native test commands.

## Source List
- GitHub Docs: [Indexing repositories for GitHub Copilot Chat](https://docs.github.com/en/enterprise-cloud%40latest/copilot/using-github-copilot/copilot-chat/indexing-repositories-for-copilot-chat)
- GitHub: [GitHub Copilot feature page](https://github.com/features/copilot)
- Cursor: [Security](https://cursor.com/security)
- Sourcegraph Docs: [Cody Context](https://sourcegraph.com/docs/cody/core-concepts/context), [Cody FAQ](https://sourcegraph.com/docs/cody/faq), [Local Indexing](https://sourcegraph.com/docs/cody/core-concepts/local-indexing)
- Sourcegraph Changelog: [Agentic context gathering available in Cody](https://sourcegraph.com/changelog/agentic-context-gathering-available-in-cody)
- Microsoft: [Language Server Protocol 3.17 Specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
- Sourcegraph Docs: [Code Graph](https://sourcegraph.com/docs/cody/core-concepts/code-graph), [Auto-indexing](https://sourcegraph.com/docs/code_navigation/explanations/auto_indexing)
- Jest Docs: [Configuration](https://jestjs.io/docs/configuration), [CLI](https://jestjs.io/docs/cli)
- Pytest Docs: [Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html), [Changing standard (Python) test discovery](https://docs.pytest.org/en/stable/example/pythoncollection.html)
- Springer: [Enhanced code reviews using pull request based change impact analysis](https://link.springer.com/article/10.1007/s10664-024-10600-2)

If you want, the next useful step is to turn these patterns into a concrete Phase 2 reconnaissance algorithm: input schema, retrieval order, stop conditions, and fallback heuristics for JS/TS and Python.