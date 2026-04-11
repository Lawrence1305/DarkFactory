"""
Test Runner Plugin - pytest-based testing
"""

import subprocess
import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..plugin import TestRunnerPlugin, PluginType


class TestRunnerPlugin(TestRunnerPlugin):
    """
    Built-in test runner plugin using pytest

    Provides comprehensive Python testing with coverage support.
    """

    name = "pytest-runner"
    version = "1.0.0"
    description = "Python test runner using pytest"
    plugin_type = PluginType.TEST_RUNNER
    hooks_provided = ["test", "test_with_coverage"]

    config_schema = {
        "test_paths": {"type": "list", "required": False, "default": ["tests"]},
        "markers": {"type": "list", "required": False},
        "cov": {"type": "bool", "required": False, "default": False},
        "cov_source": {"type": "str", "required": False, "default": "src"},
        "verbose": {"type": "bool", "required": False, "default": True},
    }

    def __init__(self):
        super().__init__()
        self._pytest_available: Optional[bool] = None

    def _check_pytest(self) -> bool:
        """Check if pytest is available"""
        if self._pytest_available is None:
            try:
                subprocess.run(
                    ["pytest", "--version"],
                    capture_output=True,
                    check=True,
                )
                self._pytest_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._pytest_available = False
        return self._pytest_available

    def execute(
        self,
        test_paths: Optional[List[str]] = None,
        markers: Optional[List[str]] = None,
        cov: bool = False,
        verbose: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Run tests

        Args:
            test_paths: Paths to test (default: from config or ["tests"])
            markers: pytest markers to filter
            cov: Enable coverage
            verbose: Verbose output
            **kwargs: Additional arguments

        Returns:
            Test results
        """
        if not self._check_pytest():
            return {
                "success": False,
                "error": "pytest not installed. Run: pip install pytest",
                "output": "",
                "tests_passed": 0,
                "tests_failed": 0,
            }

        paths = test_paths or self._config.get("test_paths", ["tests"])
        run_cov = cov or self._config.get("cov", False)

        cmd = ["pytest", "-v", "--tb=short"]
        if run_cov:
            cmd.append(f"--cov={self._config.get('cov_source', 'src')}")
            cmd.append("--cov-report=json")

        if markers:
            for marker in markers:
                cmd.append(f"-m={marker}")

        cmd.extend(paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Parse coverage if enabled
            coverage = None
            if run_cov:
                cov_file = Path("coverage.json")
                if cov_file.exists():
                    try:
                        with open(cov_file) as f:
                            coverage = json.load(f)
                    except Exception:
                        pass

            # Parse test results
            output = result.stdout + result.stderr
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": output,
                "tests_passed": passed,
                "tests_failed": failed,
                "coverage": coverage,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "tests_passed": 0,
                "tests_failed": 0,
            }

    def test(
        self,
        test_paths: Optional[List[str]] = None,
        markers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run tests without coverage"""
        return self.execute(test_paths=test_paths, markers=markers, cov=False)

    def test_with_coverage(
        self,
        test_paths: Optional[List[str]] = None,
        markers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run tests with coverage"""
        return self.execute(test_paths=test_paths, markers=markers, cov=True)
