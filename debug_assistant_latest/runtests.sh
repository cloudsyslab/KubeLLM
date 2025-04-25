python3 main.py ./troubleshooting/wrong_interface/config_step.json > toolsAgent.log
python3 teardownenv.py wrong_interface

python3 main.py ./troubleshooting/wrong_port/config_step.json >> toolsAgent.log
python3 teardownenv.py wrong_port

python3 main.py ./troubleshooting/incorrect_selector/config_step.json >> toolsAgent.log
python3 teardownenv.py incorrect_selector

python3 main.py ./troubleshooting/port_mismatch/config_step.json >> toolsAgent.log
python3 teardownenv.py port_mismatch

python3 main.py ./troubleshooting/readiness_failure/config_step.json >> toolsAgent.log
python3 teardownenv.py readiness_failure

