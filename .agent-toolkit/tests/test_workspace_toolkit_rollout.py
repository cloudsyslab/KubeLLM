import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOLKIT_PATH = Path(__file__).resolve().parents[1] / "bin" / "workspace_toolkit.py"
SPEC = importlib.util.spec_from_file_location("workspace_toolkit_rollout_test", TOOLKIT_PATH)
TOOLKIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOLKIT
SPEC.loader.exec_module(TOOLKIT)


def git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


class LocalRolloutTests(unittest.TestCase):
    def test_unselected_checkout_is_not_authorized_for_update(self):
        source = Path("/tmp/kubellm-rollout-source").resolve()
        checkout = Path("/tmp/kubellm-rollout-other").resolve()
        self.assertTrue(TOOLKIT.rollout_checkout_is_selected(source, source, set()))
        self.assertFalse(TOOLKIT.rollout_checkout_is_selected(checkout, source, set()))
        self.assertTrue(TOOLKIT.rollout_checkout_is_selected(checkout, source, {checkout}))

    def test_fast_forward_preserves_ignored_path_collision(self):
        with tempfile.TemporaryDirectory(prefix="toolkit-rollout-test-") as temporary:
            root = Path(temporary)
            checkout = root / "checkout"
            target_worktree = root / "target"
            checkout.mkdir()
            git(checkout, "init", "--quiet", "--initial-branch=main")
            git(checkout, "config", "user.name", "Toolkit Test")
            git(checkout, "config", "user.email", "toolkit-test@example.invalid")
            (checkout / ".gitignore").write_text("ignored-output.bin\n")
            git(checkout, "add", ".gitignore")
            git(checkout, "commit", "--quiet", "-m", "base")
            base = git(checkout, "rev-parse", "HEAD")

            ignored = checkout / "ignored-output.bin"
            ignored.write_bytes(b"keep local artifact")
            git(checkout, "worktree", "add", "--quiet", "--detach", str(target_worktree), base)
            tracked = target_worktree / "ignored-output.bin"
            tracked.write_bytes(b"tracked upstream file")
            git(target_worktree, "add", "-f", "ignored-output.bin")
            git(target_worktree, "commit", "--quiet", "-m", "track colliding path")
            target_sha = git(target_worktree, "rev-parse", "HEAD")

            result = TOOLKIT.fast_forward_default_checkout(checkout, target_sha)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ignored-output.bin", result.stderr)
            self.assertEqual(git(checkout, "rev-parse", "HEAD"), base)
            self.assertEqual(ignored.read_bytes(), b"keep local artifact")


if __name__ == "__main__":
    unittest.main()
