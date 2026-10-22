import os

from prompt_helpers import append_relevant_files

from verification_base import VerificationAgentBase


class AgentVerification_v2(VerificationAgentBase):
    """
    Verification agent that checks whether the debug agent successfully resolved the Kubernetes issue.
    This agent inspects Kubernetes state and reports its judgment without changing the system.
    """

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.debugAgentResponse = None
        self.verificationStatus = None
        self.verificationReport = None

    default_instructions = [
        "You are a verification agent tasked with verifying whether the described Kubernetes issue has been fixed.",
        "Inspect Kubernetes state with direct read-only kubectl commands such as get, describe, and logs.",
        "Do not change resources, edit files, enter pods, read Secrets, or make network requests.",
        "A Running pod alone does not establish that the original symptom is resolved.",
        "If the available evidence is insufficient, report UNKNOWN.",
        "After completing verification, you must conclude with EXACTLY one of these tokens:",
        "- <|VERIFIED|> if the issue has been completely fixed",
        "- <|FAILED|> if the issue has NOT been fixed",
        "- <|VERIFICATION_ERROR|> only if you cannot inspect the relevant cluster state",
        "DO NOT create your own tokens. Use ONLY the three tokens listed above.",
    ]

    default_guidelines = [
        "Use only read-only resource metadata, status, and logs as evidence.",
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
            5. Never change cluster state or run an active network probe. If the available evidence cannot establish reachability, report UNKNOWN.

            ### RELEVANT MANIFESTS (use these to find exact names)
            """
            self.prompt = append_relevant_files(
                self.config,
                self.prompt,
                file_types=["deployment", "application", "service"],
            )

            from debug_assistant_latest.lab_context import active_lane_config, is_lane_active

            lane_profile = active_lane_config()["minikube_profile"] if is_lane_active() else None
            configured_profile = self.config.get("minikube-profile")
            if lane_profile and configured_profile and configured_profile != lane_profile:
                raise ValueError("Case Minikube profile conflicts with the selected lab lane")
            minikube_profile = lane_profile or configured_profile or os.environ.get("MINIKUBE_PROFILE") or "minikube"
            self.prompt += f"""
            ### CURRENT CONTEXT
            - Working directory: {self.config['test-directory']}
            - Main configuration file: {self.config.get('yaml-file-name', 'N/A')}
            - Minikube profile: {minikube_profile}

            ### READ-ONLY VERIFICATION PROCEDURE (follow in order)
            1. Run `kubectl get pods` → confirm all expected pods exist and are in Running state with 1/1 (or expected) ready containers.
            2. For each expected pod, run `kubectl describe pod <pod-name>` and check Events for errors (CrashLoopBackOff, ImagePullBackOff, OOM, etc.).
            3. If relevant Service YAML exists, run `kubectl get service <service-name>` and inspect its selector and ports.
            4. Inspect endpoints and one-shot pod logs with direct `kubectl get` or `kubectl logs` commands.
            5. Do not use `kubectl exec`, `minikube service`, curl, or any command that changes state. If those are needed to establish reachability, report UNKNOWN.
            """
        except Exception as e:
            raise RuntimeError(f"Error creating verification agent prompt: {e}") from e


class AgentVerification_v1(VerificationAgentBase):
    """
    Verification agent that checks whether the debug agent successfully resolved the Kubernetes issue.
    This agent inspects Kubernetes state and reports its judgment without changing the system.
    """

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.debugAgentResponse = None
        self.verificationStatus = None
        self.verificationReport = None

    default_instructions = [
        "You are a verification agent tasked with verifying whether the debug agent successfully resolved the Kubernetes issue.",
        "Inspect Kubernetes state with direct read-only kubectl commands such as get, describe, and logs.",
        "Do not change resources, edit files, enter pods, read Secrets, or make network requests.",
        "A Running pod alone does not establish that the original symptom is resolved.",
        "If the available evidence is insufficient, report UNKNOWN.",
        "After completing verification, you must conclude with EXACTLY one of these tokens:",
        "- <|VERIFIED|> if the issue has been completely fixed",
        "- <|FAILED|> if the issue has NOT been fixed",
        "- <|VERIFICATION_ERROR|> only if you cannot inspect the relevant cluster state",
        "DO NOT create your own tokens. Use ONLY the three tokens listed above.",
    ]

    default_guidelines = [
        "Use read-only resource metadata, status, and logs as evidence.",
        "A Running pod alone does not establish that the original symptom is resolved.",
        "Do not assume the debug agent succeeded just because it said so",
        "Check the actual current state, not what was claimed",
        "You MUST use one of the three specified tokens: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>",
    ]

    def preparePrompt(self):
        try:
            self.prompt = "You are a verification agent. Your task is to verify whether the debug agent actually solved the Kubernetes issue.\n\n"
            self.prompt += f"=== ORIGINAL PROBLEM ===\n{self.config['knowledge-prompt']['problem-desc']}\n\n"
            if self.debugAgentResponse:
                self.prompt += f"=== DEBUG AGENT'S RESPONSE ===\n{self.debugAgentResponse}\n\n"
            self.prompt += "=== YOUR OBSERVATION-ONLY VERIFICATION TASK ===\n"
            self.prompt += "1. Read the debug agent's response carefully\n"
            self.prompt += "2. Identify what changes it claims to have made\n"
            self.prompt += "3. Inspect live Kubernetes resources, status, and logs with direct read-only commands\n"
            self.prompt += "4. Do not change resources, edit files, enter pods, or make network requests\n"
            self.prompt += "5. If the available evidence cannot establish the symptom's status, report UNKNOWN\n\n"
            self.prompt += "=== RELEVANT MANIFESTS (context only) ===\n"
            self.prompt = append_relevant_files(
                self.config,
                self.prompt,
                file_types=["deployment", "application", "service"],
            )
            self.prompt += f"\nTest directory: {self.config['test-directory']}\n"
            self.prompt += f"Configuration file: {self.config.get('yaml-file-name', 'N/A')}\n\n"
            self.prompt += "=== VERIFICATION APPROACH ===\n"
            self.prompt += "- Compare live cluster evidence with the original symptom and claimed changes\n"
            self.prompt += "- Confirm pod and service state from read-only commands\n"
            self.prompt += "- Report UNKNOWN when a conclusion requires an active probe\n"
            self.prompt += "- DO NOT trust claims without verification\n\n"
        except Exception as e:
            raise RuntimeError(f"Error creating verification agent prompt: {e}") from e
