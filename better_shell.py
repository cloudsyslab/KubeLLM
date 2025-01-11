from pathlib import Path
from typing import List, Optional, Union

from phi.tools import Toolkit
from phi.utils.log import logger

class BetterShellTools(Toolkit):
    def __init__(self, base_dir: Optional[Union[Path, str]] = None):
        super().__init__(name="shell_tools")

        self.base_dir: Optional[Path] = None
        if base_dir is not None:
            self.base_dir = Path(base_dir) if isinstance(base_dir, str) else base_dir

        self.register(self.run_shell_command)

    #def run_shell_command(self, args: str, tail: int = 100) -> str:
            #tail (int): The number of lines to return from the output.
    def run_shell_command(self, args: str) -> str:
        """Runs a shell command and returns the output or error.

        Args:
            args (str): The command to run, as if typing into a bash shell.
        Returns:
            str: The output of the command.
        """
        import subprocess

        try:
            logger.info(f"Running shell command: {args}")
            if self.base_dir:
                result = subprocess.run(args, check=True, cwd=self.base_dir, capture_output=True, shell=True, text=True)
            else:
                result = subprocess.run(args, check=True, capture_output=True, shell=True, text=True)
            logger.debug(f"Result: {result}")
            logger.debug(f"Return code: {result.returncode}")
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            # return only the last n lines of the output
            return "\n".join(result.stdout.split("\n")[-50:])
        except Exception as e:
            logger.warning(f"Failed to run shell command: {e}")
            return f"Error: {e}"
