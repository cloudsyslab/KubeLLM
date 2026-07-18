CASE: Resource Limits - Out of Memory (OOMKilled)

Case Setup:
- Application is a simple Python HTTP server
- Pod has memory limit set to 50Mi (very restrictive)
- Application tries to allocate more memory than the limit allows
- Pod gets OOMKilled (Out of Memory) by Kubernetes

Replication Steps:
1. Build and deploy: `docker build -t kube-resource-limits-app .` then `kubectl apply -f resource_limits_oom.yaml`
2. Check pod status: `kubectl get pods` - Pod shows CrashLoopBackOff or Error status
3. Check pod events: `kubectl describe pod <pod-name>` - Shows "OOMKilled" in events
4. Check restart count: Pod restarts multiple times

Problem Analysis:
- Memory limit is set to 50Mi in the pod spec (resources.limits.memory)
- The application's memory usage exceeds this limit
- Kubernetes OOM killer terminates the container
- Pod enters CrashLoopBackOff as it keeps getting killed

Solution Steps:
1. Check pod status and observe CrashLoopBackOff
2. Run `kubectl describe pod <pod-name>` to see OOMKilled in the events
3. Identify that memory limit is too restrictive (50Mi)
4. Modify resource_limits_oom.yaml to increase memory limit to 128Mi or 256Mi
5. Delete existing pod: `kubectl delete -f resource_limits_oom.yaml`
6. Reapply: `kubectl apply -f resource_limits_oom.yaml`
7. Verify pod starts and stays running

Solution State:
- Pod status shows Running with 1/1 ready
- No OOMKilled events in pod description
- Pod does not restart
- Application is accessible and responds to HTTP requests
