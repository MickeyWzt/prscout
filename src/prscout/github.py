from __future__ import annotations

import base64
import http.client
import json
import ssl
import time
from dataclasses import asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .models import JsonDict, RepoRef


class GitHubAPIError(RuntimeError):
    """Raised when GitHub cannot return the data needed for a scan."""


def parse_repo_ref(value: str) -> RepoRef:
    """Parse owner/repo, GitHub URLs, and SSH remote URLs."""
    candidate = value.strip()
    if candidate.endswith(".git"):
        candidate = candidate[:-4]

    if candidate.startswith("git@github.com:"):
        candidate = candidate.removeprefix("git@github.com:")
        parts = candidate.split("/")
    elif "://" in candidate:
        parsed = urlparse(candidate)
        if parsed.netloc.lower() != "github.com":
            raise ValueError("Only github.com repositories are supported.")
        parts = [part for part in parsed.path.strip("/").split("/") if part]
    else:
        parts = candidate.split("/")

    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError("Repository must look like owner/repo or a GitHub URL.")

    return RepoRef(parts[0], parts[1])


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        api_base: str = "https://api.github.com",
        timeout: int = 20,
        retries: int = 2,
    ) -> None:
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    def fetch_snapshot(self, ref: RepoRef, issue_limit: int = 50) -> JsonDict:
        repo_path = self._repo_path(ref)
        repo = self._get_json(repo_path)
        root_entries = self._get_optional_json(f"{repo_path}/contents") or []
        readme = self._fetch_readme(repo_path)
        root_files = sorted(
            entry.get("name", "")
            for entry in root_entries
            if isinstance(entry, dict) and entry.get("name")
        )

        files = {
            "readme": bool(readme),
            "contributing": self._exists_any(
                repo_path,
                ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"],
            ),
            "code_of_conduct": self._exists_any(
                repo_path,
                ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"],
            ),
            "license": bool(repo.get("license")),
            "issue_templates": self._path_exists(repo_path, ".github/ISSUE_TEMPLATE"),
            "workflows": self._path_exists(repo_path, ".github/workflows"),
        }

        issues = self._get_json(
            f"{repo_path}/issues?state=open&sort=updated"
            f"&direction=desc&per_page={issue_limit}"
        )
        pulls = self._get_json(
            f"{repo_path}/pulls?state=open&sort=updated"
            f"&direction=desc&per_page={issue_limit}"
        )

        return {
            "ref": asdict(ref),
            "repo": repo,
            "root_files": root_files,
            "files": files,
            "readme": readme,
            "issues": issues,
            "pulls": pulls,
        }

    def _repo_path(self, ref: RepoRef) -> str:
        owner = quote(ref.owner, safe="")
        name = quote(ref.name, safe="")
        return f"/repos/{owner}/{name}"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "PRScout/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_json(self, path: str) -> Any:
        url = f"{self.api_base}{path}"
        request = Request(url, headers=self._headers())
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code in {500, 502, 503, 504} and attempt < self.retries:
                    self._sleep_before_retry(attempt)
                    continue
                message = exc.read().decode("utf-8", errors="replace")
                if exc.code == 401:
                    raise GitHubAPIError(
                        "Authentication failed (HTTP 401). "
                        "Make sure your GitHub token is valid."
                    ) from exc
                if exc.code == 403 and "rate limit" in message.lower():
                    raise GitHubAPIError(
                        "GitHub rate limit reached. Set GITHUB_TOKEN and try again."
                    ) from exc
                if exc.code == 403:
                    raise GitHubAPIError(
                        "Access denied (HTTP 403). "
                        "You may not have permission for this resource."
                    ) from exc
                if exc.code == 404:
                    raise GitHubAPIError("Repository or API path was not found.") from exc
                if exc.code == 422:
                    raise GitHubAPIError(
                        "Request was invalid (HTTP 422). This may be a GitHub API issue."
                    ) from exc
                raise GitHubAPIError(f"GitHub API error {exc.code}: {message}") from exc
            except (
                TimeoutError,
                URLError,
                ssl.SSLError,
                http.client.RemoteDisconnected,
                OSError,
            ) as exc:
                if attempt < self.retries:
                    self._sleep_before_retry(attempt)
                    continue
                reason = getattr(exc, "reason", exc)
                raise GitHubAPIError(
                    f"Could not reach GitHub while requesting {path}. "
                    f"Network error: {reason}. Check your internet connection."
                ) from exc

        raise GitHubAPIError(
            f"Could not reach GitHub while requesting {path}. Check your internet connection."
        )

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(0.5 * (attempt + 1))

    def _get_optional_json(self, path: str) -> Any | None:
        try:
            return self._get_json(path)
        except GitHubAPIError as exc:
            if "not found" in str(exc).lower():
                return None
            raise

    def _path_exists(self, repo_path: str, path: str) -> bool:
        encoded = "/".join(quote(part, safe="") for part in path.split("/"))
        return self._get_optional_json(f"{repo_path}/contents/{encoded}") is not None

    def _exists_any(self, repo_path: str, paths: list[str]) -> bool:
        return any(self._path_exists(repo_path, path) for path in paths)

    def _fetch_readme(self, repo_path: str) -> str:
        readme = self._get_optional_json(f"{repo_path}/readme")
        if not isinstance(readme, dict) or readme.get("encoding") != "base64":
            return ""
        content = readme.get("content", "")
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except ValueError:
            return ""
