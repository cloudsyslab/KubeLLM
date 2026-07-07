import os

from prompt_helpers import append_relevant_files

from verification_base import VerificationAgentBase


class AgentVerification_v2(VerificationAgentBase):
    """
    Verification agent that checks whether the debug agent successfully resolved the Kubernetes issue.
    This agent runs diagnostic commands to verify the actual state of the cluster and files.
    """

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.debugAgentResponse = None
        self.verificationStatus = None
        self.verificationReport = None

    default_instructions = [
        "You are a verification agent tasked with verifying whether the described Kubernetes issue has been fixed.",
        "Run diagnostic commands to check the current state of the cluster.",
        "Always verify that the pods are running",
        "Since this Kubernetes cluster is running on Minikube, use the minikube service command to access services when appropriate.",
        "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
        "If kubectl logs fails, wait 5-10 seconds and try again up to 3 times",
        "If logs are still unavailable after retries, you can still verify based on pod status and output of specific diagnostic command that will be provided to you",
        "Use <|VERIFIED|> if the pod is Running and the kubectl or minikube diagnostic commands indicate success, even if logs are temporarily unavailable)",
        "After completing verification, you must conclude with EXACTLY one of these tokens:",
        "- <|VERIFIED|> if the issue has been completely fixed",
        "- <|FAILED|> if the issue has NOT been fixed",
        "- <|VERIFICATION_ERROR|> only if you cannot check files or pod status at all",
        "DO NOT create your own tokens. Use ONLY the three tokens listed above.",
    ]

    default_guidelines = [
        "If pod logs are temporarily unavailable, this is acceptable",
        "The PRIMARY verification is: pod is Running and output of kubectl or minikube based diagnostic commands.",
        "Log verification is secondary - if unavailable, ignore it. You can verify without logs",
        "You MUST use one of the three specified tokens: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>",
    ]

    include_duration_cost = True

    def preparePrompt(self):
        try:
            self.prompt = f"""You are a precise Kubernetes Verification Agent. Your only goal is to determine, with evidence, whether the original problem described below has been fully resolved in the current cluster state.

            ### ORIGINAL PROBLEM TO VERIFY
            {self.config['knowledge-prompt']['problem-desc'].strip()}

            ### VERIFICATION RULES (STRICTLY FOLLOW)
            1. **Never assume** the problem is fixed. You must prove it with real commands and observed output.
            2. Always start verification using `kubectl` (never guess pod/service names).
            3. Use exact resource names extracted from the YAML manifests — do not invent them.
            4. If a command fails or a resource does not exist, clearly state that and do not proceed as if it succeeded.
            5. Only declare the issue resolved if all relevant pods are Running/Ready and the configured access path for this scenario is reachable.

            ### RELEVANT MANIFESTS (use these to find exact names)
            """
            self.prompt = append_relevant_files(
                self.config,
                self.prompt,
                file_types=["deployment", "application", "service"],
            )

            minikube_profile = self.config.get("minikube-profile") or os.environ.get("MINIKUBE_PROFILE") or "minikube"
            self.prompt += f"""
            ### CURRENT CONTEXT
            - Working directory: {self.config['test-directory']}
            - Main configuration file: {self.config.get('yaml-file-name', 'N/A')}
            - Minikube profile: {minikube_profile}

            ### STEP-BY-STEP VERIFICATION PROCEDURE (follow exactly in order)
            1. Run `kubectl get pods` → confirm all expected pods exist and are in Running state with 1/1 (or expected) ready containers.
            2. For each expected pod, run `kubectl describe pod <pod-name>` and check Events for errors (CrashLoopBackOff, ImagePullBackOff, OOM, etc.).
            3. If relevant service YAML exists, run `kubectl get service <service-name>` → confirm expected Service exists and has ClusterIP assigned.
            4. Only if a Service manifest exists and the Service is running:
               - Run: `minikube -p {minikube_profile} service <service-name> --url`
               - Take the URL(s) returned and test with `curl -v <url>`
            5. If Ingress exists, get the ingress address and test the hostname/path with curl.
            """
        except Exception as e:
            raise RuntimeError(f"Error creating verification agent prompt: {e}") from e


class AgentVerification_v1(VerificationAgentBase):
    """
    Verification agent that checks whether the debug agent successfully resolved the Kubernetes issue.
    This agent runs diagnostic commands to verify the actual state of the cluster and files.
    """

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.debugAgentResponse = None
        self.verificationStatus = None
        self.verificationReport = None

    default_instructions = [
        "You are a verification agent tasked with verifying whether the debug agent successfully resolved the Kubernetes issue.",
        "Run diagnostic commands to check the current state of the cluster.",
        "Verify that the fixes claimed by the debug agent were actually applied.",
        "Always check the actual file contents using commands like 'cat' or 'grep'",
        "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
        "If kubectl logs fails, wait 5-10 seconds and try again up to 3 times",
        "If logs are still unavailable after retries, you can still verify based on file contents and pod status",
        "Use <|VERIFIED|> if the YAML file has the correct changes AND pod is Running (even if logs temporarily unavailable)",
        "After completing verification, you must conclude with EXACTLY one of these tokens:",
        "- <|VERIFIED|> if the issue has been completely fixed",
        "- <|FAILED|> if the issue has NOT been fixed",
        "- <|VERIFICATION_ERROR|> only if you cannot check files or pod status at all",
        "DO NOT create your own tokens. Use ONLY the three tokens listed above.",
    ]

    default_guidelines = [
        "Always verify the actual file contents to confirm changes were made",
        "Check pod status with kubectl get pods",
        "If pod logs are temporarily unavailable, this is acceptable - focus on file verification and pod status",
        "Verify the changes match what the debug agent claimed",
        "The PRIMARY verification is: Files have correct changes AND pod is Running",
        "Log verification is secondary - if unavailable, still verify based on files + pod status",
        "Do not assume the debug agent succeeded just because it said so",
        "Check the actual current state, not what was claimed",
        "If files are correct and pod is Running, you can conclude VERIFIED even without logs",
        "You MUST use one of the three specified tokens: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>",
    ]

    def preparePrompt(self):
        try:
            self.prompt = "You are a verification agent. Your task is to verify whether the debug agent actually solved the Kubernetes issue.\n\n"
            self.prompt += f"=== ORIGINAL PROBLEM ===\n{self.config['knowledge-prompt']['problem-desc']}\n\n"
            if self.debugAgentResponse:
                self.prompt += f"=== DEBUG AGENT'S RESPONSE ===\n{self.debugAgentResponse}\n\n"
            self.prompt += "=== YOUR VERIFICATION TASK ===\n"
            self.prompt += "1. Read the debug agent's response carefully\n"
            self.prompt += "2. Identify what changes it claims to have made\n"
            self.prompt += "3. Verify each claimed change is actually present in the system\n"
            self.prompt += "4. Check if the original problem is actually resolved\n"
            self.prompt += "5. Use kubectl commands and file inspection to verify the actual state\n\n"
            self.prompt += "=== RELEVANT FILES (from configuration) ===\n"
            self.prompt = append_relevant_files(
                self.config,
                self.prompt,
                file_types=["deployment", "application", "service"],
            )
            self.prompt += f"\nTest directory: {self.config['test-directory']}\n"
            self.prompt += f"Configuration file: {self.config.get('yaml-file-name', 'N/A')}\n\n"
            self.prompt += "=== VERIFICATION APPROACH ===\n"
            self.prompt += "- Check file contents match what debug agent claimed\n"
            self.prompt += "- Verify Kubernetes resources were actually modified/reapplied\n"
            self.prompt += "- Confirm pods are running (not in error states)\n"
            self.prompt += "- Test that the original problem symptom is gone\n"
            self.prompt += "- DO NOT trust claims without verification\n\n"
        except Exception as e:
            raise RuntimeError(f"Error creating verification agent prompt: {e}") from e
