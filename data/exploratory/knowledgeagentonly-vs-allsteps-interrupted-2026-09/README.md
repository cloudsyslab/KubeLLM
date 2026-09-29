# Interrupted KnowledgeAgentOnly pilot (September 2026)

This is a gated archive of the first 27-case, two-technique comparison. It is
not a complete benchmark: the `allStepsAtOnce` control finished one suite, but
the `knowledgeAgentOnly` suite was interrupted after 26 of 27 stage artifacts.
The latter produced no runner summaries or aggregate, so the two arms do not
have comparable complete-run cost or outcome records. The default analyzer
excludes both archived arms because their configs are named
`run_config.archived.json`.

The [status record](pilot_status.json) preserves the planned sample, actual
artifact coverage, stage counts, and the known integrity diagnosis. The
allowlisted arm archives keep control summaries and Knowledge stage categories
only. Raw logs, prompts, generated plans/commands, and personal lane details
remain in ignored `.local/` artifacts and are not included here.

The pilot found no evidence that deterministic parsing changed the valid plan:
the 25 schema-valid raw plans matched their parsed representation, and all 98
attempted command strings matched the Knowledge instructions. This establishes
parser fidelity for those observed attempts, not that every plan is executable
or that the architecture is better overall. In particular, 12 of the 26
recorded executions had an action failure, although 7 of those cases still
passed Ground Truth.

The interrupted `liveness_probe_wrong_path` case edited its fixture, then hit
an immutable Pod-field error during apply. Its manifest teardown timed out;
because baseline restoration was sequenced after that command, the old runner
left the shared fixture edited. The selected lane was checked afterward and
had no residual target resources; the fixture was manually restored. This
archive therefore records an architecture/runner integrity failure, not a
KnowledgeAgentOnly benchmark result. The corrective runner now restores the
fixture in `finally`, records per-case results incrementally, and stops serial
work/repeats on cleanup failure. These fixes were validated before restarting
the full comparison.
