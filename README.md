# KubeLLM

KubeLLM is a research harness for evaluating multi-agent diagnosis and repair
of Kubernetes failures. It combines a Knowledge Agent, tool execution,
independent Verification, and deterministic Ground Truth.

The canonical interface is `debug_assistant_latest/runner.py`; cases live in
`debug_assistant_latest/troubleshooting/`. Four techniques can be selected:
`allStepsAtOnce`, `stepByStep`, `singleAgent`, and `knowledgeAgentOnly`. The
last validates the Knowledge Agent's structured plan and executes it without
a generative tools agent. See the [architecture reference](.agents/skills/kubellm-benchmarks/references/architecture.md).

## Quick start

Install the project dependencies in a compatible Python environment, then
check the runner and case definitions:

```bash
python3 -m pip install -r requirements.txt
python3 debug_assistant_latest/runner.py --list
python3 debug_assistant_latest/runner.py --validate-ground-truth
```

Live cases require the configured model provider, RAG API, pgvector, Docker,
and Kubernetes environment. Run `runner.py --preflight` before a live case.
For an isolated/shared lab, select its owner-only lane explicitly with
`KUBELLM_LAB_CONFIG` or `--lab-config`; do not rely on the current kubectl
context or shared defaults. Full preparation and safe run commands are in
[$kubellm-benchmarks](.agents/skills/kubellm-benchmarks/SKILL.md).

Example after the selected environment is ready:

```bash
python3 debug_assistant_latest/runner.py wrong_port --technique knowledgeAgentOnly
```

Run unit tests with `python3 -m pytest tests/ -q`. Keep generated benchmark
artifacts in ignored `.local/`; use `$kubellm-benchmarks` to run and report a
suite or analyze existing results. The
[benchmark catalog](data/README.md) documents structured exports and their
integrity status.

Agent operating rules and skill routes are in [AGENTS.md](AGENTS.md). The
`docs/` directory retains branch-history records; benchmark and operational
guidance lives with the focused skills under `.agents/skills/`.

## Citation

```bibtex
@inproceedings{de2025llm,
  author    = {Mario De Jesus and Perfect Sylvester and William Clifford and Aaron Perez and Palden Lama},
  title     = {LLM-Based Multi-Agent Framework for Troubleshooting Distributed Systems},
  booktitle = {Proceedings of the IEEE Cloud Summit},
  year      = {2025}
}
```
