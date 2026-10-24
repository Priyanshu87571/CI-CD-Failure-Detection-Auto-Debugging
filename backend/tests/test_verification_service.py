from pathlib import Path

import pytest

from backend.app.services.verification_service import VerificationService


@pytest.fixture
def source_dir(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.py").write_text("# fixture source\n", encoding="utf-8")
    return source


def _mock_execution(monkeypatch, exit_codes):
    results = iter(exit_codes)

    def execute_in_sandbox(**kwargs):
        code = next(results)
        return code, "test output", "", 5

    monkeypatch.setattr(
        VerificationService, "execute_in_sandbox", execute_in_sandbox
    )
    monkeypatch.setattr(
        VerificationService, "apply_patch_to_directory", lambda **kwargs: None
    )


def test_passing_baseline_and_candidate_is_inconclusive_not_resolved(
    monkeypatch, source_dir
):
    _mock_execution(monkeypatch, [0, 0])

    result = VerificationService.run_verification(
        str(source_dir),
        "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-# fixture source\n+# candidate source\n",
        "pytest -q",
    )

    assert result.status == "inconclusive"
    assert result.baseline_result == "passed"
    assert result.candidate_result == "passed"
    assert result.test_summary["resolved"] is False
    assert "baseline also passed" in result.failure_reason


def test_failed_baseline_and_passing_candidate_is_resolved(
    monkeypatch, source_dir
):
    _mock_execution(monkeypatch, [1, 0])

    result = VerificationService.run_verification(
        str(source_dir),
        "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-# fixture source\n+# candidate source\n",
        "pytest -q",
    )

    assert result.status == "passed"
    assert result.baseline_result == "failed"
    assert result.candidate_result == "passed"
    assert result.test_summary["resolved"] is True


def test_candidate_failure_remains_failed(monkeypatch, source_dir):
    _mock_execution(monkeypatch, [1, 1])

    result = VerificationService.run_verification(
        str(source_dir),
        "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-# fixture source\n+# candidate source\n",
        "pytest -q",
    )

    assert result.status == "failed"
    assert result.test_summary["resolved"] is False


def test_patch_application_failure_is_recorded_without_candidate_tests(
    monkeypatch, source_dir
):
    executions = iter([1])

    def execute_in_sandbox(**kwargs):
        return next(executions), "baseline failed", "", 5

    def reject_patch(**kwargs):
        raise RuntimeError("patch does not apply to checked-out commit")

    monkeypatch.setattr(
        VerificationService, "execute_in_sandbox", execute_in_sandbox
    )
    monkeypatch.setattr(
        VerificationService, "apply_patch_to_directory", reject_patch
    )

    result = VerificationService.run_verification(
        str(source_dir),
        "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-# stale source\n+# candidate source\n",
        "pytest -q",
    )

    assert result.status == "failed"
    assert result.baseline_result == "failed"
    assert result.candidate_result == "patch_application_failed"
    assert result.test_summary["patch_applied"] is False
    assert "does not apply" in result.failure_reason
