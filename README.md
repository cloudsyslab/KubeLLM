# kubeLLM 🤖

KubeLLM is an LLM-based multi-agent framework that manages your kubernetes clusters all on its own. KubeLLM takes in ONE formatted prompt and it will automatically diagnose and apply fixes to Kubernetes configuration issues.

**Full documentation index:** [docs/README.md](docs/README.md) (architecture, agent iteration loop, operations, history).

---

### Execution environment
- Develop and run tests from your machine; use Docker, Kubernetes (for example Minikube), pgvector, and the RAG API as described below.
- Generic/legacy runner invocations default to the shared URL on loopback: `http://127.0.0.1:18000`. Minh's isolated lane uses an explicit private selector and a dedicated RAG port; see [lab-lanes.md](docs/handbook/lab-lanes.md).
- Set `RAG_API_URL` or `--rag-api-url` when the RAG API runs on another host.

### Minh's shared-lab workflow
For Minh's experiments, use the owner-only lane selector and the checkout's
lock-matched virtual environment. The preparation and benchmark skills do this
automatically; for a direct run:

```bash
export KUBELLM_LAB_CONFIG="${KUBELLM_LAB_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/kubellm/lanes/minh.json}"
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" --preflight
.venv/bin/python debug_assistant_latest/runner.py --lab-config "$KUBELLM_LAB_CONFIG" wrong_port --technique knowledgeAgentOnly
```

Do not use the generic `.env`, shared `minikube` profile, pgvector port 5532,
or RAG port 18000 for this lane. The remaining generic setup examples apply to
other researchers' separately selected environments.

---

### Author/Contact Information 📞
- Dr. Palden Lama - palden.lama@utsa.edu - (Current Contributor)
- William Clifford - william.clifford@utsa.edu - (Past Contributor)
- Aaron Perez - aaron.perez@utsa.edu - (Past Contributor)
- Mario De Jesus - mario.dejesus@utsa.edu - (Past Contributor)

---

### Link to Bugtracker 🐛
*(Coming Soon)*

---

### Test Cases 📁
All troubleshooting test cases are located in `debug_assistant_latest/troubleshooting/`. This is the canonical location for test case definitions.

---

### Running KubeLLM 🏃💨

#### Overview
- Canonical test definitions live in `debug_assistant_latest/troubleshooting/`.
- The recommended entrypoint is `debug_assistant_latest/runner.py`.
- `debug_assistant_latest/main.py` is a lower-level legacy entrypoint for a single config file.

#### Generic/legacy prerequisites
The following manual setup is for independent workspaces, not Minh's personal
shared-lab lane (use the lane workflow above).

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Create a repo-level `.env` file from the example:
```bash
cp .env.example .env
```

For OpenAI-backed chat or embedding configs, add your OpenAI key to `.env`:
```bash
OPENAI_API_KEY=your_key_here
```

For Ollama-only configs, `OPENAI_API_KEY` is not required unless you explicitly select an OpenAI chat model or embedder.

You also need:
- Docker available on the machine running tests
- A working Kubernetes environment (for example Minikube) when running cluster-backed tests
- PostgreSQL/pgvector reachable through `KUBELLM_DB_URL` (default:
  `postgresql+psycopg2://ai:ai@localhost:5532/ai`)
- The RAG API server running and reachable by the client code

Provider-specific prerequisites:
- OpenAI-only path: `OPENAI_API_KEY`, pgvector, and the RAG API server. Ollama is not required.
- Ollama-only path: Ollama service plus the selected Ollama model/embedder, pgvector, and the RAG API server. `OPENAI_API_KEY` is not required unless you choose an OpenAI model or embedder.
- Missing dependencies for an unselected provider are ignored by design.

Start pgvector:
```bash
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  phidata/pgvector:16
```

To use an isolated pgvector instance on another port, set its SQLAlchemy URL
in the repo-level `.env` file:
```bash
KUBELLM_DB_URL=postgresql+psycopg2://ai:ai@localhost:5533/ai
```

Start the RAG API server:
```bash
python start_apiserver.py
```

Linux/macOS wrapper:
```bash
bash start_apiserver.sh
```

RAG API URL precedence:
- `python3 debug_assistant_latest/runner.py ... --rag-api-url <url>`
- `RAG_API_URL` from the shell or `.env`
- default `http://127.0.0.1:${RAG_SERVER_PORT:-18000}`

Server bind defaults:
- `RAG_SERVER_HOST=127.0.0.1`
- `RAG_SERVER_PORT=18000`

Set `RAG_SERVER_HOST=0.0.0.0` only when you intentionally want remote clients to reach the API server. If you do that from another machine, also set `RAG_API_URL` (or `--rag-api-url`) to the externally reachable URL.

#### Typical workflow
When the runner and API server run on the same machine, leave `RAG_API_URL` unset unless you intentionally split them. A typical flow:

For Minh's personal lab lane, first set `KUBELLM_LAB_CONFIG` to the owner-only
config described in [lab-lanes.md](docs/handbook/lab-lanes.md). Once set, runner
commands below use that lane automatically; do not pass shared-profile or
shared-service overrides.

1. Go to the repo:
```bash
cd /path/to/KubeLLM-main
```

2. Start the RAG API server:
```bash
python3 start_apiserver.py
```

3. Run runner preflight before any test (lane-aware when `KUBELLM_LAB_CONFIG` is set):
```bash
python3 debug_assistant_latest/runner.py --preflight
```
The generic/manual helper is `bash orchestrator/preflight.sh <profile>`; do not
use it with the shared default kubeconfig for Minh's personal lane.

4. List available test cases:
```bash
python3 debug_assistant_latest/runner.py --list
```

5. Run one test case:
```bash
python3 debug_assistant_latest/runner.py wrong_port
```

6. Run multiple matching tests:
```bash
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4
```
This parallel form is for non-lane legacy runs; the personal lane enforces
serial execution.

7. Run a repeat queue for stability testing:
```bash
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900
```

#### Useful Runner Options
Override models:
```bash
python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o
python3 debug_assistant_latest/runner.py wrong_port --api-model gpt-5-mini
python3 debug_assistant_latest/runner.py wrong_port --verification-model gpt-4o
python3 debug_assistant_latest/runner.py wrong_port --embedder text-embedding-3-small --embedder-provider openai
```

Use a specific Minikube profile:
```bash
python3 debug_assistant_latest/runner.py wrong_port --minikube-profile minikube
```

Point the runner at a non-default API server:
```bash
python3 debug_assistant_latest/runner.py wrong_port --rag-api-url http://other-host:8000
```

Run with automatic teardown and fixture restoration:
```bash
python3 debug_assistant_latest/runner.py wrong_port --teardown-after-run
```

#### View Results
Each run writes logs and reports under `.local/test_runs/`.

Aggregate report:
```bash
cat .local/test_runs/*/aggregate.json | jq
```

Per-test summary:
```bash
cat .local/test_runs/*/wrong_port/summary.json | jq
```

Per-test stdout/stderr:
```bash
cat .local/test_runs/*/wrong_port/stdout.log
cat .local/test_runs/*/wrong_port/stderr.log
```

Find the latest run directory:
```bash
python3 debug_assistant_latest/runner.py --latest-run
```

Structured diagnosis and history:
```bash
python3 debug_assistant_latest/runner.py --diagnose-last
python3 debug_assistant_latest/runner.py --dashboard
```

#### Cleanup
Teardown one test case:
```bash
python3 debug_assistant_latest/teardownenv.py wrong_port
```

Teardown all supported test cases:
```bash
python3 debug_assistant_latest/teardownenv.py all
```
Broad teardown is refused while a personal lane is active; tear down one case.

#### Legacy Single-Config Entry Point
If you need to run the lower-level script directly instead of the runner:
```bash
python3 debug_assistant_latest/main.py debug_assistant_latest/troubleshooting/wrong_port/config_step.json
```

Use this only when you explicitly want the raw single-config execution path. The runner is the preferred interface.

---

### Agents 🕵️‍♀️
The default benchmark flow uses a Knowledge Agent to retrieve diagnostic
instructions, a corrective agent to apply them, and independent Verification
and Ground Truth checks afterward. The opt-in `knowledgeAgentOnly` POC removes
the corrective agent's generative step: it validates the Knowledge Agent's
strict JSON command plan, executes those commands deterministically, then
runs the same Verification and Ground Truth stages. See
[Architecture](docs/handbook/ARCHITECTURE.md) and [Personal lab lanes](docs/handbook/lab-lanes.md).

The Knowledge Agent uses pgvector and Retrieval-Augmented Generation (RAG) to
store and retrieve relevant knowledge, primarily Kubernetes documentation.

* Our approach is currently based off this graph here [Kubernetes Troubleshooting Graph](https://learnk8s.io/troubleshooting-deployments)

### Citation
If you use KubeLLM in your work, please cite the following paper:
```
@inproceedings{de2025llm,
  author    = {Mario De Jesus and Perfect Sylvester and William Clifford and Aaron Perez and Palden Lama},
  title     = {LLM-Based Multi-Agent Framework for Troubleshooting Distributed Systems},
  booktitle = {Proceedings of the IEEE Cloud Summit},
  year      = {2025}
}
```
