
import re
from typing import Any, Dict, List, Tuple

from backend.app.models.failure import FailureCategory


class ClassificationResult:
    def __init__(
        self,
        category: FailureCategory,
        confidence: float,
        rule_id: str,
        confidence_justification: str,
        summary: str,
        evidence_lines: List[Tuple[int, str]],
    ):
        self.category = category
        self.confidence = confidence
        self.rule_id = rule_id
        self.confidence_justification = confidence_justification
        self.summary = summary
        self.evidence_lines = evidence_lines


# Specific errors are checked before generic test failures.
# Exit code 1 alone does not prove that a unit test failed.
RULES: List[Dict[str, Any]] = [
    {
        "id": "RULE_DEP_01_PYTHON_MISSING_MODULE",
        "category": FailureCategory.DEPENDENCY_INSTALLATION,
        "pattern": re.compile(
            r"""(?:ModuleNotFoundError|ImportError):\s*No module named\s+['"]([^'"]+)['"]""",
            re.IGNORECASE,
        ),
        "confidence": 0.97,
        "summary": "Missing Python dependency/module: '{group}' is not installed.",
        "justification": "Python reported a missing module by name.",
        "capture_group": 1,
    },
    {
        "id": "RULE_DEP_02_NPM_RESOLVE",
        "category": FailureCategory.DEPENDENCY_INSTALLATION,
        "pattern": re.compile(
            r"(?:"
            r"npm\s+(?:ERR!|error)\s+code\s+"
            r"(?:E404|ERESOLVE|ENOENT|ETARGET|ECONNRESET)|"
            r"npm\s+(?:ERR!|error)\s+Missing:|"
            r"ERR_MODULE_NOT_FOUND|"
            r"""Cannot find module\s+['"][^'"]+['"]|"""
            r"No matching version found for"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.94,
        "summary": "Node.js dependency installation or module resolution failed.",
        "justification": "A package manager or Node.js module-resolution error was detected.",
    },
    {
        "id": "RULE_COMP_01_SYNTAX_ERROR",
        "category": FailureCategory.COMPILATION_SYNTAX,
        "pattern": re.compile(
            r"(?:"
            r"SyntaxError\s*:|"
            r"error TS\d+:|"
            r"TS\d+:\s*error|"
            r"""Cannot find name\s+['"][^'"]+['"]|"""
            r"Unexpected token|"
            r"Unexpected end of input"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.95,
        "summary": "A syntax or compilation error prevents the project from building.",
        "justification": "An explicit parser or compiler diagnostic was detected.",
    },
    {
        "id": "RULE_LINT_01_RUFF",
        "category": FailureCategory.LINTING_FORMATTING,
        "pattern": re.compile(
            r"(?:"
            r"\bFound\s+\d+\s+errors?\b|"
            r"^\s*[A-Z]\d{3}\s+.+$|"
            r"\bruff\s+check\b.*\b(?:failed|error)\b|"
            r"^\s*All checks passed\s*$"
            r")",
            re.IGNORECASE | re.MULTILINE,
        ),
        "confidence": 0.93,
        "summary": "Ruff reported Python lint violations.",
        "justification": "A Ruff diagnostic or lint summary was detected.",
    },
    {
        "id": "RULE_LINT_02_ESLINT",
        "category": FailureCategory.LINTING_FORMATTING,
        "pattern": re.compile(
            r"(?:"
            r"\beslint\b.*\b(?:error|failed|problems?)\b|"
            r"\d+\s+problems?\s*\(\s*\d+\s+errors?,\s*"
            r"\d+\s+warnings?\s*\)|"
            r"\d+\s+errors?\s+and\s+\d+\s+warnings?|"
            r"^\s*✖\s+\d+\s+problems?\b|"
            # ESLint diagnostics can be present even when the command
            # summary is absent from the captured log excerpt.
            r"\b(?:error|warning)\s+.+\s+@typescript-eslint/[\w-]+\b|"
            r"\b(?:error|warning)\s+.+\s+\((?:no-unused-vars|@typescript-eslint/no-unused-vars)\)"
            r")",
            re.IGNORECASE | re.MULTILINE,
        ),
        "confidence": 0.92,
        "summary": "ESLint reported JavaScript or TypeScript lint violations.",
        "justification": "An ESLint diagnostic or violation summary was detected.",
    },
    {
        "id": "RULE_LINT_03_FORMATTER",
        "category": FailureCategory.LINTING_FORMATTING,
        "pattern": re.compile(
            r"(?:"
            r"\bwould reformat\b|"
            r"\bBlack would reformat\b|"
            r"\bflake8:\s*found\s+\d+\s+errors?\b|"
            r"\bprettier\b.*\b(?:error|failed|not formatted)\b"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.90,
        "summary": "A formatter or style checker reported violations.",
        "justification": "A formatting or linting failure was detected.",
    },
    {
        "id": "RULE_ENV_01_MISSING_ENV_VAR",
        "category": FailureCategory.MISSING_ENV_VAR,
        "pattern": re.compile(
            r"(?:"
            r"""KeyError:\s*['"]([A-Z][A-Z0-9_]*)['"]|"""
            r"""environment variable\s+['"]([A-Z][A-Z0-9_]*)['"]\s+is not set|"""
            r"Missing required environment variable"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.91,
        "summary": "The application requires an environment variable that is missing.",
        "justification": "A missing-environment-variable diagnostic was detected.",
    },
    {
        "id": "RULE_CONFIG_01_YAML_JSON",
        "category": FailureCategory.CONFIGURATION_ERROR,
        "pattern": re.compile(
            r"(?:"
            r"yaml\.parser\.ParserError|"
            r"yaml\.scanner\.ScannerError|"
            r"json\.decoder\.JSONDecodeError|"
            r"invalid configuration file|"
            r"schema validation failed"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.92,
        "summary": "A configuration file failed parsing or schema validation.",
        "justification": "A YAML/JSON parser or configuration validation error was detected.",
    },
    {
        "id": "RULE_PERM_01_ACCESS_DENIED",
        "category": FailureCategory.PERMISSION_ERROR,
        "pattern": re.compile(
            r"(?:"
            r"PermissionDenied|"
            r"EACCES:\s*permission denied|"
            r"Access Denied|"
            r"403 Forbidden|"
            r"insufficient permissions"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.89,
        "summary": "A filesystem or API permission error blocked execution.",
        "justification": "An explicit access-denied diagnostic was detected.",
    },
    {
        "id": "RULE_NET_01_EXTERNAL_SERVICE",
        "category": FailureCategory.NETWORK_EXTERNAL_SERVICE,
        "pattern": re.compile(
            r"(?:"
            r"ConnectionRefusedError|"
            r"getaddrinfo ENOTFOUND|"
            r"HTTPError:\s*50[234]|"
            r"Connection timed out after \d+\s*ms|"
            r"ECONNRESET|ECONNREFUSED|ETIMEDOUT"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.88,
        "summary": "A network connection or external service request failed.",
        "justification": "A connection, DNS, timeout, or remote-service error was detected.",
    },
    {
        "id": "RULE_RES_01_TIMEOUT_OOM",
        "category": FailureCategory.RESOURCE_TIMEOUT,
        "pattern": re.compile(
            r"(?:"
            r"Workflow timed out after|"
            r"Process completed with exit code 137|"
            r"JavaScript heap out of memory|"
            r"fatal error: runtime: out of memory|"
            r"out of memory|"
            r"job exceeded its maximum execution time"
            r")",
            re.IGNORECASE,
        ),
        "confidence": 0.92,
        "summary": "The job exceeded a resource or execution-time limit.",
        "justification": "A timeout or memory-exhaustion diagnostic was detected.",
    },
    {
        "id": "RULE_TEST_01_ASSERTION_FAILURE",
        "category": FailureCategory.UNIT_TEST,
        "pattern": re.compile(
            r"(?:"
            r"\bAssertionError\b|"
            r"^\s*FAILED\s+\S+::\S+|"
            r"^\s*FAIL\s+\S+\s*>\s*\S+|"
            r"\b\d+\s+failed(?:,\s*\d+\s+passed)?\b|"
            r"\bTests:\s*\d+\s+failed\b|"
            r"\btest suite failed\b|"
            r"\bpytest\b.*\bfailed\b|"
            r"\bDeployGuard test:\s*intentional CI failure\b"
            r")",
            re.IGNORECASE | re.MULTILINE,
        ),
        "confidence": 0.92,
        "summary": "An automated test failed during CI execution.",
        "justification": "Explicit test failure output or an assertion failure was detected.",
    },
]


class FailureClassifierService:
    @classmethod
    def classify(
        cls,
        sanitized_log: str,
        error_lines: List[Tuple[int, str]],
        failed_job_name: str = "build",
    ) -> ClassificationResult:
        log = sanitized_log or ""
        lines = error_lines or []

        # Search supplied diagnostic lines first.
        for rule in RULES:
            pattern = rule["pattern"]

            for line_no, content in lines:
                match = pattern.search(content)
                if not match:
                    continue

                group_index = rule.get("capture_group")
                group_value = (
                    match.group(group_index)
                    if group_index and match.lastindex
                    else match.group(0)
                )

                summary = rule["summary"].replace("{group}", group_value)

                return ClassificationResult(
                    category=rule["category"],
                    confidence=rule["confidence"],
                    rule_id=rule["id"],
                    confidence_justification=rule["justification"],
                    summary=summary,
                    evidence_lines=[(line_no, content.strip())],
                )

        # Fall back to searching the complete sanitized log.
        log_lines = log.splitlines()

        for rule in RULES:
            pattern = rule["pattern"]
            match = pattern.search(log)

            if not match:
                continue

            group_index = rule.get("capture_group")
            group_value = (
                match.group(group_index)
                if group_index and match.lastindex
                else match.group(0)
            )

            summary = rule["summary"].replace("{group}", group_value)

            evidence = [
                (index, line.strip())
                for index, line in enumerate(log_lines, start=1)
                if pattern.search(line)
            ]

            return ClassificationResult(
                category=rule["category"],
                confidence=round(rule["confidence"] * 0.95, 3),
                rule_id=rule["id"],
                confidence_justification=rule["justification"],
                summary=summary,
                evidence_lines=evidence[:3] or lines[:3],
            )

        return ClassificationResult(
            category=FailureCategory.UNKNOWN,
            confidence=0.35,
            rule_id="RULE_UNKNOWN_FALLBACK",
            confidence_justification=(
                "No configured deterministic pattern matched the available log. "
                "The root cause cannot be reliably determined from this evidence."
            ),
            summary=(
                f"Unknown failure in job '{failed_job_name}'. "
                "Review the complete execution log for diagnostic clues."
            ),
            evidence_lines=lines[:3],
        )
