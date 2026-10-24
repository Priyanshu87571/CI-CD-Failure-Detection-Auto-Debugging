import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.services.fix_generator import (
    FixGeneratorService,
    PatchValidationError,
)


# Only these commands can be used to run verification.
ALLOWLISTED_RUNNERS = {
    "pytest",
    "python",
    "python3",
    "npm",
    "yarn",
    "pnpm",
    "go",
    "cargo",
}

# Environment variables that must not be passed to test processes.
SENSITIVE_ENV_VARS = {
    "SECRET_KEY",
    "AI_API_KEY",
    "GITHUB_TOKEN",
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_CLIENT_SECRET",
    "GITHUB_APP_PRIVATE_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SESSION_TOKEN",
}


class VerificationResult:
    """Structured result of a baseline-versus-candidate verification."""

    def __init__(
        self,
        status: str,
        exit_code: Optional[int],
        duration_ms: int,
        baseline_result: Optional[str],
        candidate_result: Optional[str],
        test_summary: Dict[str, Any],
        failure_reason: Optional[str] = None,
    ):
        self.status = status
        self.exit_code = exit_code
        self.duration_ms = duration_ms
        self.baseline_result = baseline_result
        self.candidate_result = candidate_result
        self.test_summary = test_summary
        self.failure_reason = failure_reason


class VerificationService:
    """Safely apply a proposed patch and compare baseline/candidate results."""

    @staticmethod
    def validate_command(command_str: str) -> List[str]:
        """
        Validate the requested test command.

        Shell operators, command substitutions, redirections, and arbitrary
        executable names are rejected. Arguments are restricted to a
        conservative character set to prevent command injection.
        """
        if not isinstance(command_str, str) or not command_str.strip():
            raise ValueError("Test command cannot be empty.")

        if len(command_str) > 500:
            raise ValueError("Test command is too long.")

        # Reject shell metacharacters and control characters.
        if re.search(r'[;&|><$`!%\r\n\x00]', command_str):
            raise ValueError(
                "Test command contains a forbidden shell metacharacter."
            )

        tokens = command_str.strip().split()

        if not tokens:
            raise ValueError("Test command cannot be empty.")

        executable = os.path.basename(tokens[0]).lower()

        if executable.endswith(".exe"):
            executable = executable[:-4]

        if executable.endswith(".cmd") or executable.endswith(".bat"):
            executable = executable.rsplit(".", 1)[0]

        if executable not in ALLOWLISTED_RUNNERS:
            raise ValueError(
                f"Executable '{executable}' is not allowed. "
                f"Allowed commands: {', '.join(sorted(ALLOWLISTED_RUNNERS))}."
            )

        # Prevent argument-based shell injection. Common verification
        # arguments such as "-m", "pytest", "run", "build", and file paths
        # remain supported.
        for token in tokens:
            if not re.fullmatch(r"[A-Za-z0-9_./:=@+-]+", token):
                raise ValueError(
                    f"Unsupported characters in command argument: {token!r}"
                )

        return tokens

    @staticmethod
    def get_sanitized_env() -> Dict[str, str]:
        """Create a child-process environment without application secrets."""
        clean_env = os.environ.copy()

        for key in SENSITIVE_ENV_VARS:
            clean_env.pop(key, None)

        # Keep Python imports predictable when running tests.
        clean_env["PYTHONUNBUFFERED"] = "1"

        return clean_env

    @staticmethod
    def _resolve_executable(executable: str) -> Optional[str]:
        """
        Resolve an allowlisted executable.

        On Windows, npm, yarn, and pnpm are commonly installed as .cmd
        files. These must be launched through cmd.exe rather than directly
        with shell=False.
        """
        executable_name = os.path.basename(executable).lower()

        if os.name == "nt":
            if executable_name in {"npm", "npm.cmd"}:
                candidates = ["npm.cmd", "npm.exe", "npm"]
            elif executable_name in {"yarn", "yarn.cmd"}:
                candidates = ["yarn.cmd", "yarn.exe", "yarn"]
            elif executable_name in {"pnpm", "pnpm.cmd"}:
                candidates = ["pnpm.cmd", "pnpm.exe", "pnpm"]
            else:
                candidates = [executable]

            for candidate in candidates:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved

            return None

        return shutil.which(executable)

    @classmethod
    def _launch_process(
        cls,
        command_tokens: List[str],
        workspace_dir: str,
        env: Dict[str, str],
        timeout_seconds: int,
    ) -> Tuple[int, str, str, int]:
        """
        Execute a validated command and return:
        (exit_code, stdout, stderr, duration_ms).

        Windows batch files are started through cmd.exe because CreateProcess
        cannot reliably execute .cmd files directly when shell=False.
        """
        start_time = time.monotonic()

        executable = cls._resolve_executable(command_tokens[0])

        if not executable:
            raise FileNotFoundError(
                f"Required executable '{command_tokens[0]}' was not found "
                "on PATH. Install the appropriate runtime and restart "
                "the backend so it inherits the updated PATH."
            )

        resolved_tokens = [executable, *command_tokens[1:]]

        if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
            comspec = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")

            if not os.path.isfile(comspec):
                raise FileNotFoundError(
                    f"Windows command processor was not found: {comspec}"
                )

            # Command tokens have already passed the strict allowlist and
            # argument validation above. list2cmdline handles Windows
            # argument quoting.
            command_line = subprocess.list2cmdline(resolved_tokens)

            # cmd.exe /c requires a quoted command string for reliable
            # execution of batch files with paths containing spaces.
            process_args = [
                comspec,
                "/d",
                "/s",
                "/c",
                f'"{command_line}"',
            ]
        else:
            process_args = resolved_tokens

        process = subprocess.Popen(
            process_args,
            cwd=workspace_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

            duration_ms = int((time.monotonic() - start_time) * 1000)

            return (
                -1,
                stdout or "",
                (
                    (stderr or "")
                    + f"\nCommand timed out after {timeout_seconds} seconds."
                ),
                duration_ms,
            )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        return process.returncode, stdout or "", stderr or "", duration_ms

    @classmethod
    def execute_in_sandbox(
        cls,
        workspace_dir: str,
        command_tokens: List[str],
        timeout_seconds: int = 45,
    ) -> Tuple[int, str, str, int]:
        """
        Run a validated command inside the supplied temporary workspace.

        A missing executable or failed process launch is returned as a
        diagnostic instead of allowing WinError 2 to crash the API request.
        """
        try:
            return cls._launch_process(
                command_tokens=command_tokens,
                workspace_dir=workspace_dir,
                env=cls.get_sanitized_env(),
                timeout_seconds=timeout_seconds,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return (
                127,
                "",
                f"Could not start verification command: {exc}",
                0,
            )

    @classmethod
    def apply_patch_to_directory(
        cls,
        target_dir: str,
        patch_content: str,
    ) -> None:
        """Validate and apply a unified diff to the candidate checkout."""
        FixGeneratorService.validate_patch_safety(
            patch_content,
            allowed_root_dir=target_dir,
        )

        git_executable = shutil.which("git")

        if not git_executable:
            raise RuntimeError(
                "Git was not found on PATH. Install Git for Windows, "
                "restart the backend, and retry verification."
            )

        try:
            result = subprocess.run(
                [
                    git_executable,
                    "apply",
                    "--whitespace=nowarn",
                    "-",
                ],
                input=patch_content,
                text=True,
                cwd=target_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(
                f"Could not execute git apply: {exc}"
            ) from exc

        if result.returncode != 0:
            details = (
                result.stderr.strip()
                or result.stdout.strip()
                or "git apply failed without diagnostic output"
            )

            raise RuntimeError(
                "Patch does not apply cleanly to the checked-out commit: "
                + details
            )

    @classmethod
    def run_verification(
        cls,
        source_dir: str,
        patch_content: str,
        test_command: str = "pytest",
    ) -> VerificationResult:
        """
        Run baseline tests, apply the proposed patch, then run candidate
        tests. The source directory must be a real repository checkout.

        This method does not invent a checkout or claim that tests passed
        when source retrieval or process startup fails.
        """
        start_time = time.monotonic()

        def unavailable(reason: str) -> VerificationResult:
            return VerificationResult(
                status="unavailable",
                exit_code=None,
                duration_ms=int((time.monotonic() - start_time) * 1000),
                baseline_result=None,
                candidate_result=None,
                test_summary={
                    "command": test_command,
                    "tests_executed": False,
                },
                failure_reason=reason,
            )

        runner_type = str(
            getattr(settings, "VERIFICATION_RUNNER_TYPE", "isolated_process")
        ).strip().lower()

        if runner_type == "docker":
            if not shutil.which("docker"):
                return unavailable(
                    "Docker verification was requested, but the Docker "
                    "executable was not found on PATH."
                )

            return unavailable(
                "Docker verification is configured, but this service "
                "implements isolated-process execution only. Configure "
                "VERIFICATION_RUNNER_TYPE=isolated_process or implement "
                "the Docker runner before retrying."
            )

        try:
            command_tokens = cls.validate_command(test_command)
        except ValueError as exc:
            return VerificationResult(
                status="failed",
                exit_code=1,
                duration_ms=int((time.monotonic() - start_time) * 1000),
                baseline_result="invalid_command",
                candidate_result="not_run",
                test_summary={"command": test_command},
                failure_reason=str(exc),
            )

        try:
            FixGeneratorService.validate_patch_safety(patch_content)
        except PatchValidationError as exc:
            return VerificationResult(
                status="failed",
                exit_code=1,
                duration_ms=int((time.monotonic() - start_time) * 1000),
                baseline_result="not_run",
                candidate_result="rejected",
                test_summary={"command": test_command},
                failure_reason=f"Patch safety validation failed: {exc}",
            )

        if not os.path.isdir(source_dir):
            return unavailable(
                f"Repository source directory does not exist: {source_dir}"
            )

        try:
            with tempfile.TemporaryDirectory(
                prefix="deployguard_sandbox_"
            ) as sandbox_dir:
                # Copy the actual retrieved source into an isolated directory.
                shutil.copytree(
                    source_dir,
                    sandbox_dir,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(
                        ".git",
                        ".env",
                        ".env.*",
                        "__pycache__",
                        ".venv",
                        "venv",
                        "node_modules",
                    ),
                )

                if not any(os.scandir(sandbox_dir)):
                    return unavailable(
                        "The repository checkout contains no usable source "
                        "files after copying into the verification workspace."
                    )

                timeout_seconds = int(
                    getattr(settings, "VERIFICATION_TIMEOUT_SECONDS", 45)
                )
                timeout_seconds = max(1, min(timeout_seconds, 600))

                # Step 1: Run the original, unmodified source.
                base_code, base_out, base_err, base_duration = (
                    cls.execute_in_sandbox(
                        workspace_dir=sandbox_dir,
                        command_tokens=command_tokens,
                        timeout_seconds=timeout_seconds,
                    )
                )

                if base_code == 127 and (
                    "Could not start verification command:" in base_err
                ):
                    return unavailable(
                        "Baseline tests could not start. " + base_err.strip()
                    )

                baseline_status = (
                    "passed"
                    if base_code == 0
                    else "timed_out"
                    if base_code == -1
                    else "failed"
                )

                # Step 2: Apply the candidate patch to the isolated checkout.
                try:
                    cls.apply_patch_to_directory(
                        target_dir=sandbox_dir,
                        patch_content=patch_content,
                    )
                except (
                    PatchValidationError,
                    RuntimeError,
                    OSError,
                    ValueError,
                    subprocess.SubprocessError,
                ) as exc:
                    return VerificationResult(
                        status="failed",
                        exit_code=1,
                        duration_ms=int(
                            (time.monotonic() - start_time) * 1000
                        ),
                        baseline_result=baseline_status,
                        candidate_result="patch_application_failed",
                        test_summary={
                            "command": test_command,
                            "baseline": {
                                "exit_code": base_code,
                                "status": baseline_status,
                                "duration_ms": base_duration,
                                "output_tail": (
                                    base_out + "\n" + base_err
                                )[-2000:],
                            },
                            "patch_applied": False,
                        },
                        failure_reason=f"Failed to apply patch: {exc}",
                    )

                # Step 3: Run tests again after applying the candidate patch.
                cand_code, cand_out, cand_err, candidate_duration = (
                    cls.execute_in_sandbox(
                        workspace_dir=sandbox_dir,
                        command_tokens=command_tokens,
                        timeout_seconds=timeout_seconds,
                    )
                )

                if cand_code == 127 and (
                    "Could not start verification command:" in cand_err
                ):
                    return VerificationResult(
                        status="unavailable",
                        exit_code=None,
                        duration_ms=int(
                            (time.monotonic() - start_time) * 1000
                        ),
                        baseline_result=baseline_status,
                        candidate_result="not_run",
                        test_summary={
                            "command": test_command,
                            "baseline": {
                                "exit_code": base_code,
                                "status": baseline_status,
                                "duration_ms": base_duration,
                                "output_tail": (
                                    base_out + "\n" + base_err
                                )[-2000:],
                            },
                            "patch_applied": True,
                        },
                        failure_reason=(
                            "Candidate tests could not start. "
                            + cand_err.strip()
                        ),
                    )

                candidate_status = (
                    "passed"
                    if cand_code == 0
                    else "timed_out"
                    if cand_code == -1
                    else "failed"
                )

                # A passing candidate is not evidence that the patch fixed
                # the original failure if the unmodified baseline already
                # passed. Keep that run inconclusive rather than allowing the
                # API to mark the failure VERIFIED.
                resolved = base_code != 0 and base_code != -1 and cand_code == 0
                if cand_code == -1:
                    overall_status = "timed_out"
                elif cand_code != 0:
                    overall_status = "failed"
                elif resolved:
                    overall_status = "passed"
                else:
                    overall_status = "inconclusive"

                test_summary = {
                    "command": test_command,
                    "baseline": {
                        "exit_code": base_code,
                        "status": baseline_status,
                        "duration_ms": base_duration,
                        "output_tail": (
                            base_out + "\n" + base_err
                        )[-2000:],
                    },
                    "candidate": {
                        "exit_code": cand_code,
                        "status": candidate_status,
                        "duration_ms": candidate_duration,
                        "output_tail": (
                            cand_out + "\n" + cand_err
                        )[-2000:],
                    },
                    "patch_applied": True,
                    "resolved": resolved,
                }

                candidate_output = (cand_out + "\n" + cand_err).strip()

                return VerificationResult(
                    status=overall_status,
                    exit_code=cand_code,
                    duration_ms=int(
                        (time.monotonic() - start_time) * 1000
                    ),
                    baseline_result=baseline_status,
                    candidate_result=candidate_status,
                    test_summary=test_summary,
                    failure_reason=(
                        "Candidate tests passed, but the unmodified baseline "
                        "also passed; the original failure was not reproduced."
                        if overall_status == "inconclusive"
                        else None
                        if cand_code == 0
                        else candidate_output[-2000:]
                        or f"Candidate tests exited with code {cand_code}."
                    ),
                )

        except (OSError, shutil.Error, ValueError) as exc:
            return unavailable(
                f"Verification workspace error: {type(exc).__name__}: {exc}"
            )