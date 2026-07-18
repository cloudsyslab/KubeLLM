CASE: App Server Bound To Loopback Address

Case Setup:
- Server application handles HTTP requests on port 8765.
- The application binds to 127.0.0.1, so it is not reachable through the pod IP or Service.
- Kubernetes pod and service manifests deploy the container image and route traffic to port 8765.

Replication Steps:
1. Build the image from this directory.
2. Apply wrong_interface_bind_address.yaml and app_service.yaml.
3. Attempt an HTTP GET request through the pod IP or Service. The request should time out or be refused.

Solution Steps:
1. In server.py, replace 127.0.0.1 with 0.0.0.0.
2. Rebuild the container image.
3. Reapply the pod manifest so the corrected image is used.

Solution State:
- HTTP GET requests made to the pod IP on port 8765 return a 200 response.
