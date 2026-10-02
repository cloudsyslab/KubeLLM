# GPT-5 mini KAO vs SingleAgent benchmark reports

This report pack records the matched 27-case, five-repetition comparison. The original KAO queue stopped at 126/135; a separate nine-case recovery completed the remaining planned slots on 2026-10-02. The final comparison combines both KAO runs while preserving each run's own summary.

- [Completed matched comparison](comparison_recovery_addendum.md)
- [Snapshot before KAO recovery](comparison_summary.md)
- [Original KAO queue: 126 attempts, 9 unstarted](runs/kao-original-queue.md)
- [KAO recovery: 9 attempts](runs/kao-recovery-9cases.md)
- [SingleAgent: 135 attempts](runs/single-agent.md)
- [Structured outcome data pack](../../../data/exploratory/kao-singleagent-gpt5mini-2026-10/README.md)

Only Markdown summaries are included here. Raw case artifacts, run configuration, and logs remain in the ignored `.local/test_runs/` directory on the benchmark checkout. Both techniques used GPT-5 mini model overrides, but their active stages differ: KAO runs separate Knowledge and Verification agents; SingleAgent uses one combined diagnosis/action agent and omits independent Verification.
