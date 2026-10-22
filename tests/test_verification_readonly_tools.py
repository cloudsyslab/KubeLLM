import subprocess
import unittest
from unittest.mock import patch

from debug_assistant_latest.better_shell import BetterShellTools


class VerificationReadOnlyToolTests(unittest.TestCase):
    def test_read_only_kubectl_uses_direct_argv(self):
        tool = BetterShellTools(phase="verification", read_only=True)
        completed = subprocess.CompletedProcess(
            args=["kubectl", "get", "pods"], returncode=0, stdout="pod-a Ready", stderr=""
        )
        with patch("subprocess.run", return_value=completed) as run:
            result = tool.run_shell_command_result(
                "kubectl get pod app -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'"
            )

        self.assertTrue(result.succeeded)
        self.assertEqual(run.call_args.args[0][0:2], ["kubectl", "get"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_read_only_verifier_blocks_mutation_exec_secrets_and_shell_chaining(self):
        tool = BetterShellTools(phase="verification", read_only=True)
        with patch("subprocess.run") as run:
            for command in (
                "kubectl apply -f fix.yaml",
                "kubectl exec app -- rm /tmp/file",
                "kubectl get secret api-key",
                "kubectl get secrets/api-key",
                "kubectl get sec api-key",
                "kubectl get --raw /api/v1/namespaces/default/secrets/api-key",
                "kubectl get --raw=/api/v1/secrets",
                "kubectl get -f secret.yaml",
                "kubectl get pods | grep app",
            ):
                result = tool.run_shell_command_result(command)
                self.assertEqual(result.status, "blocked", command)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
