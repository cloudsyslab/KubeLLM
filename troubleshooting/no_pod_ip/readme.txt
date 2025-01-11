CASE: Pod IP, No Endpoints

Case Setup:
- Server application set to handle http requests on port 8765
- Dockerfile configured to install necessary packages for server application and expose the container port 8765
- Kubernetes pod configuration file to deploy the container image to the kubernetes cluster
- Kubernetes service configuration file to create a service to support the deployed pod
- Modified kube-controller-manager.yaml file that can be used to implement case issue

Replication Steps:
1. Replace the default kube-controller-manager.yaml file with the provided kube-controller-manager.yaml file. This file is typically located at the location /etc/kubernetes/manifests/kube-controller-manager.yaml
2. Wait for the new controller manager configuration file to be deployed to the cluster by the Kubelet daemon
3. Deploy the image created from the included Dockerfile to the Kubernetes cluster using the following command `kubectl apply -f path_to_directory/correct_app.yaml`
4. Deploy the service to the cluster using the command `kubectl apply -f path_to_directory/app-service.yaml`
5. Run the command `kubectl describe service app-service` to see that there are no endpoints listed for the service

Solution Steps:
1. Replace the kube-controller-manager.yaml file with a default kube-controller-manager configuration file (recommended) or if desired with a fixed version of the configuration file
2. Delete the correct_app.yaml and app-service.yaml deployments using the commands `kubectl delete -f path_to_directory/correct_app.yaml` and `kubectl delete -f path_to_directory/app-service.yaml`
3. Wait for the replacement kube-controller-manager to be applied to the cluster by the Kubelet daemon
3. Reapply the deployments for correct_app.yaml and app-service.yaml using the commands `kubectl apply -f path_to_directory/correct_app.yaml` and `kubectl apply -f path_to_directory/app-service.yaml`

Solution State:
- Endpoints will be listed for the app-service.yaml deployment when the `kubectl describe service app-service` command is run