CASE: Incorrect Port Exposed In Container

Case Setup:
- Server application handles HTTP requests on port 9090.
- Dockerfile exposes port 8080.
- Kubernetes pod manifest declares containerPort 8080.
- This workload has no Kubernetes Service; the case verifies direct pod behavior from inside the pod.

Replication Steps:
1. Build the image from this directory.
2. Apply wrong_port_9090.yaml to the Kubernetes cluster.
3. Attempt an HTTP GET request to the pod on the declared port.
4. The request should fail because the application listens on a different port.

Solution Steps:
1. Inspect server.py to find the actual listening port.
2. Update the pod manifest and Dockerfile to use port 9090.
3. Rebuild the image.
4. Delete and reapply wrong_port_9090.yaml.

Solution State:
- The pod is Ready, containerPort is 9090, and an in-pod HTTP request to localhost:9090 returns 200.
