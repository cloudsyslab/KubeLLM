# Test Scenarios Documentation

## Overview

KubeLLM-Minh includes 11 realistic Kubernetes troubleshooting scenarios designed to test LLM agents' ability to diagnose and fix common deployment issues. Each scenario represents a real-world problem that developers encounter.

**Location**: `debug_assistant_latest/troubleshooting/`

## Test Scenario Structure

Each test scenario directory contains:

```
<scenario_name>/
├── readme.txt              # Problem description and solution steps
├── config.json             # Agent configuration for this test
├── <scenario_name>.yaml    # Kubernetes deployment (with bugs)
├── server.py              # Sample application code (if applicable)
├── Dockerfile             # Container configuration (if applicable)
├── app_service.yaml       # Kubernetes service (if applicable)
└── backup_*.yaml          # Backup files (created during testing)
```

## Configuration File Format

Each `config.json` contains:

```json
{
  "test-name": "wrong_port",
  "test-directory": "~/KubeLLM/debug_assistant_latest/troubleshooting/wrong_port/",
  "yaml-file-name": "wrong_port.yaml",
  "minikube-profile": "lamap",

  "api-agent": {
    "model": "llama3.1:70b",
    "embedder": "nomic-embed-text",
    "knowledge": ["https://learnk8s.io/troubleshooting-deployments"]
  },

  "debug-agent": {
    "model": "gpt-4o",
    "instructions": [...],
    "guidelines": [...]
  },

  "verification-agent": {
    "model": "gpt-4o",
    "temperature": 0.3
  },

  "knowledge-prompt": {
    "problem-desc": "The pod is not accessible...",
    "system-prompt": "Analyze this Kubernetes issue...",
    "additional-directions": "Focus on port configuration..."
  },

  "debug-prompt": {
    "additional-directions": "Rebuild the container after fixing..."
  },

  "relevant-files": {
    "deployment": ["wrong_port.yaml"],
    "application": ["server.py"],
    "service": [],
    "dockerfile": true
  },

  "setup-commands": [
    "minikube -p lamap docker-env",
    "eval $(minikube -p lamap docker-env)",
    "docker build -t kube-wrong-port-app .",
    "kubectl apply -f wrong_port.yaml"
  ]
}
```

---

## Test Scenarios (Detailed)

### 1. wrong_port - Dockerfile Port Misconfiguration

**Location**: `troubleshooting/wrong_port/`

**Problem**: Dockerfile exposes the wrong port number

**Scenario**:
- Application listens on port 8765
- Dockerfile exposes port 8000
- Container port mismatch prevents access

**Files**:
- `server.py`: Python HTTP server listening on port 8765
- `Dockerfile`: `EXPOSE 8000` (wrong)
- `wrong_port.yaml`: Kubernetes deployment

**Root Cause**:
```dockerfile
# Dockerfile (BROKEN)
EXPOSE 8000  # Should be 8765
```

**Solution Steps**:
1. Identify port mismatch between server.py and Dockerfile
2. Modify Dockerfile to `EXPOSE 8765`
3. Rebuild container image: `docker build -t kube-wrong-port-app . --no-cache`
4. Delete deployment: `kubectl delete -f wrong_port.yaml`
5. Reapply: `kubectl apply -f wrong_port.yaml`

**Verification**:
```bash
kubectl get pods  # Should be Running
POD_IP=$(kubectl get pod <pod-name> -o jsonpath='{.status.podIP}')
curl $POD_IP:8765  # Should return HTTP response
```

**Learning Focus**:
- Container port configuration
- Dockerfile EXPOSE directive
- Image rebuild requirements

---

### 2. incorrect_selector - Service Selector Mismatch

**Location**: `troubleshooting/incorrect_selector/`

**Problem**: Service selector doesn't match pod labels

**Scenario**:
- Pod has label `app: correct-app`
- Service selector has `app: incorrect-selector`
- Service has no endpoints

**Files**:
- `incorrect_selector.yaml`: Pod deployment
- `app_service.yaml`: Service with wrong selector
- `server.py`, `Dockerfile`

**Root Cause**:
```yaml
# app_service.yaml (BROKEN)
spec:
  selector:
    app: incorrect-selector  # Should match pod label
```

**Solution Steps**:
1. Run `kubectl describe service app-service` → no endpoints
2. Get pod labels: `kubectl get pods --show-labels`
3. Identify mismatch between service selector and pod label
4. Modify `app_service.yaml` selector to match pod label
5. Delete and reapply both resources

**Verification**:
```bash
kubectl describe service app-service  # Should show endpoints
kubectl get endpoints app-service  # Should list pod IPs
```

**Learning Focus**:
- Kubernetes service discovery
- Label selectors
- Endpoint creation

---

### 3. readiness_failure - Readiness Probe Wrong Port

**Location**: `troubleshooting/readiness_failure/`

**Problem**: Readiness probe checks wrong port

**Scenario**:
- Application listens on port 8765
- Readiness probe checks port 8000
- Pod never becomes ready (0/1)

**Files**:
- `readiness_failure.yaml`: Deployment with wrong readiness probe

**Root Cause**:
```yaml
# readiness_failure.yaml (BROKEN)
readinessProbe:
  httpGet:
    path: /
    port: 8000  # Should be 8765
```

**Solution Steps**:
1. Check pod status: `kubectl get pods` → 0/1 READY
2. Describe pod: `kubectl describe pod <pod>` → readiness probe failed
3. Identify port mismatch in readiness probe
4. Modify YAML to correct port: 8765
5. Delete and reapply deployment

**Verification**:
```bash
kubectl get pods  # Should show 1/1 READY
kubectl describe pod <pod>  # Readiness probe succeeds
```

**Learning Focus**:
- Kubernetes readiness probes
- Pod readiness vs. running state
- Health check configuration

---

### 4. wrong_interface - Application Binds to Localhost

**Location**: `troubleshooting/wrong_interface/`

**Problem**: Application binds to 127.0.0.1 instead of 0.0.0.0

**Scenario**:
- Server listens on localhost (127.0.0.1)
- Kubernetes network cannot reach localhost
- Pod running but not accessible

**Files**:
- `server.py`: Python server with `server_address = ('localhost', 8765)`
- `wrong_interface.yaml`: Kubernetes deployment
- `app_service.yaml`: Service configuration

**Root Cause**:
```python
# server.py (BROKEN)
server_address = ('localhost', 8765)  # Should be ('0.0.0.0', 8765)
```

**Solution Steps**:
1. Test pod access: `curl <POD_IP>:8765` → timeout
2. Check container logs: May show server listening on 127.0.0.1
3. Identify localhost binding in server.py
4. Modify server.py to bind to `0.0.0.0`
5. Rebuild container image
6. Delete and reapply deployment

**Verification**:
```bash
POD_IP=$(kubectl get pod <pod> -o jsonpath='{.status.podIP}')
curl $POD_IP:8765  # Should succeed
minikube -p lamap service app-service --url  # Test service access
```

**Learning Focus**:
- Network interface binding
- Localhost vs. 0.0.0.0
- Container networking basics

---

### 5. port_mismatch - Service Port Doesn't Match Container Port

**Location**: `troubleshooting/port_mismatch/`

**Problem**: Service forwards to wrong container port

**Scenario**:
- Container exposes port 8765
- Service targetPort is 8000
- Traffic routed to wrong port

**Files**:
- `port_mismatch.yaml`: Deployment
- `app_service.yaml`: Service with wrong targetPort

**Root Cause**:
```yaml
# app_service.yaml (BROKEN)
spec:
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000  # Should be 8765
```

**Solution Steps**:
1. Test service access: Fails or times out
2. Check pod accessibility: `curl <POD_IP>:8765` → works
3. Identify service targetPort mismatch
4. Modify app_service.yaml targetPort to 8765
5. Delete and reapply service

**Verification**:
```bash
minikube -p lamap service app-service --url
curl <service-url>  # Should succeed
```

**Learning Focus**:
- Service port vs. targetPort
- Service to pod routing
- Port mapping in Kubernetes

---

### 6. no_pod_ip - Pod IP Assignment Issues

**Location**: `troubleshooting/no_pod_ip/`

**Problem**: Pod cannot obtain IP address

**Scenario**:
- Pod stuck in Pending or unusual network state
- Network plugin issues
- Configuration problems preventing IP assignment

**Solution Focus**:
- Check network plugin status
- Verify cluster networking
- Inspect pod events for IP assignment errors

**Learning Focus**:
- Kubernetes networking
- CNI plugins
- IP address management (IPAM)

---

### 7. environment_variable - Missing Required Environment Variables

**Location**: `troubleshooting/environment_variable/`

**Problem**: Application requires environment variables not set in deployment

**Scenario**:
- Application expects `MY_ENV_VAR`
- Deployment doesn't define environment variables
- Application crashes or fails to start

**Files**:
- `server.py`: References `os.environ['MY_ENV_VAR']`
- `environment_variable.yaml`: Deployment without env vars

**Root Cause**:
```python
# server.py (requires env var)
my_var = os.environ['MY_ENV_VAR']  # KeyError if not set
```

**Solution Steps**:
1. Check pod logs: `kubectl logs <pod>` → KeyError or similar
2. Identify missing environment variable in application code
3. Add environment variables to deployment YAML
4. Delete and reapply deployment

**Solution YAML**:
```yaml
spec:
  containers:
  - name: app
    env:
    - name: MY_ENV_VAR
      value: "some_value"
```

**Verification**:
```bash
kubectl logs <pod>  # No environment variable errors
kubectl get pods  # Running state
```

**Learning Focus**:
- Environment variable configuration
- ConfigMaps and Secrets (optional extension)
- Application configuration in Kubernetes

---

### 8. missing_dependency - Container Missing Required Packages

**Location**: `troubleshooting/missing_dependency/`

**Problem**: Dockerfile doesn't install required dependencies

**Scenario**:
- Application requires packages (e.g., pip packages)
- Dockerfile missing `RUN pip install ...`
- Container crashes on startup

**Files**:
- `server.py`: Imports packages like `requests`
- `Dockerfile`: Missing dependency installation

**Root Cause**:
```dockerfile
# Dockerfile (BROKEN) - missing dependencies
FROM python:3.9
COPY server.py .
CMD ["python", "server.py"]
# Missing: RUN pip install requests
```

**Solution Steps**:
1. Check pod logs: ImportError or ModuleNotFoundError
2. Identify missing packages from error messages
3. Add package installation to Dockerfile
4. Rebuild container image
5. Delete and reapply deployment

**Solution Dockerfile**:
```dockerfile
FROM python:3.9
RUN pip install requests
COPY server.py .
CMD ["python", "server.py"]
```

**Verification**:
```bash
kubectl logs <pod>  # No import errors
kubectl get pods  # Running state
```

**Learning Focus**:
- Dockerfile best practices
- Container dependency management
- Image building

---

### 9. liveness_probe - Liveness Probe Misconfiguration

**Location**: `troubleshooting/liveness_probe/`

**Problem**: Liveness probe fails, causing restart loops

**Scenario**:
- Liveness probe checks wrong endpoint or port
- Pod continuously restarts (CrashLoopBackOff)
- Application actually healthy

**Root Cause**:
```yaml
# liveness_probe.yaml (BROKEN)
livenessProbe:
  httpGet:
    path: /healthz  # Endpoint doesn't exist
    port: 8000      # Or wrong port
  initialDelaySeconds: 3
  periodSeconds: 3
```

**Solution Steps**:
1. Check pod status: CrashLoopBackOff or frequent restarts
2. Check restart count: `kubectl get pods`
3. Describe pod: Liveness probe failures in events
4. Modify liveness probe configuration
5. Delete and reapply deployment

**Verification**:
```bash
kubectl get pods  # Stable, no restarts
kubectl describe pod <pod>  # Liveness probe succeeds
```

**Learning Focus**:
- Liveness vs. readiness probes
- Restart policies
- Health check tuning (initialDelaySeconds, etc.)

---

### 10. volume_mount - Volume Mounting Problems

**Location**: `troubleshooting/volume_mount/`

**Problem**: Volume mount configuration errors

**Scenario**:
- Volume not properly defined
- Mount path conflicts
- Permission issues

**Common Issues**:
- Volume name mismatch between spec and volumeMounts
- Incorrect mount path
- Missing volume definition

**Root Cause Example**:
```yaml
# BROKEN
volumeMounts:
- name: data-volume
  mountPath: /app/data
# Missing volumes: section or name mismatch
```

**Solution**:
```yaml
spec:
  containers:
  - name: app
    volumeMounts:
    - name: data-volume
      mountPath: /app/data
  volumes:
  - name: data-volume
    emptyDir: {}
```

**Learning Focus**:
- Volume configuration
- Persistent storage
- Volume types (emptyDir, hostPath, PVC)

---

### 11. correct_app - Baseline Working Configuration

**Location**: `troubleshooting/correct_app/`

**Problem**: None (this is the working baseline)

**Purpose**:
- Reference for correct configuration
- Baseline for comparison
- Testing verification agents on successful deployments

**Expected Behavior**:
- All agents should recognize no issues
- Verification should succeed immediately
- Useful for testing false positive rates

---

## Test Execution

### Running a Single Test

```bash
cd ~/KubeLLM/debug_assistant_latest
python3 main.py troubleshooting/wrong_port/config.json allStepsAtOnce
```

### Running Multiple Tests

```bash
python3 kube_test.py
```

Edit `kube_test.py` to configure:
- Number of iterations: `numTests = 20`
- Test scenarios: `testEnvName` list
- Test modes: `testName` list

---

## Test Metrics

Each test execution records:

| Metric | Description |
|--------|-------------|
| test_case | Scenario name |
| model | LLM model used |
| agent_type | "debug" or "verification" |
| input_tokens | Tokens sent to LLM |
| output_tokens | Tokens generated by LLM |
| total_tokens | Sum of input + output |
| task_status | 1 (success), 0 (failure), -1 (error) |
| duration_s | Execution time in seconds |
| cost | Estimated cost in USD |

Stored in: `~/KubeLLM/token_metrics.db`

---

## Test Success Criteria

### For Debug Agent:
- ✅ Identifies root cause correctly
- ✅ Modifies correct files
- ✅ Executes appropriate kubectl commands
- ✅ Pod reaches Running state
- ✅ Reports accurate status token

### For Verification Agent:
- ✅ Independently confirms fix
- ✅ Pod is actually Running (not just claimed)
- ✅ Service endpoints exist (if applicable)
- ✅ Application is accessible (curl succeeds)
- ✅ Returns accurate verification token

---

## Common Test Failures and Causes

### 1. Agent Timeout (480s exceeded)
**Causes**:
- Using blocking commands (`kubectl logs -f`)
- Infinite loops in reasoning
- Very slow model responses

**Solutions**:
- Strengthen tool usage rules
- Use faster models
- Add explicit timeout instructions

### 2. Agent Reports Success but Verification Fails
**Causes**:
- Agent misinterprets command output
- Changes not fully applied
- Timing issues (changes need time to propagate)

**Solutions**:
- Trust verification agent (it's correct)
- Add wait times after kubectl apply
- Improve debug agent instructions

### 3. Container Build Failures
**Causes**:
- Minikube Docker environment not set
- Image name conflicts
- Build cache issues

**Solutions**:
- Always run: `eval $(minikube -p lamap docker-env)`
- Use `--no-cache` flag for rebuilds
- Clean up old images

### 4. Service Not Accessible
**Causes**:
- Not using minikube service command
- Wrong port in curl
- Service selector still wrong

**Solutions**:
- Use: `minikube -p lamap service <name> --url`
- Verify with curl to returned URL
- Double-check selector matches pod labels

---

## Adding New Test Scenarios

### Step-by-Step Guide

1. **Create Directory**:
   ```bash
   mkdir troubleshooting/new_scenario
   cd troubleshooting/new_scenario
   ```

2. **Create Application Files**:
   - `server.py` (with intentional bug)
   - `Dockerfile` (if needed)
   - `new_scenario.yaml` (Kubernetes deployment with bug)
   - `app_service.yaml` (if testing services)

3. **Write readme.txt**:
   ```
   CASE: Description

   Case Setup:
   - Component configurations

   Replication Steps:
   1. Deploy...
   2. Test...
   3. Observe failure...

   Solution Steps:
   1. Identify...
   2. Modify...
   3. Reapply...

   Solution State:
   - Expected working state
   ```

4. **Create config.json**:
   - Copy from similar scenario
   - Update test-name, test-directory, yaml-file-name
   - Customize problem-desc
   - Adjust relevant-files
   - Set appropriate setup-commands

5. **Test Manually**:
   ```bash
   python3 main.py troubleshooting/new_scenario/config.json allStepsAtOnce
   ```

6. **Add to Automated Testing**:
   - Update `kube_test.py` with new scenario name
   - Add backup/teardown logic if needed

7. **Document**:
   - Add to this file
   - Note any special requirements
   - Include common failure modes

---

## Test Scenario Difficulty Levels

### Easy (Good starting points)
- ✅ `correct_app` - No issues
- ✅ `readiness_failure` - Simple YAML fix
- ✅ `incorrect_selector` - Label matching

### Medium
- 🟨 `wrong_port` - Dockerfile + rebuild
- 🟨 `port_mismatch` - Service configuration
- 🟨 `environment_variable` - YAML modification

### Hard
- 🟥 `wrong_interface` - Application code + rebuild
- 🟥 `missing_dependency` - Dockerfile + dependencies
- 🟥 `liveness_probe` - Complex probe tuning

### Complex Multi-Step
- 🔴 `volume_mount` - Multiple configuration points
- 🔴 `no_pod_ip` - Network-level issues

---

## Test Scenario Best Practices

### For Creating New Scenarios:

1. **Realistic Problems**: Based on actual Kubernetes issues
2. **Single Root Cause**: One primary issue per scenario (may have secondary effects)
3. **Clear Documentation**: readme.txt should be complete
4. **Deterministic**: Same bug every time, reproducible
5. **Testable**: Clear success criteria
6. **Incremental Difficulty**: Start easy, add complexity

### For Running Tests:

1. **Clean State**: Ensure Minikube clean between tests
2. **Consistent Environment**: Same Minikube profile, same Docker env
3. **Backup Files**: Always backup before running
4. **Multiple Iterations**: Run 10-20 times for statistical significance
5. **Different Models**: Test with multiple LLMs
6. **Record Everything**: Save logs, metrics, observations

---

## Research Applications

### Comparing Models:
```python
models = ["gpt-4o", "o3-mini", "llama3.1:70b", "gemini-1.5-flash"]
scenarios = ["wrong_port", "incorrect_selector", "readiness_failure"]

for model in models:
    for scenario in scenarios:
        # Run test, collect metrics
        # Compare success rates, token usage, cost
```

### Comparing Architectures:
```python
modes = ["allStepsAtOnce", "stepByStep", "singleAgent"]

for mode in modes:
    # Run same scenarios
    # Compare effectiveness, efficiency
```

### Evaluating Verification:
```python
# Compare debug agent self-report vs. verification agent
# Measure false positive rate
# Identify scenarios where verification catches errors
```

---

## Summary: Quick Reference

| Scenario | Bug Type | Files to Fix | Rebuild? | Difficulty |
|----------|----------|--------------|----------|------------|
| wrong_port | Dockerfile | Dockerfile | Yes | Medium |
| incorrect_selector | Service | app_service.yaml | No | Easy |
| readiness_failure | Probe | YAML | No | Easy |
| wrong_interface | Application | server.py | Yes | Hard |
| port_mismatch | Service | app_service.yaml | No | Medium |
| no_pod_ip | Network | Various | Maybe | Hard |
| environment_variable | Config | YAML | No | Medium |
| missing_dependency | Dockerfile | Dockerfile | Yes | Hard |
| liveness_probe | Probe | YAML | No | Medium |
| volume_mount | Volume | YAML | No | Medium-Hard |
| correct_app | None | None | No | Easy |

---

## Troubleshooting Test Execution

See TROUBLESHOOTING.md for detailed guidance on common test execution issues.
