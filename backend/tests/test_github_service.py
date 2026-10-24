import pytest
from backend.app.services.github_service import GitHubService

@pytest.mark.parametrize(("value", "expected"), [
    ("Priyanshu87571/store-rating-platform", "Priyanshu87571/store-rating-platform"),
    ("https://github.com/Priy anshu87571/store-rating-platform", None),
    ("https://github.com/Priyanshu87571/store-rating-platform", "Priyanshu87571/store-rating-platform"),
    ("https://github.com/Priy anshu87571/store-rating-platform.git", None),
])
def test_normalize_repo(value, expected):
    if expected is None:
        with pytest.raises(ValueError):
            GitHubService.normalize_repo(value)
    else:
        assert GitHubService.normalize_repo(value) == expected

def test_reject_non_github_url():
    with pytest.raises(ValueError):
        GitHubService.normalize_repo("https://example.com/owner/repo")
