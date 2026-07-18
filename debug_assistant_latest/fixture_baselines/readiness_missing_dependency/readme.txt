CASE: Readiness Probe Failure + Missing Dependency (Combined)

Case Setup:
- Application requires the 'requests' Python package but Dockerfile doesn't install it
- Application crashes on startup with ImportError
- Readiness probe is configured but fails because the application never starts successfully
- TWO related issues: missing dependency causes app crash, which causes readiness failure

Replication Steps:
1. Build and deploy: `docker build -t kube-readiness-missing-dep-app .` then `kubectl apply -f readiness_missing_dependency.yaml`
2. Check pod status: `kubectl get pods` - Pod shows 0/1 READY and may show CrashLoopBackOff or Running but not ready
3. Check pod logs: `kubectl logs <pod-name>` - Shows ImportError for 'requests' module
4. Check pod events: `kubectl describe pod <pod-name>` - Shows readiness probe failures

Problem Analysis:
- Issue 1 (Root Cause): Dockerfile missing `RUN pip install requests`, causing ImportError
- Issue 2 (Symptom): Readiness probe fails because application never starts successfully
- The readiness probe itself is correctly configured, but app can't respond because it crashes

Solution Steps:
1. Check pod logs to identify the ImportError for 'requests' module
2. Examine Dockerfile and identify missing pip install command
3. Modify Dockerfile to add: `RUN pip install requests`
4. Rebuild container image: `docker build -t kube-readiness-missing-dep-app . --no-cache`
5. Delete existing pod: `kubectl delete -f readiness_missing_dependency.yaml`
6. Reapply: `kubectl apply -f readiness_missing_dependency.yaml`
7. Wait for pod to start and become ready (1/1)

Solution State:
- Pod status shows 1/1 READY and Running
- Readiness probe succeeds
- Application successfully starts and responds to HTTP requests
- `kubectl logs <pod-name>` shows "Server running" message without errors
