import pytest

from prscout.github import parse_repo_ref


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("owner/repo", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
    ],
)
def test_parse_repo_ref(value, expected):
    assert parse_repo_ref(value).full_name == expected


def test_parse_repo_ref_rejects_non_github_url():
    with pytest.raises(ValueError, match="github.com"):
        parse_repo_ref("https://example.com/owner/repo")

