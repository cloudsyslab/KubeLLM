from main import allStepsAtOnce, stepByStep, singleAgentApproach, conversationAgentApproach
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import shutil
import os
import subprocess
import datetime
import re
def aftermathTestOfActions(testEnvName):
    """ RETURN THE RESPONSE TO BE : FAILED TO TEST POD"""
    if testEnvName == "wrong_port":

        try:
            #Restart the container to pick up new changes

            #Tear down the Container
            subprocess.run("docker stop wrong_port_app", shell=True, check=True)
            subprocess.run("docker rm wrong_port_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-wrong-port-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-wrong-port-app", shell=True, check=True)

            #Build Container
            subprocess.run("docker build -t kube-wrong-port-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/wrong_port/", shell=True, check=True)
            subprocess.run("docker tag kube-wrong-port-app marioutsa/kube-wrong-port-app", shell=True, check=True)
            subprocess.run("docker run -d -p 8765:8765 --name wrong_port_app -v /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/wrong_port/server.py:/app/server.py marioutsa/kube-wrong-port-app", shell=True, check=True)

            time.sleep(5)
            res = subprocess.run(f"curl 10.242.128.44:8765", shell=True, check=True)
            returnCode = True if res.returncode == 0 else False
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "wrong_interface":

        try:
            #Restart the container to pick up new changes

            #Tear down the Container
            subprocess.run("docker stop wrong_interface_app", shell=True, check=True)
            subprocess.run("docker rm wrong_interface_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-wrong-interface-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-wrong-interface-app", shell=True, check=True)

            #Build Container
            subprocess.run("docker build -t kube-wrong-interface-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/wrong_interface/", shell=True, check=True)
            subprocess.run("docker tag kube-wrong-interface-app marioutsa/kube-wrong-interface-app", shell=True, check=True)
            subprocess.run("docker run -d -p 8765:8765 --name wrong_interface_app marioutsa/kube-wrong-interface-app", shell=True, check=True)
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/wrong_interface/wrong_interface.yaml", shell=True, check=True)

            time.sleep(5)
            res = subprocess.run(f"curl 10.242.128.44:8765", shell=True, check=True)
            returnCode = True if res.returncode == 0 else False
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "readiness_failure":
        try:
            res = subprocess.run(f"cat /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/readiness_failure/readiness_failure.yaml", shell=True, check=True, capture_output=True, text=True )
            res = str(res.stdout)
            returnCode = True if 'path: /healthz' in res else False 
            #Artificially wait or else google will block - this test runs faster than the others
            time.sleep(30)           
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "port_mismatch":
        try:
            res = subprocess.run(f"kubectl describe service app-service", shell=True, check=True, capture_output=True, text=True )
            #res = subprocess.run(f"cat /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/readiness_failure/readiness_failure.yaml", shell=True, check=True, capture_output=True, text=True )
            res = str(res.stdout)
            returnCode = True if ":8765" in res or ":8000" in res else False
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "incorrect_selector":
        try:
            res = subprocess.run(f"kubectl describe service app-service", shell=True, check=True, capture_output=True, text=True )
            #res = subprocess.run(f"cat /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/readiness_failure/readiness_failure.yaml", shell=True, check=True, capture_output=True, text=True )
            res = str(res.stdout)
            print(res)
            returnCode = True if ":8765" in res or ":8000" in res else False
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "volume_mount":
        try:
            #Tear down the Container
            subprocess.run("docker stop volume_mount_app", shell=True, check=True)
            subprocess.run("docker rm volume_mount_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-volume-mount-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-volume-mount-app", shell=True, check=True)

            #Build Container
            subprocess.run("docker build -t kube-volume-mount-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/volume_mount/", shell=True, check=True)
            subprocess.run("docker tag kube-volume-mount-app marioutsa/kube-volume-mount-app", shell=True, check=True)
            subprocess.run("docker run -d -p 8765:8765 --name volume_mount_app marioutsa/kube-volume-mount-app", shell=True, check=True)
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/volume_mount/volume_mount.yaml", shell=True, check=True)
        
            time.sleep(5)
            res = subprocess.run("curl 127.0.0.1:8765/log", shell=True, capture_output=True, text=True)
            res = str(res.stdout)
            returnCode = True if 'Application started' in res else False 
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "misspelling":
        try:
            # Tear down existing container
            subprocess.run("docker stop liveness_app", shell=True, check=True)
            subprocess.run("docker rm liveness_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-liveness-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-liveness-app", shell=True, check=True)

            # Build and tag container
            subprocess.run("docker build -t kube-liveness-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/misspelling/", shell=True, check=True)
            subprocess.run("docker tag kube-liveness-app marioutsa/kube-liveness-app", shell=True, check=True)
            
            # Run container
            subprocess.run("docker run -d -p 8765:8765 --name liveness_app marioutsa/kube-liveness-app", shell=True, check=True)
            
            time.sleep(5)
            
            # Apply Kubernetes configuration
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/misspelling/misspelling.yaml", shell=True, check=True)
            
            res = subprocess.run(f"cat /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/misspelling/misspelling.yaml", shell=True, check=True, capture_output=True, text=True )
            res = str(res.stdout)
            returnCode = True if 'image: marioutsa/kube-liveness-app' in res else False 
            return returnCode
        except Exception as e:
            print(e)
    elif testEnvName == "missing_dependency":
        try:
            # Tear down existing container
            subprocess.run("docker stop kube_missing_dependency_app", shell=True, check=True)
            subprocess.run("docker rm kube_missing_dependency_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-missing-dependency-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-missing-dependency-app", shell=True, check=True)

            # Build and tag container
            subprocess.run("docker build -t kube-missing-dependency-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/missing_dependency/", shell=True, check=True)
            subprocess.run("docker tag kube-missing-dependency-app marioutsa/kube-missing-dependency-app", shell=True, check=True)
            
            # Run container
            subprocess.run("docker run -d -p 8765:8765 --name kube_missing_dependency_app marioutsa/kube-missing-dependency-app", shell=True, check=True)
            
            time.sleep(5)
            
            # Apply Kubernetes configuration
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/missing_dependency/missing_dependency.yaml", shell=True, check=True)
            
            res = subprocess.run(f"kubectl get pods kube-missing-dependency", shell=True, check=True, capture_output=True, text=True )
            res = str(res.stdout)
 
            returnCode = True if 'Running' in res else False 
            return returnCode

        except Exception as e:
            print(e)
    elif testEnvName == "liveness_probe":
        try:
            # Tear down existing container
            subprocess.run("docker stop liveness_app", shell=True, check=True)
            subprocess.run("docker rm liveness_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-liveness-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-liveness-app", shell=True, check=True)

            # Build and tag container
            subprocess.run("docker build -t kube-liveness-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/liveness_probe/", shell=True, check=True)
            subprocess.run("docker tag kube-liveness-app marioutsa/kube-liveness-app", shell=True, check=True)
            
            # Run container
            subprocess.run("docker run -d -p 8765:8765 --name liveness_app marioutsa/kube-liveness-app", shell=True, check=True)
            
            time.sleep(5)
            
            # Apply Kubernetes configuration
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/liveness_probe/liveness_probe.yaml", shell=True, check=True)
            
            # Test if liveness probe endpoint is accessible
            time.sleep(30)  # Wait for initial delay period
            res = subprocess.run("curl 127.0.0.1:8765/health", shell=True, capture_output=True, text=True)
            
            return "OK" in res.stdout
        except Exception as e:
            print(e)
    elif testEnvName == "crashloop":
        try:
            # Tear down existing container
            subprocess.run("docker stop crashloop_app", shell=True, check=True)
            subprocess.run("docker rm crashloop_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-crashloop-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-crashloop-app", shell=True, check=True)

            # Build and tag container
            subprocess.run("docker build -t kube-crashloop-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/crashloop/", shell=True, check=True)
            subprocess.run("docker tag kube-crashloop-app marioutsa/kube-crashloop-app", shell=True, check=True)
            
            # Run container
            subprocess.run("docker run -d -p 8765:8765 --name crashloop_app marioutsa/kube-crashloop-app", shell=True, check=True)
            
            time.sleep(5)
            
            # Apply Kubernetes configuration
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/crashloop/crashloop.yaml", shell=True, check=True)
            
            # Check if pod enters CrashLoopBackOff state
            time.sleep(10)
            pod_status = subprocess.run("kubectl get pod -l app=crashloop -o jsonpath='{.items[0].status.containerStatuses[0].state.waiting.reason}'", shell=True, capture_output=True, text=True)
            
            return "CrashLoopBackOff" in pod_status.stdout
        except Exception as e:
            print(e)
    elif testEnvName == "environment_variable":
        try:
            #Tear down the Container
            subprocess.run("docker stop environment_variable_app", shell=True, check=True)
            subprocess.run("docker rm environment_variable_app", shell=True, check=True)
            subprocess.run("docker rmi -f marioutsa/kube-env-missing-app", shell=True, check=True)
            subprocess.run("docker rmi -f kube-env-missing-app", shell=True, check=True)
            #Build Container
            subprocess.run("docker build -t kube-env-missing-app /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/environment_variable/", shell=True, check=True)
            subprocess.run("docker tag kube-env-missing-app marioutsa/kube-env-missing-app", shell=True, check=True)
            subprocess.run("docker run -d -p 8765:8765 --name environment_variable_app marioutsa/kube-env-missing-app", shell=True, check=True)
            subprocess.run("kubectl apply -f /home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/environment_variable/environment_variable.yaml", shell=True, check=True)
        
            time.sleep(5)
            res = subprocess.run("kubectl exec -it kube-env-missing -- printenv APP_MODE", shell=True, capture_output=True, text=True)
            res = str(res.stdout)
            returnCode = True if len(res) > 0 else False 
            return returnCode
        except Exception as e:
            print(e)



def backupEnviornment(testEnvName):
    if testEnvName == "wrong_interface":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "readiness_failure":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
    elif testEnvName == "wrong_port":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "port_mismatch":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/app_service.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_app_service.yaml")
    elif testEnvName == "incorrect_selector":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/app_service.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_app_service.yaml")
    elif testEnvName == "crashloop":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "liveness_probe":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "missing_dependency":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "misspelling":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "volume_mount":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "environment_variable":
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile")

def tearDownEnviornment(testEnvName):

    if testEnvName == "wrong_interface":
        subprocess.run("docker stop wrong_interface_app", shell=True, check=True)
        subprocess.run("docker rm wrong_interface_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-wrong-interface-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-wrong-interface-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")        

        try:
            subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
        except:
            pass

    elif testEnvName == "readiness_failure":
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)

    elif testEnvName == "wrong_port":
        subprocess.run("docker stop wrong_port_app", shell=True, check=True)
        subprocess.run("docker rm wrong_port_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-wrong-port-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-wrong-port-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")        

        try:
            subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
        except:
            pass
            
    elif testEnvName == "port_mismatch":
        subprocess.run("docker stop port_mismatch_app", shell=True, check=True)
        subprocess.run("docker rm port_mismatch_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-port-mismatch-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-port-mismatch-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/app_service.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")   
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_app_service.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/app_service.yaml")     
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)

    elif testEnvName == "incorrect_selector":

        subprocess.run("docker stop incorrect_selector_app", shell=True, check=True)
        subprocess.run("docker rm incorrect_selector_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-incorrect-selector-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-incorrect-selector-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/app_service.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")   
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_app_service.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/app_service.yaml")     
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)
    
    
    elif testEnvName == "crashloop":
        subprocess.run("docker stop crashloop_app", shell=True, check=True)
        subprocess.run("docker rm crashloop_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-crashloop-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-crashloop-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")   


    elif testEnvName == "liveness_probe":
        subprocess.run("docker stop liveness_app", shell=True, check=True)
        subprocess.run("docker rm liveness_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-liveness-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-liveness-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")   
    elif testEnvName == "missing_dependency":
        subprocess.run("docker stop kube_missing_dependency_app", shell=True, check=True)
        subprocess.run("docker rm kube_missing_dependency_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-missing-dependency-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-missing-dependency-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")   

    elif testEnvName == "misspelling":
        subprocess.run("docker stop liveness_app", shell=True, check=True)
        subprocess.run("docker rm liveness_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-liveness-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-liveness-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")   

    elif testEnvName == "volume_mount":
        subprocess.run("docker stop volume_mount_app", shell=True, check=True)
        subprocess.run("docker rm volume_mount_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-volume-mount-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-volume-mount-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

    elif testEnvName == "environment_variable":
        subprocess.run("docker stop environment_variable_app", shell=True, check=True)
        subprocess.run("docker rm environment_variable_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-env-missing-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-env-missing-app", shell=True, check=True)

        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")
        os.remove(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")

        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_yaml.yaml", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_server.py", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/server.py")        
        shutil.copyfile(f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/backup_Dockerfile", f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/Dockerfile")   




    #Delete all kube deployments and pods that were created as waste
    subprocess.run(f"kubectl delete deployments --all", shell=True, check=True)
    subprocess.run(f"kubectl delete pods --all", shell=True, check=True)


def selectTestFunc(testName):
    """ return the test function based on the test name given """
    if testName == "allStepsAtOnce":
        return allStepsAtOnce
    elif testName == "stepByStep":
        return stepByStep
    elif testName == "singleAgent":
        return singleAgentApproach
    elif testName == "conversationalAgent":
        return conversationAgentApproach
    else:
        return None

def runSingleTest(testFunc, configFile):
    """ Run the test and collect the results from the run """
    startTime = time.time()
    result, reason = testFunc(configFile = configFile)
    endTime = time.time()
    totalTime = endTime - startTime

    return {"TimeTaken":totalTime,"Result":result, "Failure Reason":reason}

def appendResultsToLog(testTechnique, testName, model, results):

    todaysDate = datetime.date.today()
    with open("/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/result_logs/results_4_19_25.txt", "a") as file:
        file.write(f"({todaysDate}) : Model - {model}, Technique - {testTechnique}, Test Name - {testName} \n\nResult: {results} \n\n------------------------------------------------------------------ \n")


def run():
    """ main runner function which is responsilbe for setting up and running all tests """
    numTests = 10
    results = {}
    model = "gemini-1.5-flash"
    for testName in ["allStepsAtOnce", "stepByStep"]:#["allStepsAtOnce", "stepByStep", "singleAgent"]:#["allStepsAtOnce", "stepByStep", "singleAgent", "conversationalAgent"]:
        testFunc = selectTestFunc(testName)
        results[testName] = {}

        for testEnvName in ["incorrect_selector", "port_mismatch", "wrong_interface", "wrong_port","environment_variable","misspelling", "volume_mount", "liveness_probe"]:#["incorrect_selector", "port_mismatch", "wrong_interface", "wrong_port","environment_variable","misspelling", "volume_mount", "liveness_probe"]:#["incorrect_selector", "port_mismatch", "readiness_failure", "wrong_interface", "wrong_port"]:

            configFile = f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/config_step.json"
            #configFile = f"/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/{testEnvName}/config_conversation.json"

            #Set up backups
            backupEnviornment(testEnvName)

            allTestResults = {}
            if testFunc:
                for testNumber in range(numTests):
                    print(f"Running Test Number : {testNumber}")
                    try:
                        testResults = runSingleTest(testFunc, configFile)
                    except Exception as e:
                        print(e)
                        testResults = {"TimeTaken":None,"Result":None, "Failure Reason":None}

                    allTestResults[testNumber] = testResults
                    #Delete test yaml and replace with the backup
                    statusFlagResult = aftermathTestOfActions(testEnvName)
                    allTestResults[testNumber]["Result"] = statusFlagResult
                    try:
                        tearDownEnviornment(testEnvName)
                    except:
                        pass

                allTestResultsDF = pd.DataFrame(allTestResults).T
                appendResultsToLog(testName, testEnvName, model, allTestResults)

                #print("Finished All Tests!")
                #print(allTestResultsDF)

                results[testName][testEnvName] = allTestResultsDF.to_dict()
            else:
                print(f"Could not find test : {testName}")


    print("Finised All Tests")
    print(results)


if __name__ == "__main__":
    run()

