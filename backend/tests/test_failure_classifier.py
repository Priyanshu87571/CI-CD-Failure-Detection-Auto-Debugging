import pytest
from backend.app.services.failure_classifier import FailureClassifierService, FailureCategory


def test_classify_dependency_installation():
    log = "ModuleNotFoundError: No module named 'fastapi'"
    res = FailureClassifierService.classify(log, [(10, log)])
    assert res.category == FailureCategory.DEPENDENCY_INSTALLATION
    assert res.confidence >= 0.90
    assert "RULE_DEP_01" in res.rule_id
    assert "fastapi" in res.summary


def test_classify_unit_test_failure():
    log = "FAILED tests/test_calc.py::test_sum - AssertionError: assert 4 == 5"
    res = FailureClassifierService.classify(log, [(25, log)])
    assert res.category == FailureCategory.UNIT_TEST
    assert res.confidence >= 0.90
    assert "RULE_TEST_01" in res.rule_id


def test_classify_compilation_syntax():
    log = "SyntaxError: invalid syntax in file parser.py, line 4"
    res = FailureClassifierService.classify(log, [(4, log)])
    assert res.category == FailureCategory.COMPILATION_SYNTAX
    assert res.confidence >= 0.90


def test_classify_missing_env_var():
    log = "KeyError: 'STRIPE_API_KEY'"
    res = FailureClassifierService.classify(log, [(8, log)])
    assert res.category == FailureCategory.MISSING_ENV_VAR
    assert res.confidence >= 0.85


def test_classify_unknown_fallback():
    log = "Build failed with ambiguous exit code. Something broke."
    res = FailureClassifierService.classify(log, [])
    assert res.category == FailureCategory.UNKNOWN
    assert res.confidence <= 0.50
    assert res.rule_id == "RULE_UNKNOWN_FALLBACK"
