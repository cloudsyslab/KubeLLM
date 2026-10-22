# Deep Research specialist route

Select this route only when the user explicitly asks for Deep Research, invokes `$deep-research`, or chooses Deep Research in the product.

1. Load the complete runtime-managed `$deep-research` skill before acting.
2. Let that skill own research breadth, evidence standards, citations, and completion criteria.
3. Do not silently upgrade an ordinary research request into Deep Research or emulate the branded workflow when the managed skill is unavailable.
4. For a multi-lane request, finish the Deep Research workflow first, then return its findings and source ledger to the discovery router for reconciliation.

This file is a routing adapter, not a copy of plugin-managed instructions.
