# kubeLLM 🤖

KubeLLM is an LLM-based multi-agent framework that manages your kubernetes clusters all on its own. KubeLLM takes in ONE formatted prompt and it will automatically diagnose and apply fixes to Kubernetes configuration issues. 

---

### Lab vs Local Execution
- ALL tests and operational commands must be run on the lab server.
- Local environment is for development/editing only (AI access and code changes).

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

#### Prerequisites
Install Python dependencies:
```bash
pip install -r requirements.txt
```

Create a repo-level `.env` file from the example:
```bash
cp .env.example .env
```

Then add your OpenAI key to `.env`:
```bash
OPENAI_API_KEY=your_key_here
```

You also need:
- Docker available on the machine running tests
- A working Kubernetes environment (Minikube on the lab server)
- Access to the required model providers through `.env` or exported shell variables
- PostgreSQL/pgvector running locally on port `5532`
- The RAG API server running and reachable by the client code

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

Start the RAG API server:
```bash
bash start_apiserver.sh
```

Note:
- The current RAG API client in `debug_assistant_latest/rag_api.py` uses a fixed `BASE_URL`.
- Confirm that the configured host matches the server you started before running tests.

#### Lab Server Workflow
Run all operational commands on the lab server. The normal flow is:

1. Go to the repo:
```bash
cd ~/kubellm-minh-testing
```

2. Run preflight before any test:
```bash
bash orchestrator/preflight.sh
```

3. List available test cases:
```bash
python3 debug_assistant_latest/runner.py --list
```

4. Run one test case:
```bash
python3 debug_assistant_latest/runner.py wrong_port
```

5. Run multiple matching tests:
```bash
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4
```

6. Run a repeat queue for stability testing:
```bash
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900
```

#### Useful Runner Options
Override models:
```bash
python3 debug_assistant_latest/runner.py wrong_port --debug-model gpt-4o
python3 debug_assistant_latest/runner.py wrong_port --api-model gpt-5-mini
python3 debug_assistant_latest/runner.py wrong_port --verification-model gpt-4o
```

Use a specific Minikube profile:
```bash
python3 debug_assistant_latest/runner.py wrong_port --minikube-profile minh
```

Run with automatic backup and teardown:
```bash
python3 debug_assistant_latest/runner.py wrong_port --backup-before-run --teardown-after-run
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

Find the latest runs:
```bash
ls -lt .local/test_runs/ | head -5
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

#### Legacy Single-Config Entry Point
If you need to run the lower-level script directly instead of the runner:
```bash
python3 debug_assistant_latest/main.py debug_assistant_latest/troubleshooting/wrong_port/config_step.json
```

Use this only when you explicitly want the raw single-config execution path. The runner is the preferred interface.

---

### Agents 🕵️‍♀️
Currently our approach uses two agents, one for knowledge and one that takes corrective actions recommended by the knowledge agent. The knowledge agent uses a pgvector database and Retrieval-Augmented Generation (RAG) technique to store and retrieve relevant knowledge, which primarily consists of Kubernetes documentation.

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
