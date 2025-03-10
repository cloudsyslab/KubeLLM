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
    try:
        if configFile:
            with open(configFile,"r") as config_file:
                parsedConfig = json.loads(config_file.read())
        else:
            with open(sys.argv[1],"r") as config_file:
                parsedConfig = json.loads(config_file.read())

    except Exception as e:
        print("Failed to open config file, please make sure you input a valid path in the arguments when invoking the python script")
        print(e)
        sys.exit()
    return parsedConfig

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

    
