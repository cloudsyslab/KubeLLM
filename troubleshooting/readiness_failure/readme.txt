CASE: Readiness Probe Failure

Case Setup:
- Kubernetes deployment configuration file to create a pod with a failing readiness probe

Replication Steps:
1. Check the deployment manifest file to ensure that the spec->readinessProbe->httpGet->path field is not set to /healthz
2. Apply the readiness_failure.yaml deployment to the cluster using the `kubectl apply -f path_to_directory/readiness_failure.yaml` command
3. Describe the deployed pod using the `kubectl describe 

Solution Steps:
1. Modify the readiness_failure.yaml file to set the spec->readinessProbe->httpGet->path field to be /healthz
2. Delete the readiness_failure deployment from the cluster using the `kubectl delete -f path_to_directory/readiness_failure.yaml` command
3. Reapply the readiness_failure deployment tp the cluster using the command `kubectl apply -f path_to_directory/readiness_failure.yaml`

Solution State:
- The Ready condition displayed when describing the pod will be listed with a True status