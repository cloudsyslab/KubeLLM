# Local lab consolidation smoke

One `wrong_port` smoke per technique on the selected lane after the cleanup
branch was pushed:

| Technique | Runner status | Ground Truth | Verification |
|---|---|---|---|
| `allStepsAtOnce` | PASS | passed | true |
| `stepByStep` | PASS | passed | true |
| `singleAgent` | PASS | passed | false |
| `knowledgeAgentOnly` | PASS | passed | true |

The single-agent verifier disagreement is retained as recorded. It does not
override Ground Truth. `knowledgeAgentOnly` planned, attempted, and completed
five deterministic actions. These four smoke observations establish that each
path ran through setup, execution, verification, Ground Truth, and teardown;
they are too small to support comparative performance claims.

The exports retain allowlisted outcomes, metrics, effective model identifiers,
and source provenance. Private raw run artifacts remain in ignored `.local/`.
