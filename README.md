# kubellm 🤖

KubeLLM is an AI agent that manages your kubernetes clusters all on its own. KubeLLM takes in ONE formatted prompt and it will solve it using various state of the art techniques to not just figure the issue, but also resolve it within your enviornment.

---

### Author/Contact Information 📞
- Dr. Palden Lama - palden.lama@utsa.edu
- William Clifford - william.clifford@utsa.edu
- Aaron Perez - aaron.perez@utsa.edu
- Mario De Jesus - mario.dejesus@utsa.edu

---

### Link to Bugtracker ? 🐛

---

### Known Issues ⚠️
1. Improve AI to answer correctly consistantly
2. Allow for a timeout after a time limit set by us. Sometimes the AI will go on forever without fixing the issue.
3. Have a Development enviornment and Production enviornment, so the debug AI can make changes to the enviornment without any further issues developing. It would also be nice to have a snapshot before running KubeLLM in order to revert if it failed.

---

### Instructions to Run 🏃💨
1. Simply download the files onto the GPU server once given access. From there you will traverse down to the location of your KubeLLM folder.
2. Once in the KubeLLM folder start by running the **./start_apiserver.sh**.
3. Once you have the API Agent running in the background or another terminal simply go down debug_assistant_latest.
4. Then run ***./main /home/mario/AgentAnalysis/WilliamAgent/phidata-samples/debug_assistant_latetest/troubleshooting/TEST_CASE_TO_RUN/config.json.***
5. You may need to update config to contain the right paths. *(Note : This will be updated in a future update)*
6. Finally, just sit back and let KubeLLM do all of the work.

---

### Instructions to Run Tests 📝
*(Coming soon in a future update)*
