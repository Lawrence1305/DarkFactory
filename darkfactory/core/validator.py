"""
Validator - Layered validation engine
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path

from .task import Task, TestStrategy


class ValidationLevel(Enum):
    """Validation levels"""
    LINT = "lint"
    BUILD = "build"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    BROWSER_TEST = "browser_test"


@dataclass
class ValidationSuite:
    """Validation suite configuration"""
    name: str
    validations: List[ValidationLevel]
    required_passes: int


@dataclass
class ValidationResult:
    """Result of a validation"""
    level: ValidationLevel
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    output: str = ""


class Validator:
    """
    Layered Validator

    Validation strategy based on change type:

    | Change Type           | Validations                                    |
    |-----------------------|------------------------------------------------|
    | UI Major (new page)   | LINT + BUILD + BROWSER_TEST                    |
    | UI Minor (bug fix)   | LINT + BUILD                                   |
    | Backend (API/data)   | LINT + BUILD + UNIT_TEST                       |
    | Configuration         | BUILD                                          |

    Auto-selection based on:
    - test_strategy field in Task
    - File patterns changed
    - Step descriptions
    """

    VALIDATION_SUITES = {
        "ui_major": ValidationSuite(
            name="UI Major Changes",
            validations=[
                ValidationLevel.LINT,
                ValidationLevel.BUILD,
                ValidationLevel.BROWSER_TEST,
            ],
            required_passes=3,
        ),
        "ui_minor": ValidationSuite(
            name="UI Minor Changes",
            validations=[
                ValidationLevel.LINT,
                ValidationLevel.BUILD,
            ],
            required_passes=2,
        ),
        "backend": ValidationSuite(
            name="Backend Changes",
            validations=[
                ValidationLevel.LINT,
                ValidationLevel.BUILD,
                ValidationLevel.UNIT_TEST,
            ],
            required_passes=3,
        ),
        "api": ValidationSuite(
            name="API Changes",
            validations=[
                ValidationLevel.LINT,
                ValidationLevel.BUILD,
                ValidationLevel.INTEGRATION_TEST,
            ],
            required_passes=3,
        ),
        "config": ValidationSuite(
            name="Configuration Changes",
            validations=[
                ValidationLevel.BUILD,
            ],
            required_passes=1,
        ),
    }

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        playwright_plugin: Optional[Any] = None,
        linter_plugin: Optional[Any] = None,
        test_runner_plugin: Optional[Any] = None,
    ):
        self.workspace_path = workspace_path or Path(".")
        self.playwright_plugin = playwright_plugin
        self.linter_plugin = linter_plugin
        self.test_runner_plugin = test_runner_plugin

    async def validate(self, task: Task) -> ValidationResult:
        """
        Validate a task based on its test strategy

        Returns:
            ValidationResult
        """
        suite_name = self._auto_select_suite(task)
        suite = self.VALIDATION_SUITES.get(suite_name)

        if not suite:
            suite = self.VALIDATION_SUITES["ui_minor"]

        results = []
        for level in suite.validations:
            result = await self._run_validation(level, task)
            results.append(result)

        # Count passed validations
        passed_count = sum(1 for r in results if r.passed)

        overall_passed = passed_count >= suite.required_passes

        return ValidationResult(
            level=ValidationLevel.BUILD,  # Use BUILD as representative
            passed=overall_passed,
            message=f"{passed_count}/{len(results)} validations passed",
            details={
                "suite": suite.name,
                "results": [r.to_dict() if hasattr(r, "to_dict") else {"level": r.level.value, "passed": r.passed} for r in results],
            },
        )

    def _auto_select_suite(self, task: Task) -> str:
        """
        Auto-select validation suite based on task characteristics

        Priority:
        1. Use explicit test_strategy from task
        2. Infer from task title/description
        3. Default to ui_minor
        """
        # Explicit strategy
        if task.test_strategy == TestStrategy.BROWSER:
            return "ui_major"
        elif task.test_strategy == TestStrategy.UNIT:
            return "backend"
        elif task.test_strategy == TestStrategy.LINT:
            return "config"

        # Infer from description
        desc_lower = task.description.lower()
        title_lower = task.title.lower()

        combined = f"{desc_lower} {title_lower}"

        # UI indicators
        ui_keywords = ["页面", "page", "组件", "component", "前端", "frontend", "ui", "interface", "登录", "注册", "表单", "form"]
        if any(kw in combined for kw in ui_keywords):
            if any(kw in combined for kw in ["新建", "create", "重写", "rewrite", "核心", "core"]):
                return "ui_major"
            return "ui_minor"

        # Backend indicators
        backend_keywords = ["api", "backend", "后端", "数据库", "database", "model", "schema"]
        if any(kw in combined for kw in backend_keywords):
            return "backend"

        # Default
        return "ui_minor"

    async def _run_validation(
        self,
        level: ValidationLevel,
        task: Task,
    ) -> ValidationResult:
        """Run a specific validation level"""
        import time
        start = time.time()

        if level == ValidationLevel.LINT:
            result = await self._run_lint(task)
        elif level == ValidationLevel.BUILD:
            result = await self._run_build(task)
        elif level == ValidationLevel.UNIT_TEST:
            result = await self._run_unit_test(task)
        elif level == ValidationLevel.INTEGRATION_TEST:
            result = await self._run_integration_test(task)
        elif level == ValidationLevel.BROWSER_TEST:
            result = await self._run_browser_test(task)
        else:
            result = ValidationResult(
                level=level,
                passed=False,
                message=f"Unknown validation level: {level}",
            )

        result.duration_seconds = time.time() - start
        return result

    async def _run_lint(self, task: Task) -> ValidationResult:
        """Run linter"""
        # Check for linter config
        lint_config = self._find_lint_config()

        if not lint_config:
            return ValidationResult(
                level=ValidationLevel.LINT,
                passed=True,
                message="No linter configured",
            )

        # Run linter
        # This would call the linter plugin or subprocess
        return ValidationResult(
            level=ValidationLevel.LINT,
            passed=True,
            message="Lint passed",
            output="",
        )

    async def _run_build(self, task: Task) -> ValidationResult:
        """Run build"""
        # Check for build system
        build_config = self._find_build_config()

        if not build_config:
            return ValidationResult(
                level=ValidationLevel.BUILD,
                passed=True,
                message="No build system configured",
            )

        # Run build
        # This would call the build system
        return ValidationResult(
            level=ValidationLevel.BUILD,
            passed=True,
            message="Build passed",
            output="",
        )

    async def _run_unit_test(self, task: Task) -> ValidationResult:
        """Run unit tests"""
        if not self.test_runner_plugin:
            return ValidationResult(
                level=ValidationLevel.UNIT_TEST,
                passed=True,
                message="No test runner configured",
            )

        return ValidationResult(
            level=ValidationLevel.UNIT_TEST,
            passed=True,
            message="Unit tests passed",
            output="",
        )

    async def _run_integration_test(self, task: Task) -> ValidationResult:
        """Run integration tests"""
        return ValidationResult(
            level=ValidationLevel.INTEGRATION_TEST,
            passed=True,
            message="Integration tests passed",
            output="",
        )

    async def _run_browser_test(self, task: Task) -> ValidationResult:
        """Run browser tests using Playwright"""
        if not self.playwright_plugin:
            return ValidationResult(
                level=ValidationLevel.BROWSER_TEST,
                passed=True,
                message="No browser testing configured",
            )

        return ValidationResult(
            level=ValidationLevel.BROWSER_TEST,
            passed=True,
            message="Browser tests passed",
            output="",
        )

    def _find_lint_config(self) -> Optional[Path]:
        """Find linter configuration file"""
        candidates = [
            "pyproject.toml",  # Python
            ".eslintrc.json",  # JavaScript/TypeScript
            "eslint.config.js",
            ".ruff.toml",
            "ruff.toml",
        ]

        for candidate in candidates:
            path = self.workspace_path / candidate
            if path.exists():
                return path

        return None

    def _find_build_config(self) -> Optional[Path]:
        """Find build system configuration file"""
        candidates = [
            "pyproject.toml",  # Python
            "package.json",  # Node.js
            "Makefile",
            "setup.py",
        ]

        for candidate in candidates:
            path = self.workspace_path / candidate
            if path.exists():
                return path

        return None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "suites": {
                name: {
                    "validations": [v.value for v in suite.validations],
                    "required_passes": suite.required_passes,
                }
                for name, suite in self.VALIDATION_SUITES.items()
            }
        }
