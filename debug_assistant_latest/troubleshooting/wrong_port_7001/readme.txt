CASE: Incorrect Port Exposed In Container

Case Setup:
- Server application handles HTTP requests on port 7001.
- Dockerfile exposes port 7000.
- Kubernetes pod manifest declares containerPort 7000.
- This workload has no Kubernetes Service; the case verifies direct pod behavior from inside the pod.

Replication Steps:
1. Build the image from this directory.
2. Apply wrong_port_7001.yaml to the Kubernetes cluster.
3. Attempt an HTTP GET request to the pod on the declared port.
4. The request should fail because the application listens on a different port.

Solution Steps:
1. Inspect server.py to find the actual listening port.
2. Update the pod manifest and Dockerfile to use port 7001.
3. Rebuild the image.
4. Delete and reapply wrong_port_7001.yaml.

Solution State:
- The pod is Ready, containerPort is 7001, and an in-pod HTTP request to localhost:7001 returns 200.
