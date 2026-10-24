import os
import re
from typing import Any, Dict, List, Optional, Tuple


class PatchValidationError(Exception):
    """Raised when a candidate patch fails safety validation."""


class FixGeneratorService:
    """Generate conservative candidate fixes for known CI failures."""

    SOURCE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
    }

    FORBIDDEN_NAMES = {
        ".git",
        ".env",
    }

    SYSTEM_PREFIXES = (
        "/etc/",
        "/var/",
        "/bin/",
        "/usr/",
    )

    # Supports diagnostics such as:
    # src/main.tsx:14:7: error 'unusedValue' is never used (no-unused-vars)
    COLON_DIAGNOSTIC_RE = re.compile(
        r"^\s*"
        r"(?P<file>.+?\.(?:py|js|jsx|ts|tsx|mjs|cjs|go|rs))"
        r":(?P<line>\d+)"
        r":(?P<column>\d+)"
        r":\s*"
        r"(?P<severity>error|warning)"
        r"\s+"
        r"(?P<message>.*?)"
        r"(?:\s+\((?P<rule>[\w/@.-]+)\))?"
        r"\s*$",
        re.IGNORECASE,
    )

    # Supports ESLint's standard formatter, for example:
    #   14:7  error  'unusedValue' is assigned a value but never used  no-unused-vars
    ESLINT_STANDARD_RE = re.compile(
        r"^\s*"
        r"(?P<line>\d+):(?P<column>\d+)"
        r"\s+"
        r"(?P<severity>error|warning)"
        r"\s+"
        r"(?P<message>.*?)"
        r"(?:\s{2,}(?P<rule>[\w/@.-]+))?"
        r"\s*$",
        re.IGNORECASE,
    )

    PYTHON_MISSING_MODULE_RE = re.compile(
        r"""(?:ModuleNotFoundError|ImportError):\s*"""
        r"""No module named\s+['"](?P<module>[^'"]+)['"]""",
        re.IGNORECASE,
    )

    @staticmethod
    def extract_patch_target_files(
        patch_content: str,
    ) -> List[str]:
        """Extract target paths from unified-diff headers."""
        target_files: List[str] = []

        for line in patch_content.splitlines():
            if not line.startswith("+++ "):
                continue

            path = line[4:].strip()

            # /dev/null represents a new or deleted file.
            if path == "/dev/null":
                continue

            # Remove the Git unified-diff destination prefix.
            if path.startswith("b/"):
                path = path[2:]

            # Handle simply quoted paths conservatively.
            if path.startswith('"') and path.endswith('"'):
                path = path[1:-1]

            if path:
                target_files.append(path)

        return list(dict.fromkeys(target_files))

    @classmethod
    def validate_patch_safety(
        cls,
        patch_content: str,
        allowed_root_dir: Optional[str] = None,
    ) -> List[str]:
        """Reject unsafe paths and malformed patch targets."""
        if not patch_content or not patch_content.strip():
            raise PatchValidationError(
                "Patch content cannot be empty."
            )

        target_files = cls.extract_patch_target_files(patch_content)

        if not target_files:
            raise PatchValidationError(
                "Patch does not target any valid file paths "
                "(missing +++ b/ header)."
            )

        root = (
            os.path.realpath(allowed_root_dir)
            if allowed_root_dir
            else None
        )

        for file_path in target_files:
            normalized = file_path.replace("\\", "/")

            # Reject absolute paths before checking relative path parts.
            if (
                not normalized
                or normalized.startswith("/")
                or re.match(r"^[A-Za-z]:", normalized)
                or normalized.startswith("//")
            ):
                raise PatchValidationError(
                    "Absolute paths are forbidden in patches: "
                    f"'{file_path}'."
                )

            parts = normalized.split("/")

            # Keep this exact phrase for existing tests and clear errors.
            if any(part == ".." for part in parts):
                raise PatchValidationError(
                    "Path traversal detected in target file: "
                    f"'{file_path}'."
                )

            if any(part in {"", "."} for part in parts):
                raise PatchValidationError(
                    "Invalid path in patch target: "
                    f"'{file_path}'."
                )

            if any(
                part.lower() in cls.FORBIDDEN_NAMES
                for part in parts
            ):
                raise PatchValidationError(
                    "Patch attempts to modify a restricted target: "
                    f"'{file_path}'."
                )

            if normalized.startswith(cls.SYSTEM_PREFIXES):
                raise PatchValidationError(
                    "Patch attempts to modify a restricted target: "
                    f"'{file_path}'."
                )

            if root:
                resolved = os.path.realpath(
                    os.path.join(root, normalized)
                )

                try:
                    inside_root = (
                        os.path.commonpath([root, resolved]) == root
                    )
                except ValueError:
                    inside_root = False

                if not inside_root:
                    raise PatchValidationError(
                        "Path escapes the allowed workspace root: "
                        f"'{file_path}'."
                    )

        return target_files

    @classmethod
    def _parse_lint_diagnostic(
        cls,
        log: str,
    ) -> Optional[Dict[str, Any]]:
        """Extract the first recognizable lint diagnostic."""
        # Format containing file path and source location.
        for line in log.splitlines():
            match = cls.COLON_DIAGNOSTIC_RE.match(line)

            if match:
                result: Dict[str, Any] = match.groupdict()
                result["line"] = int(result["line"])
                result["column"] = int(result["column"])
                return result

        # Standard ESLint output often puts the file path on a
        # separate heading line, so this format has no file field.
        for line in log.splitlines():
            match = cls.ESLINT_STANDARD_RE.match(line)

            if match:
                result = match.groupdict()
                result["line"] = int(result["line"])
                result["column"] = int(result["column"])
                result["file"] = None
                return result

        return None

    @classmethod
    def _safe_relative_path(
        cls,
        file_path: str,
    ) -> Optional[str]:
        """Return a normalized, repository-relative source path."""
        if not file_path:
            return None

        normalized = (
            file_path.strip()
            .strip('"')
            .replace("\\", "/")
        )

        # Remove common current-directory prefixes.
        normalized = re.sub(r"^(?:\./)+", "", normalized)

        if normalized.startswith("b/"):
            normalized = normalized[2:]

        if (
            not normalized
            or normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or normalized.startswith("//")
        ):
            return None

        parts = normalized.split("/")

        if any(part in {"", ".", ".."} for part in parts):
            return None

        if any(
            part.lower() in cls.FORBIDDEN_NAMES
            for part in parts
        ):
            return None

        extension = os.path.splitext(normalized)[1].lower()

        if extension not in cls.SOURCE_EXTENSIONS:
            return None

        return normalized

    @classmethod
    def generate_candidate_fix(
        cls,
        category: str,
        summary: str,
        evidence_text: str,
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Generate a conservative candidate fix.

        Returns:
            (patch_content, explanation, affected_files)

        A None patch means no safe, evidence-backed patch could
        be generated from the supplied evidence.
        """
        log = evidence_text or ""
        category_text = str(category or "").lower()
        summary_text = str(summary or "")

        combined_text = (
            f"{category_text}\n{summary_text}\n{log}"
        ).lower()

        # ---------------------------------------------------------
        # 1. Lint failures
        # ---------------------------------------------------------
        is_lint_failure = any(
            keyword in combined_text
            for keyword in (
                "eslint",
                "lint",
                "linting_formatting",
            )
        )

        if is_lint_failure:
            diagnostic = cls._parse_lint_diagnostic(log)

            if diagnostic:
                raw_path = diagnostic.get("file") or ""
                file_path = cls._safe_relative_path(raw_path)

                line_number = diagnostic["line"]
                column_number = diagnostic["column"]
                severity = diagnostic.get("severity") or "unknown"
                rule = diagnostic.get("rule") or "unknown rule"
                message = (
                    diagnostic.get("message") or ""
                ).strip()

                if not file_path:
                    return (
                        None,
                        (
                            "A lint diagnostic was found at "
                            f"{line_number}:{column_number}, but its "
                            "repository-relative source path is missing "
                            "or unsafe. Retrieve the exact file path and "
                            "source at the failed commit before "
                            "generating a patch."
                        ),
                        [],
                    )

                explanation = (
                    f"Lint diagnostic in {file_path}:"
                    f"{line_number}:{column_number} "
                    f"({severity}, {rule}): {message}. "
                    "The diagnostic identifies a possible problem, "
                    "but a reliable unified diff cannot be generated "
                    "from the diagnostic alone. Retrieve the exact "
                    "source file at the failed commit before proposing "
                    "a patch."
                )

                return None, explanation, [file_path]

            return (
                None,
                (
                    "A linting failure was detected, but the captured "
                    "logs do not contain a recognized file-and-location "
                    "diagnostic. Retrieve the complete lint-step output "
                    "and source context before proposing a patch."
                ),
                [],
            )

        # ---------------------------------------------------------
        # 2. Missing Python dependency
        # ---------------------------------------------------------
        dependency_match = cls.PYTHON_MISSING_MODULE_RE.search(log)

        if dependency_match:
            module_name = (
                dependency_match.group("module").split(".")[0]
            )

            if not re.fullmatch(
                r"[A-Za-z0-9_-]+",
                module_name,
            ):
                return (
                    None,
                    (
                        "A missing Python module was detected, but its "
                        "name is not safe to use in an automated patch. "
                        "Review the dependency manually."
                    ),
                    [],
                )

            return (
                None,
                (
                    f"Python reports that module '{module_name}' is "
                    "missing. No requirements.txt patch was generated "
                    "because the import name may differ from its PyPI "
                    "distribution name. Confirm the correct package "
                    "and version before changing dependencies."
                ),
                ["requirements.txt"],
            )

        # ---------------------------------------------------------
        # 3. Test failures
        # ---------------------------------------------------------
        is_test_failure = any(
            keyword in combined_text
            for keyword in (
                "assertionerror",
                "unit_test",
                "unit test",
                "pytest",
                "test failure",
                "tests failed",
            )
        )

        if is_test_failure:
            return (
                None,
                (
                    "A test failure was detected. Review the failing "
                    "test, expected behavior, and implementation. "
                    "The exact source and test context are required "
                    "before generating a safe candidate patch."
                ),
                [],
            )

        # ---------------------------------------------------------
        # 4. Unknown or unsupported failure
        # ---------------------------------------------------------
        return (
            None,
            (
                "No safe automatic patch rule matched this failure. "
                "Review the root-cause analysis, complete failure logs, "
                "and source files at the failed commit. No patch was "
                "generated because the available evidence is insufficient."
            ),
            [],
        )