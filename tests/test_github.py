import io
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from prscout.github import GitHubAPIError, GitHubClient, parse_repo_ref


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


# Error message tests


def _make_http_error(code, body=b"{}", reason="Forbidden"):
    """Helper: create an HTTPError with a readable body."""
    fp = io.BytesIO(body)
    fp.headers = {"X-RateLimit-Remaining": "0", "Content-Type": "application/json"}
    return HTTPError(
        url="https://api.github.com/repos/a/b",
        code=code,
        msg=reason,
        hdrs=fp.headers,
        fp=fp,
    )


@patch("prscout.github.urlopen")
def test_401_raises_auth_error(mock_urlopen):
    """HTTP 401 should raise an authentication failure message."""
    mock_urlopen.side_effect = _make_http_error(401, b'{"message":"Bad credentials"}')
    client = GitHubClient(retries=0)
    with pytest.raises(GitHubAPIError, match="Authentication failed.*HTTP 401"):
        client._get_json("repos/a/b")


@patch("prscout.github.urlopen")
def test_403_rate_limit_raises_rate_message(mock_urlopen):
    """HTTP 403 with a rate-limit body should raise the rate-limit message."""
    mock_urlopen.side_effect = _make_http_error(
        403, b'{"message":"API rate limit exceeded"}'
    )
    client = GitHubClient(retries=0)
    with pytest.raises(GitHubAPIError, match="GitHub rate limit reached"):
        client._get_json("repos/a/b")


@patch("prscout.github.urlopen")
def test_403_no_rate_limit_raises_access_denied(mock_urlopen):
    """HTTP 403 without a rate-limit body should raise access denied."""
    mock_urlopen.side_effect = _make_http_error(
        403, b'{"message":"Resource not accessible"}'
    )
    client = GitHubClient(retries=0)
    with pytest.raises(GitHubAPIError, match="Access denied.*HTTP 403"):
        client._get_json("repos/a/b")


@patch("prscout.github.urlopen")
def test_422_raises_validation_error(mock_urlopen):
    """HTTP 422 should raise the validation or API issue message."""
    mock_urlopen.side_effect = _make_http_error(422, b'{"message":"Validation Failed"}')
    client = GitHubClient(retries=0)
    with pytest.raises(GitHubAPIError, match="HTTP 422"):
        client._get_json("repos/a/b")


@patch("prscout.github.urlopen")
def test_network_timeout_raises_helpful_message(mock_urlopen):
    """TimeoutError after retries are exhausted should raise a helpful message."""
    import socket

    mock_urlopen.side_effect = TimeoutError("timed out")
    client = GitHubClient(retries=0)
    with pytest.raises(GitHubAPIError, match="Could not reach GitHub"):
        client._get_json("repos/a/b")

    # Also test that socket.timeout gives a helpful hint.
    mock_urlopen.side_effect = socket.timeout("connection timed out")
    with pytest.raises(GitHubAPIError, match="Could not reach GitHub"):
        client._get_json("repos/a/b")


@patch("prscout.github.urlopen")
def test_access_denied_retries_then_raises(mock_urlopen):
    """Confirm repeated access-denied 403 responses still raise after retries."""
    responses = [_make_http_error(403) for _ in range(4)]
    mock_urlopen.side_effect = responses
    client = GitHubClient(retries=3)
    with pytest.raises(GitHubAPIError, match="Access denied"):
        client._get_json("repos/a/b")
