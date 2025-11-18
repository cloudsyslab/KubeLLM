CASE: Incorrect Service Selector + Missing Environment Variable (Combined)

Case Setup:
- Application requires an environment variable APP_MESSAGE that is not defined in the deployment
- Service selector label doesn't match the pod's label
- TWO independent issues: service can't find pod, AND pod crashes due to missing env var

Replication Steps:
1. Build and deploy: `docker build -t kube-selector-env-app .` then `kubectl apply -f selector_env_variable.yaml`
2. Deploy service: `kubectl apply -f app_service.yaml`
3. Check pod status: `kubectl get pods` - Pod may show CrashLoopBackOff
4. Check pod logs: `kubectl logs <pod-name>` - Shows KeyError for 'APP_MESSAGE'
5. Check service: `kubectl describe service app-service` - Shows no endpoints
6. Check endpoints: `kubectl get endpoints app-service` - Should be empty

Problem Analysis:
- Issue 1: Pod crashes immediately due to missing APP_MESSAGE environment variable (KeyError)
- Issue 2: Service selector is 'app: wrong-selector' but pod has label 'app: selector-env-app'
- Even if env var was fixed, service still wouldn't route traffic due to selector mismatch
- Both issues must be fixed independently

Solution Steps:
1. Check pod logs to identify missing environment variable (APP_MESSAGE)
2. Check service and pod labels to identify selector mismatch
3. Modify selector_env_variable.yaml to add environment variable:
   env:
   - name: APP_MESSAGE
     value: "Hello from selector_env_variable test!"
4. Modify app_service.yaml to fix selector to match pod label:
   selector:
     app: selector-env-app
5. Delete existing resources: `kubectl delete -f selector_env_variable.yaml` and `kubectl delete -f app_service.yaml`
6. Reapply both: `kubectl apply -f selector_env_variable.yaml` and `kubectl apply -f app_service.yaml`
7. Verify pod is running and service has endpoints

Solution State:
- Pod is Running with 1/1 ready
- Pod logs show no KeyError
- Service has endpoints listed
- Application is accessible through the service
- `kubectl describe service app-service` shows pod IP as endpoint
