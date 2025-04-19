# kubeLLM 🤖

KubeLLM is an LLM-based multi-agent framework that manages your kubernetes clusters all on its own. KubeLLM takes in ONE formatted prompt and it will automatically diagnose and apply fixes to Kubernetes configuration issues. 

---

### Author/Contact Information 📞
- Dr. Palden Lama - palden.lama@utsa.edu - (Current Contributor)
- William Clifford - william.clifford@utsa.edu - (Past Contributor)
- Aaron Perez - aaron.perez@utsa.edu - (Past Contributor)
- Mario De Jesus - mario.dejesus@utsa.edu - (Current Contributor)

---

### Link to Bugtracker 🐛
*(Coming Soon)*

---

### Instructions to Run 🏃💨
1. Navigate to the KubeLLM directory and start the Knowledge Agent with RAG capability by running the **./start_apiserver.sh**.
3. Once you have the Knowledge Agent running in the background or another terminal, change directory to debug_assistant_latest.
4. Optional: if you need to run a single test case only
   ***python3 main.py ~/KubeLLM/debug_assistant_latest/troubleshooting/TEST_CASE_TO_RUN/config.json.***
6. You may need to update config to contain the right paths. *(Note : This will be updated in a future update)*
7. Finally, just sit back and let KubeLLM do all of the work.

---

### Instructions to Run Tests 📝
Simply navigate to the kube_test.py file in debug_assistant_latest folder and run the test.
```
  python3 kube_test.py
```

---

### Agents 🕵️‍♀️
Currently our approach uses two agents, one for knowledge and one that takes corrective actions recommended by the knowledge agent. The knowledge agent uses a pgvector database and Retrieval-Augmented Generation (RAG) technique to store and retrieve relevant knowledge, which primarily consists of Kubernetes documentation.

* Our approach is currently based off this graph here [Kubernetes Troubleshooting Graph](https://learnk8s.io/troubleshooting-deployments)
