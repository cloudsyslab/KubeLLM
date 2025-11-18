CASE: Port Mismatch + Wrong Interface Binding (Combined)

Case Setup:
- Server application listens on port 8765 and binds to localhost (127.0.0.1) instead of 0.0.0.0
- Service forwards traffic to port 8000 (wrong target port)
- Dockerfile correctly exposes port 8765
- TWO simultaneous issues that need to be fixed

Replication Steps:
1. Deploy the image created from the included Dockerfile to the Kubernetes cluster using `kubectl apply -f port_mismatch_wrong_interface.yaml`
2. Deploy the service using `kubectl apply -f app_service.yaml`
3. Check pod status: `kubectl get pods` - Pod should be Running
4. Test pod direct access: `curl <POD_IP>:8765` - This will FAIL due to localhost binding
5. Test service access: `minikube -p lamap service app-service --url` then `curl <url>` - This will ALSO fail

Problem Analysis:
- Issue 1: Application binds to 127.0.0.1 (localhost) instead of 0.0.0.0, preventing external access
- Issue 2: Service targetPort is 8000 but container listens on port 8765
- Both issues must be fixed for the application to work

Solution Steps:
1. Identify that the application binds to localhost by checking server.py code
2. Modify server.py to bind to 0.0.0.0 instead of localhost
3. Identify service targetPort mismatch by comparing app_service.yaml with actual container port
4. Modify app_service.yaml to set targetPort to 8765
5. Rebuild the container image: `docker build -t kube-port-mismatch-wrong-interface-app . --no-cache`
6. Delete existing deployments: `kubectl delete -f port_mismatch_wrong_interface.yaml` and `kubectl delete -f app_service.yaml`
7. Reapply both: `kubectl apply -f port_mismatch_wrong_interface.yaml` and `kubectl apply -f app_service.yaml`

Solution State:
- Pod is running and accessible at pod IP on port 8765
- Service correctly routes traffic to the pod
- `minikube service app-service --url` returns a working URL
- `curl <service-url>` returns the default HTML page
