from phi.assistant import Assistant
from phi.llm.ollama import Ollama
from phi.tools.shell import ShellTools
#from phi.llm.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.ollama import OllamaTools
import requests
import rag_api
# Import the functions and BASE_URL from rag_api.py
from rag_api import (
    BASE_URL,
    initialize_assistant,
    ask_question,
    add_url,
    upload_pdf,
    clear_knowledge_base,
    get_chat_history,
    start_new_run
)
def read_yaml_file_as_string(file_path):
    """Reads the YAML file as plain text and returns its content as a string."""
    try:
        with open(file_path, 'r') as file:
            yaml_content = file.read()  # Read the entire file content as a string
        return yaml_content
    except FileNotFoundError:
        return "YAML file not found."
    except Exception as e:
        return f"Error reading the file: {e}"

# file contents
base_path = '/home/mario/AgentAnalysis/WilliamAgent/phidata-samples/troubleshooting/'
prompt_directions = 'Give specific commands to fix this issue. If modifying file contents is necessary, use the sed command to achieve this. If providing a file path, make sure to keep the full file path.'

# wrong interface
wrong_interface_yaml = open(base_path + "wrong_interface/wrong_interface.yaml","r").read()
wrong_interface_app = open(base_path + "wrong_interface/server.py","r").read()
wrong_interface_dockerfile = open(base_path + "wrong_interface/Dockerfile","r").read()

# wrong port
wrong_port_yaml = open(base_path + "wrong_port/wrong_port.yaml","r").read()
wrong_port_app = open(base_path + "wrong_port/server.py","r").read()
wrong_port_dockerfile = open(base_path + "wrong_port/Dockerfile","r").read()

# no pod ip
ip_yaml = open(base_path + "no_pod_ip/correct_app.yaml","r").read()
ip_app = open(base_path + "no_pod_ip/server.py","r").read()
ip_dockerfile = open(base_path + "no_pod_ip/Dockerfile","r").read()
ip_service = open(base_path + "no_pod_ip/app_service.yaml","r").read()

# readiness probe failure
readiness_failure_yaml = open(base_path + "readiness_failure/readiness_failure.yaml","r").read()

# incorrect selector
incorrect_selector_yaml = open(base_path + "incorrect_selector/correct_app.yaml","r").read()
incorrect_selector_service = open(base_path + "incorrect_selector/app-service.yaml","r").read()

# Read the YAML content as a string
# yaml_string_content = read_yaml_file_as_string(yaml_file_path)

# Print the string representation of the YAML file
# print(yaml_string_content)

print("Base URL:", BASE_URL)

new_run_response = start_new_run()
print("New Run Response:", new_run_response)
input()

# initialize RAG assistant
initialize_response = initialize_assistant("llama3.1:70b", "nomic-embed-text")
print("Initialize Response:", initialize_response)
input()
# clear knowledge base
clear_kb_response = clear_knowledge_base()
print("Clear Knowledge Base Response:", clear_kb_response)
input()
# add knowledge to knowledge base
add_url_response = add_url("https://learnk8s.io/troubleshooting-deployments")
print("Add URL Response:", add_url_response)
add_url_response = add_url("https://pythonbasics.org/webserver/") 
print("Add URL Response:", add_url_response)
input()
# begin a new run
# knowledge source for RAG assistant can be provied here through API call, or directly through web interface
# knowledge database is persistent. So, no need to add knowledge source every time. 
###########


# Assuming that the knowledge database is already updated, ask a question to RAG assistant
# wrong_interface
# response = ask_question(f"The pod on my Kubernetes cluster cannot be accessed by making a curl request. Any requests made to the application running in this pod result in a timeout. {prompt_directions} This is the deployment configuration: {wrong_interface_yaml}. This is the application server code: {wrong_interface_app}. This is the container image Dockerfile: {wrong_interface_dockerfile}.")

# wrong_port
# response = ask_question(f"The pod on my Kubernetes cluster cannot be accessed by making a curl request. Any requests made to the application running in this pod result in a timeout. {prompt_directions} This is the deployment configuration: {wrong_port_yaml}. This is the application server code: {wrong_port_app}. This is the container image Dockerfile: {wrong_port_dockerfile}.")

# no_pod_ip
# response = ask_question(f"When I describe the pod on my cluster, it has an IP address listed. The service associated with the pod seems to be configured correctly. Describing the service shows no endpoints listed for the service. {prompt_directions} This is the deployment configuration: {ip_yaml}. This is the application server code: {ip_app}. This is the container image Dockerfile: {ip_dockerfile}. This is the app-service configuration: {ip_service}.")

# readiness_probe
response = ask_question(f"When I describe the pod on my cluster, it shows the Ready condition for the pod as False. {prompt_directions} This is the deployment manifest is named: readiness_failure.yaml and the path for the manifest is: /home/mario/AgentAnalysis/WilliamAgent/phidata-samples/troubleshooting/readiness_failure/readiness_failure.yaml and the contents are : {readiness_failure_yaml}.")

# incorrect_selector
#response = ask_question(f"When I describe the service associated with the pod on my kubernetes cluster, it shows no endpoints listed. {prompt_directions} This is the deployment configuration: {incorrect_selector_yaml}. This is the deployment service configuration file: {incorrect_selector_service}.")

print("RAG assistant Response:", response)


assistant = Assistant(
    llm=OllamaTools(model="llama3.1:70b"),
    tools=[ShellTools()], 
    debug_mode=True,
    # Show tool calls in the response
    show_tool_calls=True,
    # Enable the assistant to read the chat history
    read_chat_history=False,
)

#assistant.cli_app(markdown=True)
# wrong_interface
# assistant.print_response(f"The deployment is described in the file: {base_path}wrong_interface/wrong_interface.yaml. Here is the deployment file contents: {wrong_interface_yaml}. The application source code is defined in the file: {base_path}wrong_interface/server.py. Here is the application source code: {wrong_interface_app}. The container image Dockerfile is defined in the file: {base_path}wrong_interface/Dockerfile. Here is the Dockerfile contents: {wrong_interface_dockerfile}. Take the necessary actions suggested here: {str(response)} You can update the wrong_interface.yaml, Dockerfile, or server.py files if necessary. If the wrong_interface.yaml, Dockerfile, or server.py files are updated, make sure to delete and reapply the wrong_interface.yaml deployment.")

# wrong_port
# assistant.print_response(f"The deployment is described in the file: {base_path}wrong_port/wrong_port.yaml. Here is the deployment file contents: {wrong_port_yaml}. The application source code is defined in the file: {base_path}wrong_port/server.py. Here is the application source code: {wrong_port_app}. The container image Dockerfile is defined in the file: {base_path}wrong_port/Dockerfile. Here is the Dockerfile contents: {wrong_port_dockerfile}. Take the necessary actions suggested here: {str(response)} You can update the wrong_port.yaml, Dockerfile, or server.py files if necessary. If the wrong_port.yaml, Dockerfile, or server.py files are updated, make sure to delete and reapply the wrong_port.yaml deployment.")

# no_pod_ip
# assistant.print_response(f"The deployment is described in the file: {base_path}no_pod_ip/correct_app.yaml. Here is the deployment file contents: {ip_yaml}. The application source code is defined in the file: {base_path}no_pod_ip/server.py. Here is the application source code: {ip_app}. The container image Dockerfile is defined in the file: {base_path}no_pod_ip/Dockerfile. Here is the Dockerfile contents: {ip_dockerfile}. The service deployment configuration is defined in the file: {base_path}no_pod_ip/app_service.yaml. Here is the deployment file contents: {ip_service}. Take the necessary actions suggested here: {str(response)} You can update the correct_app.yaml, app-service.yaml, Dockerfile, or server.py files if necessary. If the correct_app.yaml, app-service.yaml, Dockerfile, or server.py files are updated, make sure to delete and reapply the correct_app.yaml and app-service.yaml deployments.")

# readiness_probe
assistant.print_response(f"The deployment is described in the file: {base_path}readiness_failure/readiness_failure.yaml. Here is the deployment file contents: {readiness_failure_yaml}. Take the necessary actions suggested here: {str(response)} You can update the readiness_failure.yaml file if necessary. If the readiness_failure.yaml file is updated, make sure to delete and reapply the readiness_failure.yaml deployment. Give full exact instructions on how to perform the deployment deletion and reapplication steps.")

# incorrect_selector
#assistant.print_response(f"The deployment is described in the file: {base_path}incorrect_selector/incorrect_selector.yaml. Here is the deployment file contents: {incorrect_selector_yaml}. The application source code is defined in the file: {base_path}incorrect_selector/server.py. Here is the application source code: {ip_app}. The container image Dockerfile is defined in the file: {base_path}incorrect_selector/Dockerfile. Here is the Dockerfile contents: {ip_dockerfile}. The service deployment configuration is defined in the file: {base_path}incorrect_selector/app-service.yaml. Here is the service deployment file contents: {incorrect_selector_service}. Take the necessary actions suggested here: {str(response)} You can update the correct_app.yaml, app-service.yaml, Dockerfile, or server.py files if necessary. If the correct_app.yaml, app-service.yaml, Dockerfile, or server.py files are updated, make sure to delete and reapply the correct_app.yaml and app-service.yaml deployments.")
