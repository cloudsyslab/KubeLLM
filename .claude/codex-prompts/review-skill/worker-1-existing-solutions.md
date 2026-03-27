## Summary
- The 5-phase model is strongly validated by CodeRabbit and Qodo, partially validated by GitHub Copilot, only partially visible in Sourcery’s public PR-review docs, and weakest for Amazon CodeGuru Reviewer.
- Across tools, the dominant workflow is not "review comment straight to fix." It is usually "PR trigger -> context gathering -> diagnosis -> human-visible suggestion -> optional fix action."
- Phase 2, codebase reconnaissance, is the clearest differentiator: GitHub Copilot uses repo instructions/memory, CodeRabbit uses full-repo and issue context, Qodo uses ticket context and RAG, and Sourcery uses review rules/style guides.
- Phase 5, verification, is the least consistently documented. CodeRabbit publicly documents setup/build verification; Qodo documents self-review, tracking, and approvals; Copilot and CodeGuru mostly leave validation to humans.
- Most usable evidence is vendor-authored docs/changelogs. That makes workflow mechanics reasonably credible, but internal parsing, prompt construction, and model orchestration remain opaque.

## Detailed Findings

### Finding 1: GitHub Copilot can auto-review at multiple PR lifecycle events
- **Claim**: GitHub Copilot can automatically review on PR open, draft-to-open transition, and optionally on every new push; otherwise re-review is manual.
- **Source**: https://docs.github.com/en/copilot/concepts/agents/code-review
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs list automatic triggers for open PRs, first draft-to-open transition, and optional review on each new push; they also note manual re-review if push-based review is not enabled.
- **Relevance**: This supports phases 1-2 by showing repeated parsing/recon on new PR states and later commits.

### Finding 2: GitHub Copilot turns review comments into directly applicable patch suggestions
- **Claim**: GitHub Copilot review outputs can include commit-ready suggestions in the PR UI, not just prose comments.
- **Source**: https://docs.github.com/en/get-started/learning-to-code/getting-feedback-on-your-code-from-github-copilot
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: GitHub’s tutorial tells users to wait for Copilot’s review, then click `Commit suggestion` under the proposed fix that changes `.classes` to `.classList`.
- **Relevance**: This is direct evidence for phase 4, fix generation, though verification is still mainly human-driven.

### Finding 3: GitHub Copilot explicitly improves reviews with persistent repository context
- **Claim**: GitHub positions repository instructions and memory as inputs that make code reviews more accurate and useful.
- **Source**: https://docs.github.com/en/copilot/concepts/agents/code-review | https://github.blog/changelog/2025-06-13-copilot-code-review-customization-for-all/
- **Source Type**: official docs
- **Date**: undated / June 13, 2025
- **Confidence**: high
- **Raw Evidence**: Docs say review quality improves when Copilot knows repository tools and standards; the June 13, 2025 changelog says `copilot-instructions.md` applies to code review automatically.
- **Relevance**: This is strong support for phase 2, codebase reconnaissance, because Copilot is explicitly conditioned on persistent repo knowledge rather than the diff alone.

### Finding 4: CodeRabbit’s default PR review flow is automatic, incremental, and context-heavy
- **Claim**: CodeRabbit does a full review on new PRs, incremental review on later commits, and uses issue plus repository context to shape findings.
- **Source**: https://docs.coderabbit.ai/overview/pull-request-review
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The docs describe full analysis on new PRs, incremental review on new commits, linked issue context from GitHub/Jira/Linear, and suggestions based on the full repository rather than only changed lines.
- **Relevance**: This cleanly supports phases 1-3: trigger, reconnaissance, and diagnosis.

### Finding 5: CodeRabbit Autofix is the clearest public example of the full 5-phase pipeline
- **Claim**: CodeRabbit publicly documents an end-to-end workflow from unresolved review threads to generated fixes, verification, and delivery.
- **Source**: https://docs.coderabbit.ai/finishing-touches/autofix
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: The documented steps are: trigger Autofix, scan unresolved CodeRabbit review threads, gather fix instructions from `Prompt for AI Agents` blocks, generate fixes, run repository setup/build verification, then push a commit or open a stacked PR.
- **Relevance**: This is almost a direct implementation of phases 1-5 as you described them.

### Finding 6: Sourcery’s public PR-review docs emphasize review, conversation, and re-review, not direct code application
- **Claim**: In the PR-review docs consulted, Sourcery documents review/re-review and conversational workflows, but not an official one-click "apply fix from review comment" flow.
- **Source**: https://docs.sourcery.ai/Code-Review/Code-Reviews-on-Pull-Requests/Interacting-with-Sourcery/
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: medium
- **Raw Evidence**: The documented commands are `@sourcery-ai review`, `summary`, `guide`, `resolve`, `dismiss`, and reply-based clarification; that page does not describe a commit/apply action from PR comments.
- **Relevance**: This supports phases 1-3 well, but phases 4-5 are under-documented in Sourcery’s core PR-review materials.

### Finding 7: Sourcery’s adjacent 2025 incident-fixing agent follows diagnosis-before-fix-before-PR
- **Claim**: Sourcery’s production-issue workflow explicitly sequences investigation, root-cause analysis, proposed fix, and PR creation.
- **Source**: https://sourcery.ai/blog/production-issues-beta
- **Source Type**: reputable blog
- **Date**: April 10, 2025
- **Confidence**: medium
- **Raw Evidence**: Vendor-authored blog states that Sourcery can investigate Sentry issues, find the root cause, propose a fix, and generate the PR, including analysis of stack traces and candidate commits.
- **Relevance**: Although adjacent to PR review rather than inside it, this strongly supports your phase ordering, especially phases 2-3 before phase 4.

### Finding 8: Qodo deliberately separates reviewer diagnosis from author repair
- **Claim**: Qodo treats `/review` as reviewer-facing analysis and `/improve` as author-facing actionable repair suggestions.
- **Source**: https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/tools/review | https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/usage-guide/automations_and_usage
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Qodo’s review docs say the reviewer benefits from `/review`, while PR authors may prefer `/improve` because it provides actionable code suggestions; the automation docs show both tools can be run automatically on PR open.
- **Relevance**: This is strong evidence for a multi-step pipeline where diagnosis and fix generation are separate phases, not one prompt.

### Finding 9: Qodo broadens reconnaissance with ticket context and RAG
- **Claim**: Qodo enriches review using ticket data and, when enabled, retrieval over repository content beyond the current diff.
- **Source**: https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/fetching_ticket_context | https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/rag_context_enrichment
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Ticket-context docs list title, description, acceptance criteria, subtasks, labels, and screenshots as fetched inputs; RAG docs say `/review` and `/implement` can use repository references found through semantic retrieval.
- **Relevance**: This is direct support for phase 2, codebase reconnaissance, and shows why a diff-only fix pipeline is probably too weak.

### Finding 10: Qodo adds a filtering and governance layer before and after fixes
- **Claim**: Qodo does not just generate suggestions; it re-ranks them, lets users turn them into committable comments, tracks implementation, and can require self-review.
- **Source**: https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/tools/index/improve | https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/self_reflection
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: Improve docs describe `Apply / Chat`, direct and indirect implementation tracking, and optional self-review/approval; self-reflection docs describe scoring, re-ranking, and filtering suggestions before presentation.
- **Relevance**: This maps to phases 3-5: diagnosis refinement, fix generation, and post-fix validation/governance.

### Finding 11: Amazon CodeGuru Reviewer remains recommendation-centric, and its current relevance is reduced by its late-2025 availability change
- **Claim**: AWS currently documents CodeGuru Reviewer as generating PR recommendations and resolution guidance, not agentically applying fixes; as of November 7, 2025, new repository associations are no longer allowed.
- **Source**: https://aws.amazon.com/codeguru/reviewer/faqs/ | https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/recommendations.html | https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/codeguru-reviewer-availability-change.html
- **Source Type**: official docs
- **Date**: undated
- **Confidence**: high
- **Raw Evidence**: AWS FAQ says CodeGuru provides intelligent recommendations directly in pull requests; recommendation docs describe various fix types plus feedback on pull-request comments; the availability-change doc says no new associations after November 7, 2025.
- **Relevance**: This supports phases 1-3, but gives weak evidence for phases 4-5 and limits CodeGuru’s usefulness as a current benchmark for agentic PR fixing.

## Patterns Observed
- Automatic PR-open and PR-update triggers are standard. Manual comment commands are the fallback when tools want a human to explicitly escalate from review into action.
- The more agentic tools separate diagnosis from repair instead of collapsing them into one step. Qodo does this most explicitly with `/review` versus `/improve`; CodeRabbit does it with review versus Autofix.
- Repository grounding is becoming the norm. Ticket links, linked issues, repo instructions, memory, full-repo context, and RAG all appear as ways to reduce shallow diff-only feedback.
- Human control remains a safety valve even in the more aggressive tools. Copilot asks users to commit suggestions, Qodo adds self-review and approval mechanics, and CodeRabbit still expects users to inspect the commit or stacked PR.
- Verification is public and explicit only in a minority of cases. CodeRabbit is the clearest example; elsewhere verification is implied, human-mediated, or undocumented.

## Contradictions & Debates
- Tools disagree on how far to automate phase 4. Copilot and CodeGuru stay mostly suggestion-centric, while CodeRabbit and Qodo are comfortable creating commits or PR-ready changes.
- Tools also disagree on how explicit to be about internals. Qodo and CodeRabbit publish more workflow detail about repair actions; Copilot and Sourcery expose UX workflows but much less about fix-generation mechanics.
- Vendor positioning often implies that better context automatically means better fixes, but public docs rarely provide independent evidence about false positives, failed autofixes, or verification pass rates.

## Gaps
- I could not find credible public documentation that explains the internal comment-parsing architecture for any of these vendors, such as exact prompt schemas, AST pipelines, or review-thread extraction logic.
- I could not find 2024-2025 official Sourcery PR-review docs showing a one-click auto-fix-from-review-comment workflow comparable to CodeRabbit Autofix or Qodo’s committable suggestions.
- I could not find public, detailed verification workflows for GitHub Copilot or Amazon CodeGuru Reviewer that match CodeRabbit’s documented setup/build verification step.
- I could not find enough recent, credible public material on Amazon CodeGuru Reviewer’s evolving fix workflow because the service moved into a no-new-associations state on November 7, 2025.
- I found strong vendor-authored descriptions of workflow steps, but not strong independent evaluations comparing how reliably these tools complete phases 3-5 in practice.

## Source List
1. https://docs.github.com/en/copilot/concepts/agents/code-review
2. https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review
3. https://docs.github.com/en/get-started/learning-to-code/getting-feedback-on-your-code-from-github-copilot
4. https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/configure-automatic-review
5. https://github.blog/changelog/2025-02-26-code-review-in-github-copilot-is-now-in-public-preview/
6. https://github.blog/changelog/2025-06-13-copilot-code-review-customization-for-all/
7. https://docs.coderabbit.ai/overview/pull-request-review
8. https://docs.coderabbit.ai/guides/commands
9. https://docs.coderabbit.ai/finishing-touches/autofix
10. https://docs.sourcery.ai/Code-Review/Code-Reviews-on-Pull-Requests/Overview/
11. https://docs.sourcery.ai/Code-Review/Code-Reviews-on-Pull-Requests/Interacting-with-Sourcery/
12. https://docs.sourcery.ai/Code-Review/Teaching-Sourcery/
13. https://sourcery.ai/blog/production-issues-beta
14. https://sourcery.ai/changelog/2024-07-11
15. https://sourcery.ai/changelog/2024-11-06
16. https://sourcery.ai/changelog/2025-01-08
17. https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/tools/review
18. https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/tools/index/improve
19. https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/usage-guide/automations_and_usage
20. https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/fetching_ticket_context
21. https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/rag_context_enrichment
22. https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/self_reflection
23. https://aws.amazon.com/codeguru/reviewer/
24. https://aws.amazon.com/codeguru/reviewer/faqs/
25. https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/recommendations.html
26. https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/codeguru-reviewer-availability-change.html
27. https://aws.amazon.com/blogs/devops/inconsistency-detection-in-amazon-codeguru-reviewer/
28. https://aws.amazon.com/blogs/devops/tightening-application-security-with-amazon-codeguru/