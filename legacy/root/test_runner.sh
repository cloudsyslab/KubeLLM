#!/bin/bash

PROGRAM="${0##*/}"
TEST_NAME=""

usage() {
  echo "Usage: $PROGRAM TEST_NAME"
}

teardown() {
  if [[ "$TB_NAME" != "" ]]; then
    if [[ "$LOG_PATH" != "" ]]; then
      minikube delete -p ${TB_NAME} 2>&1 >> ${LOG_PATH}
    else
      minikube delete -p ${TB_NAME}
    fi
  fi
}

die() {
  teardown
  echo "$PROGRAM: $*" >&2
  exit 1
}

json_tb() {
  python3 -c "import sys, test; test.Test.model_validate_json(sys.stdin.read()).print_values()"
}

parse_options() {
  TEMP=$(getopt -o h --long help -- "$@")
  if [ $? != 0 ]; then exit 1; fi

  eval set -- "$TEMP"

  while true; do
    case "$1" in
      -h | --help)
        usage
	exit 0
	;;
      --)
        shift
	break
	;;
    esac
  done

  TEST_NAME="$1"
}

parse_options "$@"
LOG_PATH="/tmp/test-${TEST_NAME}-$(TZ='America/Chicago' date +%Z-%m_%d_%Y-%H_%M_%S).log"

# Ensure that the test setup directory exists
TEST_DIR="./troubleshooting/${TEST_NAME}"
GOOSE="${TEST_DIR}/goose.sh"
TESTBENCH="${TEST_DIR}/testbench.json"

if [[ "$TEST_NAME" == "" ]]; then
  die "No test specified"
elif ! [ -d "$TEST_DIR" ] || ! [ -f "$GOOSE" ] || ! [ -f "$TESTBENCH" ]; then
  die "Directory '$TEST_DIR' does not exist or goose/testbench files are missing"
fi

# Get testbench parameters
_parsed=(`json_tb < ${TESTBENCH}`)
if [ "$?" -ne 0 ]; then
  die "Failed to read testbench parameters"
fi
INVERT_TEST_RESULT=${_parsed[0]}
NUM_NODES=${_parsed[1]}
TB_NAME=${_parsed[2]}
unset _parsed

touch "$LOG_PATH"

# Make sure minikube uses kvm for creating nodes
minikube config set driver kvm2 >> ${LOG_PATH} 2>&1

# Create cluster
minikube start --driver=kvm2 --cni=calico -p ${TB_NAME} -n $(( ${NUM_NODES} + 1 )) >> $LOG_PATH 2>&1 || die "Failed to create testbench '$TB_NAME'"

# This was used when the test runner had the option to not initialize a cluster, so we could verify the cluster existed
#minikube -p ${TB_NAME} node list 2>&1 >/dev/null || NO_TEARDOWN=true die "Testbench '${TB_NAME}' does not exist"

# Apply test case to k8s cluster
echo -n "Test [${TEST_NAME}]... "
exit_code=( 0 )

statement=$(cd ${TEST_DIR}; . ../util/catch.sh && export -f catch && cluster_name=${TB_NAME} ./goose.sh 2>> $LOG_PATH)
if [ "$?" -ne 0 ]; then
  echo "ERROR :|"
  die "Test script ${TEST_NAME} failed to complete"
fi

python3 kubellm_json.py <<< "$statement" >> "$LOG_PATH" 2>&1
exit_code="$?"
if [ "$exit_code" -eq 1 ]; then
  echo "ERROR :|"
  die "KubeLLM failed to complete"
elif [ "$exit_code" -eq 2 ]; then
  echo "FAILED :("
elif [ "$exit_code" -eq 0 ]; then
  echo "PASSED :)"
fi

# Testing finished, teardown cluster
teardown || echo "Failed to delete testbench '$TB_NAME'"

exit $exit_code