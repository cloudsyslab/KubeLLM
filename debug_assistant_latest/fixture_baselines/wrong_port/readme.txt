CASE: Incorrect Port Declared For Deployment Workload

Case Setup:
- Server application handles HTTP requests on port 8765.
- Dockerfile exposes port 8000.
- Kubernetes Deployment manifest declares containerPort 8000.
- This workload has no Kubernetes Service; the case verifies direct workload behavior from inside the selected pod.

Replication Steps:
1. Build the image from this directory.
2. Apply wrong_port.yaml to the Kubernetes cluster.
3. Attempt an HTTP GET request to the workload on the declared port.
4. The request should fail because the application listens on a different port.

Solution Steps:
1. Inspect server.py to find the actual listening port.
2. Update the Deployment manifest and Dockerfile to use port 8765.
3. Rebuild the image.
4. Reapply wrong_port.yaml.

Solution State:
- The Deployment is available, the live pod template containerPort is 8765, and an in-pod HTTP request to localhost:8765 returns 200.
