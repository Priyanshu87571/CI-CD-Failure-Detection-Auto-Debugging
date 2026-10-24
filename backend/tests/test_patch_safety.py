import pytest
from backend.app.services.fix_generator import FixGeneratorService, PatchValidationError


def test_valid_patch_accepted():
    patch = """--- a/src/math.py
+++ b/src/math.py
@@ -1,2 +1,2 @@
-def sub(): pass
+def add(): pass
"""
    files = FixGeneratorService.validate_patch_safety(patch)
    assert files == ["src/math.py"]


def test_reject_path_traversal():
    patch = """--- a/../../secret.txt
+++ b/../../secret.txt
@@ -1,1 +1,1 @@
-old
+new
"""
    with pytest.raises(PatchValidationError) as exc:
        FixGeneratorService.validate_patch_safety(patch)
    assert "Path traversal detected" in str(exc.value)


def test_reject_absolute_path():
    patch = """--- a//etc/passwd
+++ b//etc/passwd
@@ -1,1 +1,1 @@
-root
+hacked
"""
    with pytest.raises(PatchValidationError) as exc:
        FixGeneratorService.validate_patch_safety(patch)
    assert "Absolute paths are forbidden" in str(exc.value) or "restricted target" in str(exc.value)


def test_reject_restricted_files():
    patch = """--- a/.env
+++ b/.env
@@ -1,1 +1,1 @@
-A=1
+A=2
"""
    with pytest.raises(PatchValidationError) as exc:
        FixGeneratorService.validate_patch_safety(patch)
    assert "restricted target" in str(exc.value)
