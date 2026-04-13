"""
Linter Plugin - Code linting with ruff
"""

import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..plugin import LinterPlugin, PluginType


class LinterPlugin(LinterPlugin):
    """
    Built-in linter plugin using ruff

    Provides fast Python linting with configurable rules.
    """

    name = "ruff-linter"
    version = "1.0.0"
    description = "Fast Python linter using ruff"
    plugin_type = PluginType.LINTER
    hooks_provided = ["lint", "lint_fix"]

    config_schema = {
        "paths": {"type": "list", "required": False, "default": ["src"]},
        "rules": {"type": "list", "required": False},
        "fix": {"type": "bool", "required": False, "default": False},
    }

    def __init__(self):
        super().__init__()
        self._ruff_available: Optional[bool] = None

    def _check_ruff(self) -> bool:
        """Check if ruff is available"""
        if self._ruff_available is None:
            try:
                subprocess.run(
                    ["ruff", "--version"],
                    capture_output=True,
                    check=True,
                )
                self._ruff_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._ruff_available = False
        return self._ruff_available

    def execute(self, paths: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Run linter

        Args:
            paths: Paths to lint (default: from config or ["src"])
            **kwargs: Additional arguments

        Returns:
            Linting results
        """
        if not self._check_ruff():
            return {
                "success": False,
                "error": "ruff not installed. Run: pip install ruff",
                "output": "",
            }

        lint_paths = paths or self._config.get("paths", ["src"])
        fix = kwargs.get("fix", self._config.get("fix", False))

        cmd = ["ruff", "check"]
        if fix:
            cmd.append("--fix")
        cmd.extend(lint_paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": result.stdout + result.stderr,
                "fixed": result.stdout.count("Fixed") if fix else 0,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
            }

    def lint(self, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Lint without fix"""
        return self.execute(paths=paths, fix=False)

    def lint_fix(self, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Lint with auto-fix"""
        return self.execute(paths=paths, fix=True)
