# Recent Refactor & Testing Updates

- Modularized the agents by splitting `api_agents.py`, `debug_agents.py`, and `verification_agents.py`, and removed the old `agents.py` shim so callers import the new modules directly.
- Added shared helpers (`agent_helpers.py`, `prompt_helpers.py`, `verification_base.py`) plus a dedicated teardown helper and runtime config, and updated the architecture docs to reflect the new layout.
- Wrapped every `phi` import in the helpers so the code can be imported even when `phi` is missing (with informative runtime errors when the missing paths are actually used).
- Expanded tests in `tests/test_refactor_helpers.py` to cover repeat-queue success/stall flows and the verification-status utilities; the suite still runs via `python3 -m unittest discover -s tests -p 'test_*.py'`.
- Added an `inspect.getargspec` shim in the tests so the newly installed `phi` package (which expects the old API) can load without errors.
