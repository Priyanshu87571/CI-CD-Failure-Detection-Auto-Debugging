
import hashlib
import re
from typing import Dict, List, Tuple


# Remove ANSI terminal colors and control sequences.
ANSI_ESCAPE_RE = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)

# Redact common credentials and secret values from log output.
SECRET_PATTERNS = [
    (
        re.compile(
            r"""(?i)\b(password|secret|token|api[_-]?key|client[_-]?secret)"""
            r"""\b\s*[:=]\s*['"]?([^\s'"`,;]+)"""
        ),
        r"\1=[REDACTED_SECRET]",
    ),
    (
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,255}\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    (
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,255}\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    (
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "[REDACTED_AWS_KEY]",
    ),
    (
        re.compile(
            r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}",
            re.IGNORECASE,
        ),
        "Bearer [REDACTED_BEARER_TOKEN]",
    ),
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
            r".*?"
            r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
]

# Patterns for extracting failed test cases.
TEST_FAILURE_PATTERNS = [
    re.compile(r"FAILED\s+([^\s:]+)::([^\s]+)\s+-\s+(.+)"),
    re.compile(r"FAIL\s+([^\s]+)\s+>\s+([^\s]+)"),
    re.compile(r"AssertionError:\s*(.+)"),
    re.compile(r"Expected:\s*(.+?)\s+Received:\s*(.+)"),
]

# Stack trace boundaries.
PYTHON_TRACEBACK_START = re.compile(
    r"Traceback \(most recent call last\):"
)

JS_STACK_TRACE_LINE = re.compile(
    r"^\s+at\s+(.+?)(?:\s+\((.+):(\d+):(\d+)\)|:(\d+):(\d+))$"
)


class ParsedLogResult:
    """Sanitized log and extracted diagnostic information."""

    def __init__(
        self,
        sanitized_log: str,
        content_hash: str,
        stack_traces: List[str],
        failed_tests: List[Dict[str, str]],
        error_lines: List[Tuple[int, str]],
        normalized_signature: str,
    ):
        self.sanitized_log = sanitized_log
        self.content_hash = content_hash
        self.stack_traces = stack_traces
        self.failed_tests = failed_tests
        self.error_lines = error_lines
        self.normalized_signature = normalized_signature


class LogParserService:
    """Sanitize logs and extract useful CI/CD failure evidence."""

    @staticmethod
    def strip_ansi(raw_text: str) -> str:
        """Remove ANSI terminal color and control sequences."""
        return ANSI_ESCAPE_RE.sub("", raw_text or "")

    @staticmethod
    def redact_secrets(text: str) -> str:
        """Redact common credentials before logs are stored or analyzed."""
        sanitized = text

        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    @classmethod
    def sanitize(
        cls,
        raw_text: str,
        max_chars: int = 150_000,
    ) -> str:
        """Remove terminal codes, redact secrets, and limit log size."""
        if max_chars < 1:
            raise ValueError("max_chars must be greater than zero.")

        cleaned = cls.strip_ansi(raw_text)
        cleaned = cls.redact_secrets(cleaned)

        if len(cleaned) > max_chars:
            marker = (
                "\n\n... [DeployGuard: middle of log truncated] ...\n\n"
            )
            available = max(0, max_chars - len(marker))
            head_size = available // 2
            tail_size = available - head_size

            head = cleaned[:head_size]
            tail = cleaned[-tail_size:] if tail_size else ""

            cleaned = f"{head}{marker}{tail}"

        return cleaned

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """Compute the SHA-256 hash of sanitized log content."""
        return hashlib.sha256(
            text.encode("utf-8", errors="replace")
        ).hexdigest()

    @classmethod
    def extract_stack_traces(cls, text: str) -> List[str]:
        """Extract Python tracebacks and JavaScript stack traces."""
        stack_traces: List[str] = []
        lines = text.splitlines()
        index = 0
        count = len(lines)

        while index < count:
            line = lines[index]

            if PYTHON_TRACEBACK_START.search(line):
                trace_lines = [line]
                index += 1

                while index < count:
                    current = lines[index]

                    # Tracebacks usually contain indented frames, followed
                    # by the final exception line.
                    if (
                        current.startswith((" ", "\t"))
                        or not current.strip()
                    ):
                        trace_lines.append(current)
                        index += 1
                        continue

                    if re.match(
                        r"^[A-Za-z_][\w.]*"
                        r"(?:Error|Exception|Interrupt|Exit)\b",
                        current.strip(),
                    ):
                        trace_lines.append(current)
                        index += 1

                    break

                stack_traces.append("\n".join(trace_lines))
                continue

            if (
                "Error:" in line
                or "Exception:" in line
                or line.strip().endswith("Error")
            ):
                trace_lines = [line]
                next_index = index + 1

                while next_index < count:
                    candidate = lines[next_index]

                    if JS_STACK_TRACE_LINE.search(candidate):
                        trace_lines.append(candidate)
                        next_index += 1
                        continue

                    if candidate.strip().startswith("at "):
                        trace_lines.append(candidate)
                        next_index += 1
                        continue

                    # Include common Python-style frame lines when present.
                    if re.match(
                        r'^\s*File\s+["\'].*["\'],\s+line\s+\d+',
                        candidate,
                    ):
                        trace_lines.append(candidate)
                        next_index += 1
                        continue

                    break

                if len(trace_lines) > 1:
                    stack_traces.append("\n".join(trace_lines))
                    index = next_index
                    continue

            index += 1

        return stack_traces

    @classmethod
    def extract_failed_tests(
        cls,
        text: str,
    ) -> List[Dict[str, str]]:
        """Identify failing test cases with their original line numbers."""
        failed_tests: List[Dict[str, str]] = []

        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in TEST_FAILURE_PATTERNS:
                match = pattern.search(line)

                if match:
                    failed_tests.append(
                        {
                            "line": str(line_number),
                            "raw": line.strip(),
                            "details": match.group(0),
                        }
                    )
                    break

        return failed_tests

    @classmethod
    def extract_error_lines(
        cls,
        text: str,
    ) -> List[Tuple[int, str]]:
        """Extract diagnostic lines using 1-based line numbers."""
        error_lines: List[Tuple[int, str]] = []

        error_patterns = [
            re.compile(
                r"\b(?:error|fatal|exception|traceback|"
                r"modulenotfounderror|importerror|syntaxerror|"
                r"typeerror|referenceerror|assertionerror):",
                re.IGNORECASE,
            ),
            re.compile(r"\bFAILED\s+\S+::\S+", re.IGNORECASE),
            re.compile(r"\bFAIL\s+\S+\s+>\s+\S+", re.IGNORECASE),
            re.compile(
                r"\bcommand failed with exit code\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bnpm ERR!", re.IGNORECASE),
            re.compile(
                r"\bprocess completed with exit code\s+[1-9]\d*\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:EACCES|ECONNREFUSED|ENOTFOUND|"
                r"ERESOLVE|ENOENT|ETIMEDOUT)\b"
            ),
            re.compile(
                r"\b\d+\s+failed(?:,|\s|$)",
                re.IGNORECASE,
            ),
        ]

        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in error_patterns):
                error_lines.append((line_number, line.strip()))

        return error_lines

    @classmethod
    def compute_normalized_signature(
        cls,
        failed_job_name: str,
        error_lines: List[Tuple[int, str]],
    ) -> str:
        """Build a stable signature for similar errors in the same job."""
        raw_error_text = " ".join(
            line for _, line in error_lines[:5]
        )

        normalized = raw_error_text.lower()

        # Normalize volatile values without erasing meaningful error codes.
        normalized = re.sub(
            r"0x[0-9a-f]+",
            "0xADDR",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\b\d{4}-\d{2}-\d{2}"
            r"[t ]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
            r"(?:z|[+-]\d{2}:?\d{2})?\b",
            "TIMESTAMP",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\bline\s+\d+\b",
            "line NUM",
            normalized,
        )
        normalized = re.sub(
            r"(?<=:)\d+(?=:\d+\b)",
            "NUM",
            normalized,
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()

        signature_base = (
            f"{failed_job_name.strip().lower()}:{normalized}"
        )

        return hashlib.sha256(
            signature_base.encode("utf-8")
        ).hexdigest()

    @classmethod
    def parse_log(
        cls,
        raw_log: str,
        failed_job_name: str = "build",
    ) -> ParsedLogResult:
        """Run the complete sanitization and diagnostic extraction pipeline."""
        sanitized = cls.sanitize(raw_log)
        error_lines = cls.extract_error_lines(sanitized)

        return ParsedLogResult(
            sanitized_log=sanitized,
            content_hash=cls.compute_content_hash(sanitized),
            stack_traces=cls.extract_stack_traces(sanitized),
            failed_tests=cls.extract_failed_tests(sanitized),
            error_lines=error_lines,
            normalized_signature=cls.compute_normalized_signature(
                failed_job_name,
                error_lines,
            ),
        )
