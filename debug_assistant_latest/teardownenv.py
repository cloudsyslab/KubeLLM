import kube_test
import sys

if (len(sys.argv) < 2):
    print ("provide the valid testcase name")
    sys.exit(1)

testEnvName = sys.argv[1]

if (testEnvName not in ["incorrect_selector", "port_mismatch", "readiness_failure", "wrong_interface", "wrong_port", "environment_variable", "liveness_probe", "missing_dependency", "port_mismatch_wrong_interface", "readiness_missing_dependency", "selector_env_variable", "resource_limits_oom"]):
    print ("provide the valid testcase name")
    sys.exit(1)

kube_test.tearDownEnviornment(testEnvName)
