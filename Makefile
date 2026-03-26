PYTHON ?= python3
TEST ?=
JOBS ?= 1

.PHONY: preflight test-unit validate-gt list run run-all

preflight:
	$(PYTHON) debug_assistant_latest/runner.py --preflight

test-unit:
	$(PYTHON) -m pytest tests/ -v

validate-gt:
	$(PYTHON) debug_assistant_latest/runner.py --validate-ground-truth

list:
	$(PYTHON) debug_assistant_latest/runner.py --list

run:
ifndef TEST
	$(error TEST is required, for example: make run TEST=wrong_port)
endif
	$(PYTHON) debug_assistant_latest/runner.py $(TEST)

run-all:
	$(PYTHON) debug_assistant_latest/runner.py --run-many all --jobs $(JOBS)
