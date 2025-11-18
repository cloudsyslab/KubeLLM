# Troubleshooting Guide

## Quick Diagnostics

### System Health Check

Run this comprehensive health check first:

```bash
#!/bin/bash
echo "=== KubeLLM-Minh System Health Check ==="

# 1. Python and packages
echo -e "\n[1/7] Checking Python..."
python3 --version
pip show phidata | grep Version

# 2. Minikube
echo -e "\n[2/7] Checking Minikube..."
minikube status -p lamap
kubectl get nodes

# 3. Docker
echo -e "\n[3/7] Checking Docker..."
docker --version
eval $(minikube -p lamap docker-env)
docker images | grep kube | head -5

# 4. PostgreSQL
echo -e "\n[4/7] Checking PostgreSQL..."
psql postgresql://ai:ai@localhost:5532/ai -c "SELECT version();" 2>&1 | head -1
psql postgresql://ai:ai@localhost:5532/ai -c "\dx vector" 2>&1 | grep vector

# 5. Ollama (if using local models)
echo -e "\n[5/7] Checking Ollama..."
ollama list 2>&1 | grep llama

# 6. Environment Variables
echo -e "\n[6/7] Checking Environment Variables..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "WARNING: OPENAI_API_KEY not set"
else
    echo "✓ OPENAI_API_KEY is set"
fi

# 7. Project Structure
echo -e "\n[7/7] Checking Project Structure..."
[ -f ~/KubeLLM-Minh/debug_assistant_latest/main.py ] && echo "✓ main.py found"
[ -f ~/KubeLLM-Minh/debug_assistant_latest/agents.py ] && echo "✓ agents.py found"
[ -d ~/KubeLLM-Minh/debug_assistant_latest/troubleshooting ] && echo "✓ troubleshooting/ found"

echo -e "\n=== Health Check Complete ==="
```

Save as `health_check.sh` and run: `bash health_check.sh`

---

## Common Issues and Solutions

### 1. Agent Execution Issues

#### Problem: Agent Times Out (480 seconds)

**Symptoms**:
```
timeout_decorator.TimeoutError: 'Timed Out'
```

**Causes**:
- Agent using blocking commands (e.g., `kubectl logs -f`)
- Infinite reasoning loop
- Very slow model responses
- Network issues with API calls

**Solutions**:

1. **Check for blocking commands**:
```python
# In agents.py, add to instructions
"Do not use live feed flags like 'kubectl logs -f'",
"Do not use blocking commands",
"Always use finite commands that return immediately"
```

2. **Reduce timeout for testing** (debug_assistant_latest/agents.py:166):
```python
@timeout_decorator.timeout(240)  # Reduce from 480 to 240 for testing
def askQuestion(self):
```

3. **Use faster model**:
```json
{
  "debug-agent": {
    "model": "gemini-1.5-flash"  // Much faster than gpt-4o
  }
}
```

4. **Check network connectivity**:
```bash
# Test OpenAI API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[0]'

# Test Ollama (local)
curl http://localhost:11434/api/tags | jq .
```

---

#### Problem: Agent Hangs Without Timeout

**Symptoms**:
- No output for extended period
- Process doesn't terminate
- No timeout error

**Solutions**:

1. **Force kill and check logs**:
```bash
# Find process
ps aux | grep python3

# Kill it
kill -9 <PID>

# Check what command it was running
kubectl get events --sort-by='.lastTimestamp' | tail -20
```

2. **Add explicit timeout decorator**:
```python
@withTimeout(False)
@timeout_decorator.timeout(480)
def askQuestion(self):
    # Your code
```

3. **Enable more verbose logging**:
```python
self.agent = llmAgent(
    model=model,
    tools=[BetterShellTools()],
    debug_mode=True,
    show_tool_calls=True,
    # Add verbose flag if available
)
```

---

#### Problem: Agent Reports Success but Actually Failed

**Symptoms**:
- Debug agent returns `<|SOLVED|>`
- Verification agent returns `<|FAILED|>`
- Mismatch between self-report and verification

**This is EXPECTED behavior!** The verification agent is correct.

**Why it happens**:
- Agent misinterprets command output
- Agent assumes success without checking
- Timing issues (changes not propagated yet)

**Solutions**:

1. **Trust the verification agent** - This is why it exists!

2. **Improve debug agent instructions**:
```python
instructions = [
    "After each kubectl command, verify it succeeded",
    "Check pod status with 'kubectl get pods' before claiming success",
    "Only use <|SOLVED|> if you see the pod in Running state with 1/1 ready",
    "If unsure, use <|FAILED|> and describe what's unclear"
]
```

3. **Add explicit verification steps to debug agent**:
```python
prompt += "\nBefore reporting <|SOLVED|>, verify:\n"
prompt += "1. Run 'kubectl get pods' and confirm Running state\n"
prompt += "2. Run 'kubectl describe pod' and check for errors\n"
prompt += "3. Only then report <|SOLVED|>\n"
```

---

### 2. Minikube Issues

#### Problem: Minikube Not Started

**Symptoms**:
```
Error: No minikube cluster found
kubectl: connection refused
```

**Solutions**:

```bash
# Check status
minikube status -p lamap

# Start if not running
minikube start -p lamap

# If corrupted, delete and recreate
minikube delete -p lamap
minikube start -p lamap

# Verify
kubectl get nodes
```

---

#### Problem: Docker Images Not Found in Minikube

**Symptoms**:
```
ImagePullBackOff
Error: ErrImageNeverPull
```

**Cause**: Not using Minikube's Docker daemon

**Solutions**:

```bash
# CRITICAL: Always set Docker environment
eval $(minikube -p lamap docker-env)

# Verify it's set
echo $DOCKER_HOST  # Should show minikube URL

# Build image in Minikube context
docker build -t kube-wrong-port-app .

# Verify image exists in Minikube
docker images | grep kube

# Add to ~/.bashrc for persistence
echo 'eval $(minikube -p lamap docker-env)' >> ~/.bashrc
```

---

#### Problem: Service Not Accessible from Host

**Symptoms**:
```
curl: (7) Failed to connect to localhost port 8080
```

**Cause**: Services in Minikube not exposed to host by default

**Solutions**:

```bash
# Method 1: Use minikube service (RECOMMENDED)
minikube -p lamap service app-service --url
# Returns: http://192.168.49.2:31234
curl http://192.168.49.2:31234

# Method 2: Port forwarding
kubectl port-forward service/app-service 8080:80
curl localhost:8080

# Method 3: Minikube tunnel (requires sudo)
minikube -p lamap tunnel
# Then use ClusterIP directly
```

**For Verification Agent**:
Update verification to use minikube service command:
```python
prompt += "Use 'minikube -p lamap service <name> --url' to get accessible URL\n"
prompt += "Then test with 'curl <url>'\n"
```

---

### 3. PostgreSQL / pgvector Issues

#### Problem: Cannot Connect to PostgreSQL

**Symptoms**:
```
psycopg.OperationalError: could not connect to server
connection refused
```

**Solutions**:

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Check if listening on correct port
netstat -an | grep 5532

# If port is wrong, update postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf
# Set: port = 5532

# Restart
sudo systemctl restart postgresql

# Test connection
psql postgresql://ai:ai@localhost:5532/ai -c "SELECT 1"
```

---

#### Problem: pgvector Extension Not Found

**Symptoms**:
```
ERROR: extension "vector" does not exist
```

**Solutions**:

```bash
# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Enable in database
psql postgresql://ai:ai@localhost:5532/ai
CREATE EXTENSION vector;
\dx  # Verify it's listed
```

---

#### Problem: Knowledge Base Empty / No Documents

**Symptoms**:
- RAG returns generic responses
- No context from documentation
- Verification: 0 documents in vector DB

**Solutions**:

```python
# Check document count
import psycopg
conn = psycopg.connect("postgresql://ai:ai@localhost:5532/ai")
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM "local_rag_documents_nomic-embed-text"')
print(f"Documents: {cursor.fetchone()[0]}")

# If 0, manually add documents
from rag_api import initialize_assistant, add_url

initialize_assistant("llama3.1:70b", "nomic-embed-text")
add_url("https://learnk8s.io/troubleshooting-deployments")

# Verify again
cursor.execute('SELECT COUNT(*) FROM "local_rag_documents_nomic-embed-text"')
print(f"Documents: {cursor.fetchone()[0]}")
```

---

### 4. LLM / API Issues

#### Problem: OpenAI API Key Invalid

**Symptoms**:
```
openai.error.AuthenticationError: Invalid API key
```

**Solutions**:

```bash
# Check if set
echo $OPENAI_API_KEY

# Set temporarily
export OPENAI_API_KEY="sk-proj-..."

# Set permanently
echo 'export OPENAI_API_KEY="sk-proj-..."' >> ~/.bashrc
source ~/.bashrc

# Test
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq .
```

---

#### Problem: Ollama Model Not Found

**Symptoms**:
```
Error: model 'llama3.1:70b' not found
```

**Solutions**:

```bash
# List available models
ollama list

# Pull required model
ollama pull llama3.1:70b

# Verify
ollama list | grep llama3.1

# Test
ollama run llama3.1:70b "Hello"
```

---

#### Problem: Rate Limiting / API Quota Exceeded

**Symptoms**:
```
openai.error.RateLimitError: Rate limit exceeded
429 Too Many Requests
```

**Solutions**:

1. **Switch to local model**:
```json
{
  "debug-agent": {
    "model": "llama3.1:70b"  // Use Ollama instead
  }
}
```

2. **Add delays between requests**:
```python
import time
# In kube_test.py
for testNumber in range(numTests):
    testResults = runSingleTest(testFunc, configFile)
    time.sleep(60)  # Wait 60 seconds between tests
```

3. **Use lower-tier model**:
```json
{
  "debug-agent": {
    "model": "gpt-3.5-turbo"  // Cheaper, higher limits
  }
}
```

---

### 5. Test Execution Issues

#### Problem: Test Fails to Clean Up

**Symptoms**:
- Resources remain in cluster
- Docker images not deleted
- Backup files not restored

**Solutions**:

```bash
# Manual cleanup script
#!/bin/bash
TEST_NAME="wrong_port"

# Delete Kubernetes resources
kubectl delete -f ~/KubeLLM/debug_assistant_latest/troubleshooting/$TEST_NAME/*.yaml --grace-period=0 --force

# Delete Docker images
docker rmi -f kube-$TEST_NAME-app

# Restore backups
cd ~/KubeLLM/debug_assistant_latest/troubleshooting/$TEST_NAME/
if [ -f backup_yaml.yaml ]; then
    cp backup_yaml.yaml ${TEST_NAME}.yaml
fi
if [ -f backup_server.py ]; then
    cp backup_server.py server.py
fi
if [ -f backup_Dockerfile ]; then
    cp backup_Dockerfile Dockerfile
fi

echo "Cleanup complete for $TEST_NAME"
```

Save as `cleanup_test.sh` and run: `bash cleanup_test.sh`

---

#### Problem: Container Rebuild Not Detected

**Symptoms**:
- Modified Dockerfile but container uses old image
- Changes not reflected in pod
- Using cached layers

**Solutions**:

```bash
# Force rebuild with no cache
docker build -t kube-wrong-port-app . --no-cache

# Delete old pods to force image pull
kubectl delete pod <pod-name>

# Verify new image
docker images | grep kube-wrong-port-app
# Check created timestamp

# In agent instructions, add:
"When rebuilding containers, always use --no-cache flag",
"After rebuilding, delete and recreate pods to force new image"
```

---

#### Problem: kubectl Commands Fail with Permission Errors

**Symptoms**:
```
Error from server (Forbidden): pods is forbidden
User cannot list resource "pods"
```

**Solutions**:

```bash
# Check kubectl config
kubectl config view

# Ensure using correct context
kubectl config current-context

# Should be: lamap

# If wrong, switch
kubectl config use-context lamap

# Verify access
kubectl auth can-i get pods
# Should return: yes
```

---

### 6. Metrics and Database Issues

#### Problem: Metrics Not Saved

**Symptoms**:
- No data in metrics database
- SQLite file doesn't exist
- Empty query results

**Solutions**:

```bash
# Check if database exists
ls -lh ~/KubeLLM/token_metrics.db

# If not, create it
sqlite3 ~/KubeLLM/token_metrics.db << 'EOF'
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_case TEXT,
    model TEXT,
    agent_type TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    task_status INTEGER,
    duration_s REAL,
    cost REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
EOF

# Verify table created
sqlite3 ~/KubeLLM/token_metrics.db "SELECT name FROM sqlite_master WHERE type='table';"
```

---

#### Problem: Cost Calculation Returns 0

**Symptoms**:
- All costs show as $0.00
- Metrics saved but cost not calculated

**Cause**: Model name not in pricing dictionary

**Solutions**:

Edit `debug_assistant_latest/metrics_db.py`:

```python
def calculate_cost(model_name, input_tokens, output_tokens):
    # Pricing per 1M tokens
    pricing = {
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},
        "o3-mini": {"input": 1.10, "output": 4.40},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "llama3.1:70b": {"input": 0, "output": 0},  # Local model
        # Add your model here
        "your-model-name": {"input": X, "output": Y},
    }

    # Find matching model
    for model_key in pricing:
        if model_key in model_name:
            input_cost = (input_tokens / 1_000_000) * pricing[model_key]["input"]
            output_cost = (output_tokens / 1_000_000) * pricing[model_key]["output"]
            return input_cost + output_cost

    # Default if not found
    print(f"WARNING: No pricing for model {model_name}, using $0")
    return 0.0
```

---

### 7. File and Path Issues

#### Problem: File Not Found Errors

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: '...'
```

**Solutions**:

```python
# Always use absolute paths or Path.expanduser()
from pathlib import Path

# Instead of:
file_path = "~/KubeLLM/debug_assistant_latest/troubleshooting/wrong_port/"

# Use:
file_path = Path("~/KubeLLM/debug_assistant_latest/troubleshooting/wrong_port/").expanduser()

# Verify path exists
if not file_path.exists():
    raise FileNotFoundError(f"Path does not exist: {file_path}")
```

---

#### Problem: Config File Parse Error

**Symptoms**:
```
json.decoder.JSONDecodeError: Expecting ',' delimiter
```

**Solutions**:

```bash
# Validate JSON syntax
python3 -m json.tool troubleshooting/wrong_port/config.json

# If it shows errors, fix them
# Common issues:
# - Missing commas
# - Trailing commas (not allowed in JSON)
# - Unescaped quotes in strings
# - Comments (not allowed in JSON)

# Example fix:
# WRONG:
{
  "model": "gpt-4o",  // This is a comment
  "temperature": 0.5,  # Trailing comma here
}

# CORRECT:
{
  "model": "gpt-4o",
  "temperature": 0.5
}
```

---

### 8. Agent Behavior Issues

#### Problem: Agent Uses Placeholder Names

**Symptoms**:
```
kubectl describe pod <pod-name>
Error: pods "<pod-name>" not found
```

**Cause**: Agent didn't retrieve actual resource names first

**Solutions**:

Add to agent instructions:

```python
instructions = [
    "When writing kubectl commands, use REAL resource names, never placeholders",
    "Before using 'kubectl describe pod <name>', first run 'kubectl get pods' to get the actual pod name",
    "Before using 'kubectl describe service <name>', first run 'kubectl get services' to get the actual service name",
    "Extract the exact name from previous command output",
    "Example: If 'kubectl get pods' shows 'my-app-abc123', use that exact name in subsequent commands"
]
```

---

#### Problem: Agent Repeats Failed Commands

**Symptoms**:
- Same command executed 5+ times
- Same error repeated
- No learning from failures

**Solutions**:

Add to agent instructions:

```python
instructions = [
    "Never repeat a command that failed",
    "If a command fails, analyze the error and try a DIFFERENT approach",
    "Do not retry the same command more than once",
    "If stuck, report <|FAILED|> with description of the issue"
]

guidelines = [
    "Keep track of what you've already tried",
    "Each action should be different from previous failures",
    "If the same error occurs twice, stop and report failure"
]
```

---

#### Problem: Agent Modifies Wrong Files

**Symptoms**:
- Changes files outside test directory
- Modifies backup files instead of active files
- Edits irrelevant configuration

**Solutions**:

Add explicit file restrictions:

```python
prompt += f"\nYou may ONLY modify files in this directory: {test_directory}\n"
prompt += "Do NOT modify any backup_* files\n"
prompt += f"The files you can modify are: {relevant_files}\n"
prompt += "Do NOT modify any files outside the specified directory\n"
```

---

### 9. Verification Issues

#### Problem: Verification Agent Cannot Access Services

**Symptoms**:
```
curl: (7) Failed to connect
Connection refused
```

**Cause**: Not using minikube service command

**Solutions**:

Update `AgentVerification_v2` prompt to emphasize minikube:

```python
prompt += """
### CRITICAL: Service Testing on Minikube
Since this is Minikube, services are NOT accessible on localhost.

To test a service:
1. Get service name: `kubectl get services`
2. Get service URL: `minikube -p lamap service <service-name> --url`
3. The command returns a URL like http://192.168.49.2:31234
4. Test that URL: `curl -v http://192.168.49.2:31234`

DO NOT use localhost or 127.0.0.1 for services.
"""
```

---

#### Problem: Verification Tokens Not Recognized

**Symptoms**:
- Verification status shows as None
- No token found in response
- Status reported as UNKNOWN

**Cause**: Agent using wrong token format

**Solutions**:

Strengthen token instructions:

```python
prompt += "\n\n=== CRITICAL: EXACT TOKEN USAGE ===\n"
prompt += "You MUST end your response with EXACTLY ONE of these tokens:\n"
prompt += "1. <|VERIFIED|>  (if issue is completely resolved)\n"
prompt += "2. <|FAILED|>  (if issue is NOT resolved)\n"
prompt += "3. <|VERIFICATION_ERROR|>  (if you cannot verify)\n\n"
prompt += "DO NOT:\n"
prompt += "- Create custom tokens like <|SUCCESS|> or <|FIXED|>\n"
prompt += "- Modify the tokens in any way\n"
prompt += "- Use multiple tokens\n"
prompt += "- Forget to include a token\n\n"
prompt += "Copy and paste the exact token from the list above.\n"
```

---

### 10. Performance Issues

#### Problem: Tests Take Too Long

**Symptoms**:
- Each test takes 10+ minutes
- Frequent timeouts
- High token usage

**Solutions**:

1. **Use faster models**:
```json
{
  "api-agent": {
    "model": "llama3.1:70b"  // Local, fast
  },
  "debug-agent": {
    "model": "gemini-1.5-flash"  // Cloud, very fast
  },
  "verification-agent": {
    "model": "gemini-1.5-flash"
  }
}
```

2. **Reduce RAG documents**:
```python
knowledge = AgentKnowledge(
    vector_db=PgVector(...),
    num_documents=2,  # Reduce from 3
)
```

3. **Optimize prompts**:
- Remove unnecessary file contents
- Use summaries instead of full files
- Reduce instruction verbosity

4. **Parallel execution** (future enhancement):
```python
# Run multiple tests in parallel
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(runSingleTest, testFunc, config) for config in configs]
    results = [f.result() for f in futures]
```

---

## Diagnostic Tools

### 1. Test Status Monitor

```python
#!/usr/bin/env python3
# watch_test.py - Monitor test execution in real-time

import sqlite3
import time
from datetime import datetime

db_path = "~/KubeLLM/token_metrics.db"

print("=== KubeLLM Test Monitor ===")
print("Watching for new test results...\n")

last_count = 0
while True:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT test_case, model, agent_type, task_status, cost, timestamp
        FROM metrics
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    results = cursor.fetchall()
    current_count = len(results)

    if current_count > last_count:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New results:")
        for row in results[:current_count - last_count]:
            test, model, agent, status, cost, ts = row
            status_str = "✓ PASS" if status == 1 else "✗ FAIL" if status == 0 else "? ERROR"
            print(f"  {status_str} | {test} | {agent} | ${cost:.4f}")

    last_count = current_count
    conn.close()
    time.sleep(5)
```

Run: `python3 watch_test.py`

---

### 2. Agent Response Analyzer

```python
#!/usr/bin/env python3
# analyze_response.py - Analyze agent responses for common issues

import re
import sys

def analyze_response(response_text):
    """Analyze agent response for common issues"""
    issues = []

    # Check for placeholder names
    if re.search(r'<[^>]+name>', response_text):
        issues.append("⚠ Contains placeholder names like <pod-name>")

    # Check for blocking commands
    if 'kubectl logs -f' in response_text:
        issues.append("⚠ Uses blocking command: kubectl logs -f")

    if 'kubectl edit' in response_text:
        issues.append("⚠ Uses interactive command: kubectl edit")

    # Check for status tokens
    tokens_found = []
    if '<|SOLVED|>' in response_text:
        tokens_found.append('SOLVED')
    if '<|VERIFIED|>' in response_text:
        tokens_found.append('VERIFIED')
    if '<|FAILED|>' in response_text:
        tokens_found.append('FAILED')

    if not tokens_found:
        issues.append("⚠ No status token found")
    elif len(tokens_found) > 1:
        issues.append(f"⚠ Multiple status tokens: {', '.join(tokens_found)}")

    # Check for localhost usage
    if 'localhost' in response_text or '127.0.0.1' in response_text:
        issues.append("⚠ May be using localhost (won't work in Kubernetes)")

    return issues

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_response.py <response_file>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        response = f.read()

    issues = analyze_response(response)

    if issues:
        print("=== Issues Found ===")
        for issue in issues:
            print(issue)
    else:
        print("✓ No issues detected")
```

Usage:
```bash
# Save agent response to file
echo "$AGENT_RESPONSE" > response.txt

# Analyze
python3 analyze_response.py response.txt
```

---

### 3. Environment Reset Script

```bash
#!/bin/bash
# reset_environment.sh - Complete environment reset

echo "=== Resetting KubeLLM Environment ==="

# 1. Stop all tests
echo "[1/6] Stopping any running tests..."
pkill -f "python3 main.py"
pkill -f "python3 kube_test.py"

# 2. Clean Kubernetes resources
echo "[2/6] Cleaning Kubernetes resources..."
kubectl delete pods --all --grace-period=0 --force
kubectl delete services --all
kubectl delete deployments --all

# 3. Clean Docker images
echo "[3/6] Cleaning Docker images..."
eval $(minikube -p lamap docker-env)
docker images | grep kube | awk '{print $3}' | xargs -r docker rmi -f

# 4. Restore all backup files
echo "[4/6] Restoring backup files..."
cd ~/KubeLLM/debug_assistant_latest/troubleshooting/
for dir in */; do
    cd "$dir"
    for backup in backup_*; do
        if [ -f "$backup" ]; then
            original="${backup#backup_}"
            original="${original%.yaml}.yaml"
            original="${original%.py}.py"
            original="${original%_Dockerfile}"
            cp "$backup" "$original"
            echo "  Restored $dir$original"
        fi
    done
    cd ..
done

# 5. Clear knowledge base (optional)
echo "[5/6] Clearing knowledge base..."
psql postgresql://ai:ai@localhost:5532/ai -c 'TRUNCATE TABLE "local_rag_documents_nomic-embed-text" RESTART IDENTITY CASCADE;' 2>/dev/null

# 6. Verify clean state
echo "[6/6] Verifying clean state..."
kubectl get pods  # Should show: No resources found
docker images | grep kube  # Should show: nothing

echo "=== Environment Reset Complete ==="
```

Save as `reset_environment.sh` and run: `bash reset_environment.sh`

---

## Getting Help

### Collecting Debug Information

When reporting issues, collect this information:

```bash
#!/bin/bash
# collect_debug_info.sh

echo "=== KubeLLM Debug Information ===" > debug_info.txt
echo "Generated: $(date)" >> debug_info.txt
echo "" >> debug_info.txt

echo "=== System Info ===" >> debug_info.txt
python3 --version >> debug_info.txt
pip show phidata | grep Version >> debug_info.txt
kubectl version --client >> debug_info.txt
minikube version >> debug_info.txt
docker --version >> debug_info.txt
echo "" >> debug_info.txt

echo "=== Minikube Status ===" >> debug_info.txt
minikube status -p lamap >> debug_info.txt
kubectl get nodes >> debug_info.txt
echo "" >> debug_info.txt

echo "=== Current Resources ===" >> debug_info.txt
kubectl get pods >> debug_info.txt
kubectl get services >> debug_info.txt
docker images | grep kube >> debug_info.txt
echo "" >> debug_info.txt

echo "=== Recent Errors ===" >> debug_info.txt
kubectl get events --sort-by='.lastTimestamp' | tail -10 >> debug_info.txt
echo "" >> debug_info.txt

echo "=== PostgreSQL ===" >> debug_info.txt
psql postgresql://ai:ai@localhost:5532/ai -c "SELECT COUNT(*) as doc_count FROM \"local_rag_documents_nomic-embed-text\"" >> debug_info.txt 2>&1
echo "" >> debug_info.txt

echo "Debug information saved to debug_info.txt"
```

Run: `bash collect_debug_info.sh` and share `debug_info.txt`

---

## Quick Fixes

| Problem | Quick Fix Command |
|---------|------------------|
| Minikube not running | `minikube start -p lamap` |
| Docker env not set | `eval $(minikube -p lamap docker-env)` |
| Pods stuck | `kubectl delete pods --all --force --grace-period=0` |
| Image not found | `docker build -t <image> . --no-cache` |
| Service not accessible | `minikube -p lamap service <service> --url` |
| Knowledge base empty | `curl -X POST localhost:8000/add_url/ -F "url=..."` |
| DB connection failed | `sudo systemctl restart postgresql` |
| Agent timeout | Reduce timeout or use faster model |
| Tests won't clean up | `bash reset_environment.sh` |
| Can't find pod name | `kubectl get pods -o name` |

---

## Additional Resources

- **Kubernetes Debugging**: https://kubernetes.io/docs/tasks/debug/
- **Minikube Troubleshooting**: https://minikube.sigs.k8s.io/docs/handbook/troubleshooting/
- **Docker Issues**: https://docs.docker.com/engine/troubleshooting/
- **pgvector Issues**: https://github.com/pgvector/pgvector/issues

---

## Still Stuck?

If you've tried everything and still have issues:

1. Run the health check script
2. Collect debug information
3. Check recent commits for breaking changes
4. Try a fresh Minikube cluster: `minikube delete -p lamap && minikube start -p lamap`
5. Try a simple test scenario first (e.g., `correct_app`)
6. Open an issue with debug_info.txt attached

Remember: The verification agent is always right. If it says FAILED, the test actually failed, even if the debug agent claimed success.
