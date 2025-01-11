CASE: Incorrect Port Exposed In Container Dockerfile

Case Setup:
- Server application set to handle http requests on port 8765 and on the localhost interface
- Dockerfile configured to install necessary packages for server application and expose the container port 8000
- Kubernetes pod configuration file to deploy the container image to the kubernetes cluster

Replication Steps:
1. Deploy the image created from the included Dockerfile to the Kubernetes cluster using the following command `kubectl apply -f path_to_directory/wrong_port.yaml`
2. Attempt to make an http GET request to the application at the IP address associated with the pod and on the port the application is running on. This can be done using the BASH command `curl podIP:port`
3. The GET request should result in a timeout as the incorrect container port is being exposed.

Solution Steps:
1. Modify the Dockerfile to expose the correct port on the container that the app server is listening on.
2. Rebuild the container image for the application and force rebuild to ensure that the image is rebuilt from the directory, and does not use cached layers as this may not apply the changes correctly to the image
3. Delete the current application deployment from the cluster using the command `kubectl delete -f path_to_directory/wrong_port.yaml`
4. Reapply the application deployment to the cluster using the command `kubectl apply -f path_to_directory/wrong_port.yaml`

Solution State:
- Any http GET requests made to the pod IP on the listening port will return a default html page