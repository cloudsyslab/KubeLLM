CASE: App Port Service Port Mismatch

Case Setup:
- Server application set to handle http requests on port 8765
- Dockerfile configured to install necessary packages for server application and expose the container port 8765
- Kubernetes pod configuration file to deploy the container image to the kubernetes cluster
- Kubernetes service configuration file to create a service to support the deployed pod

Replication Steps:
1. Check the spec->containers->ports->containerPort field value in the port_mismatch.yaml file is different than the spec->ports->targetPort field value in the app_service.yaml file
2. Deploy the image created from the included Dockerfile to the Kubernetes cluster using the following command `kubectl apply -f path_to_directory/port_mismatch.yaml`
3. Deploy the service to the cluster using the command `kubectl apply -f path_to_directory/app_service.yaml`
4. Run the command `kubectl describe service app-service` to see that there are no endpoints listed for the service

Solution Steps:
1. Modify either the described targetPort or containerPort field to match the port that the app is listening on. Which one to modify depends on which one (or possibly both) is the wrong port
2. Delete the port_mismatch.yaml and app_service.yaml deployments using the commands `kubectl delete -f path_to_directory/port_mismatch.yaml` and `kubectl delete -f path_to_directory/app_service.yaml`
3. Reapply the deployments for port_mismatch.yaml and app_service.yaml using the commands `kubectl apply -f path_to_directory/port_mismatch.yaml` and `kubectl apply -f path_to_directory/app_service.yaml`

Solution State:
- Endpoints will be listed for the app-service.yaml deployment when the `kubectl describe service app-service` command is run
