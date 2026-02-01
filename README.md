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

### Instructions to Run 🏃💨
1. Navigate to KubeLLM directory and install software dependencies as follows:
   pip install -r requirements.txt
2. Make sure Kubernetes (MiniKube) is up and running.
3. Start the PgVector database using the following command:
   docker run -d \\   
  -e POSTGRES_DB=ai \\   
  -e POSTGRES_USER=ai \\   
  -e POSTGRES_PASSWORD=ai \\   
  -e PGDATA=/var/lib/postgresql/data/pgdata \\   
  -v pgvolume:/var/lib/postgresql/data \\   
  -p 5532:5432 \\   
  --name pgvector \\   
  phidata/pgvector:16

4. Start the Knowledge Agent with RAG capability by running the **bash start_apiserver.sh**.
5. Once you have the Knowledge Agent running in the background or another terminal, change directory to debug_assistant_latest.
6. Optional: if you need to run a single test case only
   ***python3 main.py ~/KubeLLM/debug_assistant_latest/troubleshooting/TEST_CASE_NAME/config_step.json.***
7. You may need to update config to contain the right paths. *(Note : This will be updated in a future update)*
8. Finally, just sit back and let KubeLLM do all of the work. Make sure to teardown the environment after each individual test case run.
   ***python3 teardownenv.py TEST_CASE_NAME***
    

---

### Test Cases 📁
All troubleshooting test cases are located in `debug_assistant_latest/troubleshooting/`. This is the canonical location for test case definitions.

---

### Instructions to Run Tests 📝
Recommended: use the test runner.
```
python3 debug_assistant_latest/runner.py --list
python3 debug_assistant_latest/runner.py wrong_port
python3 debug_assistant_latest/runner.py --run-many "port_*" --jobs 4

# Repeat queue (serial, teardown forced, hard-kill on stall)
python3 debug_assistant_latest/runner.py wrong_port --repeat 10 --stall-limit-s 900
```

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
