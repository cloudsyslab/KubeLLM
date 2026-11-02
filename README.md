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

## Private operator UI

The local operator UI checks or prepares the selected private lab lane, runs
serial benchmark campaigns through the canonical runner, and visualizes
structured benchmark history. It binds to `127.0.0.1` and stores its login,
job database, runner logs, and results under ignored `.local/operator_ui/`
and `.local/test_runs/operator_ui/` paths.

Set up the single-operator login once, save the generated password in your
password manager, then start the server:

```bash
make operator-ui-auth
make operator-ui
```

The setup command prints the password once; it is stored hashed in an
owner-only local settings file. Open `http://127.0.0.1:8787` on the server or
forward it through your existing private SSH connection:

```bash
ssh -L 8787:127.0.0.1:8787 <server>
```

The app uses `KUBELLM_LAB_CONFIG` when set, or the private
`~/.config/kubellm/lanes/minh.json` selector by default. It never falls back to
the active Kubernetes context. Change the login with
`python3 -m operator_ui.setup_auth --reset`.
Campaigns require a preflight from the current server session and selected
lane that is less than 20 minutes old.

Completed campaigns include a safe Markdown summary. **Publish results** opens
a preview of the exact sanitized archive files and model identifiers; confirming
it creates a path-scoped commit and pushes it to the branch's configured
upstream. Publishing refuses the default branch: run it on a results branch
and merge that through a pull request.
Raw logs and prompts stay in ignored `.local/` storage. Case, prompt, and RAG
editing are not part of this first operator pass.

Agent operating rules and skill routes are in [AGENTS.md](AGENTS.md). The
[documentation map](docs/README.md) links benchmark, prediction-research, and
branch-history material. The paired selector pilot and its limitations are
documented in [data analysis](data_analysis/README.md) and its
[sanitized evidence pack](data/exploratory/prediction-pilot-2026-10/README.md).

## Citation

```bibtex
@inproceedings{de2025llm,
  author    = {Mario De Jesus and Perfect Sylvester and William Clifford and Aaron Perez and Palden Lama},
  title     = {LLM-Based Multi-Agent Framework for Troubleshooting Distributed Systems},
  booktitle = {Proceedings of the IEEE Cloud Summit},
  year      = {2025}
}
```
