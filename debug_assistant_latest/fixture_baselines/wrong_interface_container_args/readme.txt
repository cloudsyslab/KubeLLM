CASE: App Server Host Configured Through Wrong Container Argument

Case Setup:
- Server application handles HTTP requests on port 8765.
- The application reads the host interface from the --host command-line argument.
- The pod manifest passes --host 127.0.0.1, so the app is not reachable through the pod IP or Service.

Replication Steps:
1. Build the image from this directory.
2. Apply wrong_interface_container_args.yaml and app_service.yaml.
3. Attempt an HTTP GET request through the pod IP or Service. The request should time out or be refused.

Solution Steps:
1. In wrong_interface_container_args.yaml, replace the --host value 127.0.0.1 with 0.0.0.0.
2. Reapply the pod manifest so the corrected argument is used.

Solution State:
- HTTP GET requests made to the pod IP on port 8765 return a 200 response.
