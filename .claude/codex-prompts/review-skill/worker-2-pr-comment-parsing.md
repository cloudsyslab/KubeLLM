## Summary
- GitHub already gives you most structural data you need for PR review comments through the API: `path`, `line`, multi-line ranges, diff side, reply/thread linkage, and diff hunks. The main best practice is to trust API anchors first and treat body parsing as fallback only.
- GitHub is actively moving away from diff-relative `position` fields toward file-relative `line`/`startLine` coordinates. A parser built today should normalize everything to file path + line/range + side.
- There is no native GitHub field for per-comment severity, category, or actionability. Recent 2025 research and tools treat those as inferred labels, usually via custom taxonomies plus rule-based or LLM-assisted classification.
- The strongest recent evidence for actionability is not sentiment; it is a mix of explicit suggestion structure, intent classification, and retrospective resolution behavior. Readability/bug/maintainability comments are acted on more often than design comments.
- I did not find a current de facto Python or JS library that takes GitHub PR review comments and directly outputs severity/category/intent out of the box. The ecosystem is still retrieval-first, with custom heuristics or LLMs layered on top.

## Detailed Findings

### Finding 1: GitHub PR review comments are a distinct API object, separate from issue and commit comments
- **Claim**: Use GitHub’s PR review comment endpoints as the primary source; do not mix them with issue comments or commit comments.
- **Source**: https://docs.github.com/en/rest/pulls/comments
- **Source Type**: official docs
- **Date**: undated (live docs)
- **Confidence**: high
- **Raw Evidence**: “comments made on a portion of the unified diff”
- **Relevance**: This is the correct starting point for Phase 1 parsing because it tells you which API surface actually carries inline review feedback.

### Finding 2: The REST payload already includes most of the structured anchors you want
- **Claim**: GitHub’s REST review-comment object exposes `path`, `line`, `start_line`, `side`, `diff_hunk`, `in_reply_to_id`, `pull_request_review_id`, and original-line/original-commit fields.
- **Source**: https://docs.github.com/en/rest/pulls/comments
- **Source Type**: official docs
- **Date**: undated (live docs)
- **Confidence**: high
- **Raw Evidence**: Example payload fields include `diff_hunk`, `path`, `line`, `start_line`, `side`, `original_line`, and `in_reply_to_id`.
- **Relevance**: These fields cover file path extraction, line-number extraction, thread/reply linkage, and enough diff context to avoid regex-parsing the body in most cases.

### Finding 3: Diff-relative `position` is being phased out; normalize to file-relative coordinates
- **Claim**: New parsers should normalize comment locations to file-relative `line`/`start_line` and treat `position` as legacy compatibility input only.
- **Source**: https://docs.github.com/en/rest/pulls/comments ; https://docs.github.com/en/graphql/reference/input-objects ; https://docs.github.com/en/enterprise-server%403.17/graphql/overview/breaking-changes
- **Source Type**: official docs
- **Date**: undated (live docs)
- **Confidence**: high
- **Raw Evidence**: REST says “`position` is closing down. Use `line` instead.” GraphQL says “Use the `line` and `startLine` fields instead.”
- **Relevance**: This directly affects your schema design. Store canonical anchors as `path + startLine? + line + side`, not `position`.

### Finding 4: GraphQL threads add resolution and staleness state that are useful for downstream parsing
- **Claim**: If you need conversation state, GraphQL `PullRequestReviewThread` is richer than a flat REST comment list because it exposes thread-level status such as resolved/outdated.
- **Source**: https://docs.github.com/en/graphql/reference/objects
- **Source Type**: official docs
- **Date**: undated (live docs)
- **Confidence**: high
- **Raw Evidence**: The docs list `isOutdated`, `isResolved`, `line`, `startLine`, `path`, and `subjectType` on review threads.
- **Relevance**: This is important if you want to distinguish “open complaint” from “already handled” feedback, or use resolved/outdated as weak labels for intent/actionability.

### Finding 5: GitHub has two strong native actionability signals: `subject_type` and suggestion blocks
- **Claim**: GitHub comments can be file-level or line-level, and explicit suggestion blocks are the cleanest built-in marker of an actionable request.
- **Source**: https://docs.github.com/en/rest/pulls/comments ; https://docs.github.com/articles/commenting-on-a-pull-request ; https://docs.github.com/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request?tool=codespaces
- **Source Type**: official docs
- **Date**: undated (live docs)
- **Confidence**: high
- **Raw Evidence**: REST exposes `subject_type` with values `line` or `file`; UI docs say reviewers can “Make a Suggestion.”
- **Relevance**: For complaint-vs-request parsing, suggestion blocks should be high-confidence actionable; file-level comments should be treated differently from line-anchored defects.

### Finding 6: The tooling landscape is retrieval-first, not semantic-first
- **Claim**: The libraries/tools I found mainly mirror raw API fields or support mining workflows; semantic parsing of severity/category/intent still appears to be custom work.
- **Source**: https://pygithub.readthedocs.io/en/v1.57/github_objects/PullRequestComment.html ; https://arxiv.org/abs/2510.04796
- **Source Type**: community docs + research paper
- **Date**: 2023-01-01 (PyGithub docs copyright year shown) ; 2025-10-06
- **Confidence**: medium
- **Raw Evidence**: PyGithub lists raw fields like `body`, `diff_hunk`, `path`, `position`; RevMine says researchers still write “ad hoc scripts.”
- **Relevance**: Best practice is to separate your parser into two layers: extraction from GitHub APIs first, semantic labeling second. I am explicitly inferring the “no standard semantic parser” point from the sources.

### Finding 7: Diff-context limits are real, and open-source tooling already works around them
- **Claim**: A production parser should model inline review comments separately from broader annotations/comments because GitHub’s review API is diff-context constrained.
- **Source**: https://github.com/reviewdog/reviewdog
- **Source Type**: community / open-source tool
- **Date**: undated GitHub repo page
- **Confidence**: medium
- **Raw Evidence**: reviewdog notes the Review API “don't support posting comments outside diff context” and falls back to check annotations.
- **Relevance**: This matters when reconciling PR feedback sources. Inline review comments, check annotations, and general PR comments should not be merged into one flat parser without source-type metadata.

### Finding 8: Recent NLP work says code review comments are often implicit and ambiguous
- **Claim**: Complaint-vs-actionable classification is not a simple keyword problem; review comments require both code context and conversational interpretation.
- **Source**: https://aclanthology.org/2025.findings-acl.476/
- **Source Type**: research paper
- **Date**: July 2025
- **Confidence**: high
- **Raw Evidence**: Comments are “implicit, ambiguous, and colloquial.”
- **Relevance**: This argues against using only sentiment or regexes for intent classification. Ambiguous comments should probably go through an LLM or context-aware classifier.

### Finding 9: A hybrid rule+LLM intent classifier is one of the clearest recent approaches
- **Claim**: Recent work on reviewer-intent extraction uses predefined templates plus a hybrid rule-based and LLM-based classifier, with measurable performance.
- **Source**: https://arxiv.org/abs/2502.08172
- **Source Type**: research paper (preprint)
- **Date**: 2025-02-12
- **Confidence**: medium
- **Raw Evidence**: “Three categories with eight subcategories” and “79% accuracy in intention extraction.”
- **Relevance**: This is directly useful for distinguishing complaints from actionable requests: use a rule-first taxonomy, then backfill ambiguous cases with an LLM classifier.

### Finding 10: Actionability should be modeled explicitly, and 2025 evidence shows not all comment types are equally actionable
- **Claim**: Recent work supports a two-stage approach: first filter or score comments for validity/actionability, then classify them into issue types.
- **Source**: https://arxiv.org/abs/2502.02757 ; https://arxiv.org/abs/2510.05450
- **Source Type**: research papers (preprints)
- **Date**: 2025-02-04 ; 2025-10-06
- **Confidence**: medium
- **Raw Evidence**: One paper reports “66-85% precision in detecting valid comments”; another reports resolution rates of 43.3% readability, 41.9% bugs, 36.2% maintainability, 28.6% design.
- **Relevance**: For severity/category parsing, actionability is a useful first label. It also suggests a practical category map: `style ~= readability`, `bug = bugs`, and `perf/security/quality ~= maintainability` as an inference layer.

## Patterns Observed
- GitHub is strong on structural metadata and weak on semantics. The APIs tell you where a comment points, not how severe or actionable it is.
- The most stable parser architecture is two-stage: `API extraction -> normalization -> semantic labeling`.
- File path and line number extraction should come from API anchors first. Parsing `body` for file/line references should be fallback only.
- Recent research repeatedly treats actionability, clarity, relevance, and comment type as separate dimensions. That is a better design than one monolithic “severity from text” classifier.
- The closest repeatable taxonomy I found in 2025 was `readability / bugs / maintainability / design / no issue`, not exactly `bug / style / perf`. A practical mapping is:
  `style -> readability`
  `bug -> bugs`
  `perf -> maintainability` when the text is about efficiency, caching, allocation, or algorithmic cost
- The strongest native actionable markers are:
  explicit suggestion blocks
  imperative/request language
  file/line anchoring
  unresolved thread state
  review-level escalation such as “Request changes” on the review itself
- Vendor bias note: GitHub docs are authoritative for wire format but say nothing about semantic parsing quality. The 2025 actionability study includes Atlassian internal data and an Atlassian tool, so its exact rates are not vendor-neutral.

## Contradictions & Debates
- Resolution is not the same as severity. A low-severity style fix may get resolved quickly, while a high-impact design issue may remain open because it needs broader discussion.
- Exact-line modification is a useful retrospective label, but it likely undercounts comments resolved by refactors, follow-up PRs, or off-line agreement.
- Research is moving toward richer utility measures, while many tools in practice still flatten review comments into basic text plus location.

## Gaps
- I did not find any official GitHub severity taxonomy for PR review comments, and I did not find a native per-comment severity field in GitHub’s PR review comment APIs.
- I did not find a current, widely adopted Python or JS library that directly converts GitHub PR review comments into structured `severity/category/intent` labels out of the box.
- I did not find recent GitHub-specific official guidance on extracting additional file/line references from free-form comment bodies such as `foo/bar.py:123` or `L45-L50`.
- I found stronger recent evidence for actionability and intent classification than for direct severity classification from comment text. Severity inference still looks mostly heuristic or custom.

## Source List
- [GitHub REST API: pull request review comments](https://docs.github.com/en/rest/pulls/comments)
- [GitHub GraphQL input objects](https://docs.github.com/en/graphql/reference/input-objects)
- [GitHub GraphQL objects](https://docs.github.com/en/graphql/reference/objects)
- [GitHub GraphQL breaking changes](https://docs.github.com/en/enterprise-server%403.17/graphql/overview/breaking-changes)
- [GitHub Docs: commenting on a pull request](https://docs.github.com/articles/commenting-on-a-pull-request)
- [GitHub Docs: reviewing proposed changes in a pull request](https://docs.github.com/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request?tool=codespaces)
- [PyGithub PullRequestComment docs](https://pygithub.readthedocs.io/en/v1.57/github_objects/PullRequestComment.html)
- [reviewdog](https://github.com/reviewdog/reviewdog)
- [RevMine](https://arxiv.org/abs/2510.04796)
- [CodeReviewQA](https://aclanthology.org/2025.findings-acl.476/)
- [Intention is All You Need](https://arxiv.org/abs/2502.08172)
- [Too Noisy To Learn](https://arxiv.org/abs/2502.02757)
- [What Types of Code Review Comments Do Developers Most Frequently Resolve?](https://arxiv.org/abs/2510.05450)

If you want, I can turn this into a concrete parser design next: a JSON schema, extraction pipeline, and a rule set for `category`, `actionability`, and `severity` with fallback LLM prompts.