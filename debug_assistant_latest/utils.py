try:
    from phi.assistant import Assistant
except ImportError:
    Assistant = None

try:
    from phi.llm.openai import OpenAIChat
except ImportError:
    OpenAIChat = None

try:
    from phi.llm.ollama import Ollama
except ImportError:
    Ollama = None

try:
    from phi.tools.shell import ShellTools
except ImportError:
    ShellTools = None

try:
    from phi.tools.duckduckgo import DuckDuckGo
except ImportError:
    DuckDuckGo = None

try:
    from phi.llm.ollama import OllamaTools
except ImportError:
    OllamaTools = None

import requests
import rag_api
import json
import sys
import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
from timeout_helpers import withTimeout
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
load_dotenv(REPO_ROOT / ".env", override=True)

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
            config_dir = Path(config_file_path).expanduser().resolve().parent
            parsedConfig["test-directory"] = str(config_dir) + "/"
            print(f"DEBUG: Derived test-directory from config location: {parsedConfig['test-directory']}")

    except Exception as e:
        raise RuntimeError(
            "Failed to open config file. Make sure the path passed to the script is valid."
        ) from e
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
    """Set up the environment using the setup commands specified in the config."""
    # Run setup commands from repo root so repo-root-relative paths work regardless of CWD.
    env = os.environ.copy()
    minikube_profile = config.get("minikube-profile")
    if minikube_profile:
        env["MINIKUBE_PROFILE"] = minikube_profile
    for command in config.get("setup-commands", []):
        subprocess.run(command, shell=True, check=True, cwd=str(REPO_ROOT), env=env)
    validate_local_images_available(config, env=env)


def _resolve_minikube_profile(config, env):
    profile = config.get("minikube-profile") or env.get("MINIKUBE_PROFILE")
    if profile:
        return profile

    try:
        result = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    context = result.stdout.strip()
    return context or None


def _manifest_paths_for_local_image_check(config):
    test_dir = Path(config.get("test-directory") or REPO_ROOT)
    if not test_dir.is_absolute():
        test_dir = REPO_ROOT / test_dir

    names = []
    yaml_file_name = config.get("yaml-file-name")
    if yaml_file_name:
        names.append(yaml_file_name)

    relevant_files = config.get("relevant-files") or {}
    deployment_files = relevant_files.get("deployment") or []
    if isinstance(deployment_files, str):
        deployment_files = [deployment_files]
    names.extend(deployment_files)

    paths = []
    seen = set()
    for name in names:
        if not name:
            continue
        path = Path(name)
        if not path.is_absolute():
            path = test_dir / path
        resolved = path.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        paths.append(resolved)
    return paths


def _pod_specs_from_manifest(doc):
    if not isinstance(doc, dict):
        return []

    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind == "Pod":
        return [spec]
    if kind in {"Deployment", "ReplicaSet", "DaemonSet", "StatefulSet", "Job"}:
        pod_spec = ((spec.get("template") or {}).get("spec") or {})
        return [pod_spec] if pod_spec else []
    if kind == "CronJob":
        job_template = (spec.get("jobTemplate") or {}).get("spec") or {}
        pod_spec = ((job_template.get("template") or {}).get("spec") or {})
        return [pod_spec] if pod_spec else []
    return []


def _normalize_latest_image_name(image):
    if not image or "@" in image:
        return image
    last_segment = image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return image
    return f"{image}:latest"


def _local_never_pull_images(config):
    images = []
    seen = set()
    for path in _manifest_paths_for_local_image_check(config):
        with open(path, "r", encoding="utf-8") as manifest:
            docs = yaml.safe_load_all(manifest)
            for doc in docs:
                for pod_spec in _pod_specs_from_manifest(doc):
                    containers = []
                    containers.extend(pod_spec.get("initContainers") or [])
                    containers.extend(pod_spec.get("containers") or [])
                    for container in containers:
                        if not isinstance(container, dict):
                            continue
                        if container.get("imagePullPolicy") != "Never":
                            continue
                        image = _normalize_latest_image_name(container.get("image"))
                        if image and image not in seen:
                            seen.add(image)
                            images.append(image)
    return images


def _image_present_in_minikube_list(image, image_list_output):
    candidates = {image}
    normalized = _normalize_latest_image_name(image)
    if normalized:
        candidates.add(normalized)
    if image and image.endswith(":latest"):
        candidates.add(image[: -len(":latest")])

    for raw_line in image_list_output.splitlines():
        line = raw_line.strip()
        for candidate in candidates:
            if line == candidate or line.endswith(f"/{candidate}"):
                return True
    return False


def validate_local_images_available(config, *, env=None, attempts=8, delay_s=1):
    """Verify minikube can see images required by imagePullPolicy: Never manifests."""
    env = env or os.environ.copy()
    images = _local_never_pull_images(config)
    if not images:
        return

    profile = _resolve_minikube_profile(config, env)
    if not profile:
        raise RuntimeError(
            "Cannot validate local Kubernetes images because no minikube profile was resolved "
            "from config['minikube-profile'], MINIKUBE_PROFILE, or kubectl current-context."
        )

    missing = images
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(
                ["minikube", "-p", profile, "image", "ls"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                cwd=str(REPO_ROOT),
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Cannot validate local Kubernetes images because minikube is not installed or not on PATH") from exc

        if result.returncode == 0:
            output = result.stdout
            missing = [image for image in images if not _image_present_in_minikube_list(image, output)]
            if not missing:
                return
            last_error = ""
        else:
            last_error = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"

        if attempt < attempts:
            time.sleep(delay_s)

    details = f": {last_error}" if last_error else ""
    raise RuntimeError(
        f"Local image(s) not found in minikube profile '{profile}' after setup: {', '.join(missing)}{details}"
    )

def identifyLLM(debugAgent):
    """ Identify the LLM model that was specified in the config and setup accordingly """
    if Ollama is None or OpenAIChat is None:
        raise RuntimeError("phi is required for identifyLLM; install the figate `phi` package first.")

    model = None
    if debugAgent["llm-source"].lower() == "ollama":
        model = Ollama(id="llama3.1:70b")
    elif debugAgent["llm-source"].lower() == "openai":
        model = OpenAIChat(id="gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")  # Returns None if not set
        if api_key is None:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to the repo-level .env file or export it in your shell."
            )
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
