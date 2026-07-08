CASE: Incorrect Selector

Case Setup:
- Server application set to handle http requests on port 8765
- Dockerfile configured to install necessary packages for server application and expose the container port 8765
- Kubernetes pod configuration file to deploy the container image to the kubernetes cluster
- Kubernetes service configuration file to create a service to support the deployed pod

Replication Steps:
1. In app_service.yaml check the spec->selector->app field to ensure that it does not match the pod label for the incorrect_selector.yaml pod manifest
2. Deploy the image created from the included Dockerfile to the Kubernetes cluster using the following command `kubectl apply -f path_to_directory/incorrect_selector.yaml`
3. Deploy the service to the cluster using the command `kubectl apply -f path_to_directory/app_service.yaml`
4. Run the command `kubectl describe service app-service` to see that there are no endpoints listed for the service

Solution Steps:
1. Modify the app_service.yaml file so that the spec->selector->app field matches the pod label for the incorrect_selector.yaml pod manifest
2. Delete the incorrect_selector.yaml and app_service.yaml resources using the commands `kubectl delete -f path_to_directory/incorrect_selector.yaml` and `kubectl delete -f path_to_directory/app_service.yaml`
3. Reapply the resources for incorrect_selector.yaml and app_service.yaml using the commands `kubectl apply -f path_to_directory/incorrect_selector.yaml` and `kubectl apply -f path_to_directory/app_service.yaml`

Solution State:
- Endpoints will be listed for the app-service service when the `kubectl describe service app-service` command is run
