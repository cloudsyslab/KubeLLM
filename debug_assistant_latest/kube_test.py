"""
Compatibility module for older imports.

The active workflow now uses `teardown.py` directly. The legacy batch harness
was moved to `legacy/debug_assistant_latest/kube_test.py` for later review.
"""

from teardown import TEARDOWN_CONFIG, backup_environment, teardown_environment


def backupEnviornment(test_env_name):
    """Backward-compatible wrapper around teardown.backup_environment()."""
    backup_environment(test_env_name)


def tearDownEnviornment(test_env_name):
    """Backward-compatible wrapper around teardown.teardown_environment()."""
    teardown_environment(test_env_name)
