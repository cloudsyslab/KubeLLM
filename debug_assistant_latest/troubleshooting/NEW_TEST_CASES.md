# New Combined and Advanced Test Cases

## Overview

Four new test scenarios have been added to increase the complexity and realism of the KubeLLM testing framework. These test cases combine multiple issues or introduce new failure modes.

## Test Case Summary

### 1. port_mismatch_wrong_interface (Combined)
**Difficulty**: 🔴 Very Hard

**Issues**:
- Application binds to localhost (127.0.0.1) instead of 0.0.0.0
- Service targetPort (8000) doesn't match container port (8765)

**Files to Fix**:
- `server.py` - Change localhost to 0.0.0.0
- `app_service.yaml` - Change targetPort to 8765
- Rebuild container required

**Learning Focus**:
- Network interface binding
- Service port configuration
- Multiple simultaneous network issues
- Testing both pod-direct and service access

**Challenge**: Agent must identify TWO separate networking issues and fix both correctly.

---

### 2. readiness_missing_dependency (Combined)
**Difficulty**: 🟥 Hard

**Issues**:
- Dockerfile missing `RUN pip install requests`
- Application crashes with ImportError
- Readiness probe fails because app never starts

**Files to Fix**:
- `Dockerfile` - Add pip install requests
- Rebuild container required

**Learning Focus**:
- Distinguishing root cause from symptoms
- Container dependency management
- Readiness probe behavior with crashing apps
- Reading and interpreting Python stack traces

**Challenge**: Agent must recognize that readiness failure is a symptom, not the root cause. The real issue is missing dependencies.

---

### 3. selector_env_variable (Combined)
**Difficulty**: 🟥 Hard

**Issues**:
- Pod crashes due to missing APP_MESSAGE environment variable
- Service selector doesn't match pod labels

**Files to Fix**:
- `selector_env_variable.yaml` - Add env var definition
- `app_service.yaml` - Fix selector to match pod label
- No rebuild required (YAML-only fixes)

**Learning Focus**:
- Multiple independent issues
- Environment variable configuration
- Service discovery via label selectors
- Endpoint validation

**Challenge**: TWO completely independent issues. Even if one is fixed, the other prevents full functionality.

---

### 4. resource_limits_oom (New Scenario)
**Difficulty**: 🟨 Medium-Hard

**Issues**:
- Memory limit set to 50Mi (too restrictive)
- Application needs ~80MB to start
- Pod gets OOMKilled by Kubernetes
- CrashLoopBackOff state

**Files to Fix**:
- `resource_limits_oom.yaml` - Increase memory limit to 128Mi or 256Mi
- No rebuild required

**Learning Focus**:
- Resource limits and requests
- OOMKilled termination reason
- Reading pod events for termination details
- Appropriate resource sizing

**Challenge**: Agent must identify OOMKilled in events, understand resource limits, and choose appropriate new limit value.

---

## Testing Workflow

### For Combined Cases (1-3)

```bash
# 1. port_mismatch_wrong_interface
cd ~/KubeLLM/debug_assistant_latest
python3 main.py troubleshooting/port_mismatch_wrong_interface/config_step.json allStepsAtOnce

# 2. readiness_missing_dependency
python3 main.py troubleshooting/readiness_missing_dependency/config_step.json allStepsAtOnce

# 3. selector_env_variable
python3 main.py troubleshooting/selector_env_variable/config_step.json allStepsAtOnce
```

### For Resource Limits Case (4)

```bash
# 4. resource_limits_oom
python3 main.py troubleshooting/resource_limits_oom/config_step.json allStepsAtOnce
```

---

## Success Criteria

### port_mismatch_wrong_interface
✅ Pod is Running
✅ Direct pod access works: `curl <POD_IP>:8765`
✅ Service access works: `minikube service app-service --url` then curl
✅ Both server.py and app_service.yaml modified correctly

### readiness_missing_dependency
✅ Pod is Running with 1/1 ready
✅ No ImportError in logs
✅ Readiness probe passes
✅ Dockerfile has pip install requests

### selector_env_variable
✅ Pod is Running without CrashLoopBackOff
✅ No KeyError in logs for APP_MESSAGE
✅ Service has endpoints listed
✅ Both YAML files modified correctly

### resource_limits_oom
✅ Pod is Running without restarts
✅ No OOMKilled events
✅ Memory limit increased to reasonable value (128Mi+)
✅ Application responds to requests

---

## Expected Agent Behavior

### Multi-Issue Diagnosis
Agents should:
1. Identify ALL issues, not just the first one found
2. Understand relationships between issues (root cause vs. symptom)
3. Fix issues in logical order
4. Verify all issues resolved before reporting success

### Common Pitfalls
- **Fixing only one issue in combined tests** - Both must be fixed
- **Treating symptoms instead of root causes** - E.g., trying to fix readiness probe config when the real issue is missing dependencies
- **Not rebuilding containers after code/Dockerfile changes**
- **Setting resource limits too high** - Should be reasonable (128-256Mi, not 1Gi)

---

## Verification Agent Behavior

Verification agents should:
- **Test multiple aspects**: Pod status, logs, service endpoints, actual HTTP access
- **Not rely on debug agent claims**: Independently verify all fixes
- **Check for all issues**: In combined tests, verify both issues are resolved
- **Use appropriate verification methods**:
  - For resource issues: Check pod events and restart count
  - For network issues: Test both direct and service access
  - For dependencies: Check logs for import errors
  - For env vars: Check logs for KeyError

---

## Difficulty Progression

| Test Case | Difficulty | Issues | Rebuild? | Reason |
|-----------|-----------|--------|----------|---------|
| readiness_missing_dependency | 🟥 Hard | 2 (related) | Yes | Root cause vs. symptom |
| selector_env_variable | 🟥 Hard | 2 (independent) | No | Multiple independent fixes |
| port_mismatch_wrong_interface | 🔴 Very Hard | 2 (independent) | Yes | Complex networking, rebuild |
| resource_limits_oom | 🟨 Medium-Hard | 1 | No | New concept (OOM), simple fix |

---

## Research Applications

These test cases are valuable for:

1. **Multi-Issue Diagnosis**: Testing if agents can identify multiple problems
2. **Causal Reasoning**: Distinguishing symptoms from root causes
3. **Resource Management**: Understanding Kubernetes resource limits
4. **Complexity Handling**: Performance on more realistic scenarios
5. **Verification Robustness**: Testing if verification catches partial fixes

---

## File Structure

Each test case includes:
```
<test_name>/
├── readme.txt                 # Problem description & solution
├── config_step.json          # Agent configuration
├── <test_name>.yaml          # Kubernetes deployment (with bugs)
├── server.py                 # Application code
├── Dockerfile                # Container config
└── app_service.yaml          # Service config (if applicable)
```

---

## Adding to Automated Tests

To add these to `kube_test.py`:

```python
for testEnvName in [
    "port_mismatch_wrong_interface",
    "readiness_missing_dependency",
    "selector_env_variable",
    "resource_limits_oom"
]:
    configFile = f"{filepath}/{testEnvName}/config_step.json"
    # Run tests...
```

You'll need to add teardown logic for each test case in the `tearDownEnviornment()` function.

---

## Future Test Case Ideas

Potential future combinations:
- `liveness_probe + volume_mount` - Liveness fails due to missing volume
- `wrong_port + missing_dependency + incorrect_selector` - Triple issue
- `resource_limits_cpu` - CPU throttling causing timeouts
- `image_pull_policy` - Wrong policy causing old image usage
- `network_policy` - Pods can't communicate due to network policy
- `init_container_failure` - Main container never starts

---

Created: 2025-01-XX
Author: Claude AI Assistant
Purpose: Enhanced testing complexity for KubeLLM research framework
