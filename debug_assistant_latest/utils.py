from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.llm.ollama import Ollama
from phi.tools.shell import ShellTools
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.ollama import OllamaTools

import requests
import rag_api
import json
import sys
import os
import subprocess
import timeout_decorator
from pathlib import Path

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

def readTheJSONConfigFile(configFile):
    """ Read the provided config JSON file within the arguments when the script is called """
    parsedConfig = None
    config_file_path = None
    try:
        if configFile:
            config_file_path = configFile
            with open(configFile,"r") as config_file:
                parsedConfig = json.loads(config_file.read())
        else:
            config_file_path = sys.argv[1]
            with open(sys.argv[1],"r") as config_file:
                parsedConfig = json.loads(config_file.read())

        # If test-directory is empty, derive it from config file location
        if not parsedConfig.get("test-directory") or parsedConfig.get("test-directory") == "":
            config_dir = Path(config_file_path).parent.absolute()
            parsedConfig["test-directory"] = str(config_dir) + "/"
            print(f"DEBUG: Derived test-directory from config location: {parsedConfig['test-directory']}")

    except Exception as e:
        print("Failed to open config file, please make sure you input a valid path in the arguments when invoking the python script")
        print(e)
        sys.exit()
    return parsedConfig


def update_debug_agent_model(json_file_path: str, new_model: str) -> None:
    """
    Updates the model name under the 'debug-agent' category in the specified JSON file.
    
    Args:
        json_file_path (str): The path to the JSON file.
        new_model (str): The new model name to set.
    
    Raises:
        FileNotFoundError: If the JSON file does not exist.
        KeyError: If 'debug-agent' or 'model' key is not found in the JSON.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    # Load the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Update the model in debug-agent
    if 'debug-agent' not in data:
        raise KeyError("'debug-agent' key not found in JSON.")
    if 'model' not in data['debug-agent']:
        raise KeyError("'model' key not found in 'debug-agent'.")
    
    data['debug-agent']['model'] = new_model
    
    # Write back to the JSON file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)


def setUpEnvironment(config):
    """ Setup the enviornment using the set up commands specified in the config"""
    try:
        for command in config.get("setup-commands", []):
            subprocess.run(command, shell=True, check=True)
    except Exception as e:
        print(f"Error running setup command: {e}")

def identifyLLM(debugAgent):
    """ Identify the LLM model that was specified in the config and setup accordingly """
    model = None
    if debugAgent["llm-source"].lower() == "ollama":    
        model = Ollama(id="llama3.1:70b")
    elif debugAgent["llm-source"].lower() == "openai":
        model = OpenAIChat(id="gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")  # Returns None if not set
        if api_key is None:
            print("Error: OPENAI_API_KEY is not set!")
            sys.exit()
        #os.environ["OPENAI_API_KEY"] = debugAgent["api-key"]

    return model

def traverseRelevantFiles(config, relevantFileType, prompt):
    """ Traverse all the relevant file type that is passed """
    file_path = Path(config["test-directory"]).expanduser()

    if relevantFileType != "dockerfile":
        for dep in config["relevant-files"][relevantFileType]:
            contents = open(file_path / dep, "r").read()
            prompt = f"{prompt} The file " +" "+ str(file_path) +"/"+ dep +" "+ f" describes a {relevantFileType}. This is the file contents: {contents}."
    elif relevantFileType == "dockerfile" and config["relevant-files"][relevantFileType]:
        contents = open(file_path / 'Dockerfile', "r").read()
        prompt = f"{prompt} The file " +" "+ str(file_path) + "/" + "Dockerfile"+" "+ f" describes a {relevantFileType}. This is the file contents: {contents}."
    print (f"DEBUG: {prompt}")
    return prompt

def printFinishMessage():
    """ Print a finish message, may need to add basic analytics """
    print("=================================================")
    print("                   FINISHED                      ")
    print("=================================================")


def withTimeout(default_value):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except timeout_decorator.TimeoutError:
                return default_value
        return wrapper
    return decorator

    
