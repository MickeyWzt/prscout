from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .models import IssueRecommendation, JsonDict, RepoReport


CHECKLIST = [
    "Read the contribution guide if present.",
    "Check open PRs for overlap before coding.",
    "Reproduce the issue locally.",
    "Keep the fix narrow and add a regression test.",
    "Write a PR body that explains root cause, change, and validation.",
]

BEGINNER_LABELS = {
    "good first issue",
    "good-first-issue",
    "beginner",
    "beginner-friendly",
    "easy",
    "first-timers-only",
}
HELP_LABELS = {"help wanted", "up-for-grabs", "contributions welcome"}
BUG_LABELS = {"bug", "defect", "regression"}
DOC_LABELS = {"documentation", "docs"}


def analyze_snapshot(snapshot: JsonDict, recommendation_limit: int = 5) -> RepoReport:
    repo = snapshot.get("repo", {})
    files = snapshot.get("files", {})
    root_files = snapshot.get("root_files", [])
    readme = snapshot.get("readme", "")
    issues = snapshot.get("issues", [])
    pulls = snapshot.get("pulls", [])

    recommendations = recommend_issues(issues, pulls, recommendation_limit)
    test_commands = detect_test_commands(root_files, readme)
    score, summary, risks = score_repository(repo, files, recommendations)

    return RepoReport(
        repository=repo.get("full_name") or _snapshot_full_name(snapshot),
        score=score,
        verdict=verdict_for(score),
        summary=summary,
        risks=risks,
        test_commands=test_commands,
        recommendations=recommendations,
        checklist=CHECKLIST,
    )


def score_repository(
    repo: JsonDict,
    files: JsonDict,
    recommendations: list[IssueRecommendation],
) -> tuple[int, list[str], list[str]]:
    score = 45
    summary: list[str] = []
    risks: list[str] = []

    if repo.get("archived"):
        score -= 45
        risks.append("Repository is archived.")
    else:
        score += 8
        summary.append("Repository is not archived.")

    pushed_days = days_since(repo.get("pushed_at"))
    if pushed_days is None:
        risks.append("Could not determine recent maintenance activity.")
    elif pushed_days <= 30:
        score += 16
        summary.append(f"Maintained recently; last push was {pushed_days} days ago.")
    elif pushed_days <= 180:
        score += 8
        summary.append(f"Some recent activity; last push was {pushed_days} days ago.")
    else:
        score -= 12
        risks.append(f"Repository looks stale; last push was {pushed_days} days ago.")

    if files.get("readme"):
        score += 8
        summary.append("README is present.")
    else:
        score -= 10
        risks.append("README was not found.")

    if files.get("license"):
        score += 7
        summary.append("License metadata is present.")
    else:
        risks.append("License metadata was not found.")

    if files.get("contributing"):
        score += 10
        summary.append("Contribution guide is present.")
    else:
        score -= 4
        risks.append("Contribution guide was not found.")

    if files.get("issue_templates"):
        score += 5
        summary.append("Issue templates are present.")
    if files.get("workflows"):
        score += 5
        summary.append("GitHub Actions workflows are present.")

    if recommendations:
        score += min(12, 4 + len(recommendations) * 2)
        summary.append(f"Found {len(recommendations)} promising issue candidates.")
    else:
        score -= 10
        risks.append("No promising open issue candidates were found.")

    return clamp(score), summary, risks


def recommend_issues(
    issues: list[JsonDict],
    pulls: list[JsonDict],
    limit: int,
) -> list[IssueRecommendation]:
    scored = []
    for issue in issues:
        if issue.get("pull_request"):
            continue
        recommendation = score_issue(issue, pulls)
        if recommendation.fit >= 45:
            scored.append(recommendation)

    scored.sort(key=lambda item: item.fit, reverse=True)
    return scored[:limit]


def score_issue(issue: JsonDict, pulls: list[JsonDict]) -> IssueRecommendation:
    labels = label_names(issue)
    label_set = set(labels)
    body = issue.get("body") or ""
    title = issue.get("title") or ""
    score = 20
    why: list[str] = []
    watch_out: list[str] = []

    if label_set & BEGINNER_LABELS:
        score += 26
        why.append("beginner-friendly label")
    if label_set & HELP_LABELS:
        score += 18
        why.append("help-wanted label")
    if label_set & BUG_LABELS:
        score += 16
        why.append("bug label")
    if label_set & DOC_LABELS:
        score += 10
        why.append("documentation label")

    if len(body) >= 500:
        score += 16
        why.append("detailed issue body")
    elif len(body) >= 150:
        score += 8
        why.append("some issue detail")
    else:
        score -= 10
        watch_out.append("thin issue description")

    if has_reproduction_language(body):
        score += 12
        why.append("clear reproduction or expected behavior")

    if issue.get("assignees"):
        score -= 12
        watch_out.append("already assigned")
    else:
        score += 8
        why.append("not assigned")

    comments = int(issue.get("comments") or issue.get("commentsCount") or 0)
    if comments == 0:
        score += 8
        why.append("no discussion noise")
    elif comments <= 2:
        score += 4
        why.append("low discussion noise")
    elif comments >= 8:
        score -= 10
        watch_out.append("long discussion thread")

    updated_days = days_since(issue.get("updated_at") or issue.get("updatedAt"))
    if updated_days is not None and updated_days <= 90:
        score += 8
        why.append("recently updated")
    elif updated_days is not None and updated_days > 365:
        score -= 10
        watch_out.append("stale issue")

    if has_obvious_duplicate_pr(issue, pulls):
        score -= 35
        watch_out.append("possible open PR overlap")
    else:
        why.append("no obvious duplicate PR")

    fit = clamp(score)
    risk = "low" if fit >= 75 and not watch_out else "medium" if fit >= 55 else "high"

    return IssueRecommendation(
        number=int(issue.get("number") or 0),
        title=title,
        url=issue.get("html_url") or issue.get("url") or "",
        fit=fit,
        risk=risk,
        labels=labels,
        why=why[:5],
        watch_out=watch_out[:4],
    )


def detect_test_commands(root_files: list[str], readme: str) -> list[str]:
    files = {name.lower() for name in root_files}
    text = readme.lower()
    commands: list[str] = []

    if "pytest" in text or "pyproject.toml" in files or "setup.py" in files:
        commands.append("python -m pytest")
    if "package.json" in files:
        if "pnpm test" in text:
            commands.append("pnpm test")
        elif "yarn test" in text:
            commands.append("yarn test")
        else:
            commands.append("npm test")
    if "cargo.toml" in files:
        commands.append("cargo test")
    if "go.mod" in files:
        commands.append("go test ./...")
    if "pom.xml" in files:
        commands.append("mvn test")
    if "build.gradle" in files or "build.gradle.kts" in files:
        commands.append("./gradlew test")

    return dedupe(commands)


def has_reproduction_language(text: str) -> bool:
    lowered = text.lower()
    signals = [
        "to reproduce",
        "steps to reproduce",
        "expected behavior",
        "actual behavior",
        "expected results",
        "actual results",
        "root cause",
        "traceback",
    ]
    return any(signal in lowered for signal in signals)


def has_obvious_duplicate_pr(issue: JsonDict, pulls: list[JsonDict]) -> bool:
    issue_number = str(issue.get("number") or "")
    issue_title = issue.get("title") or ""
    issue_tokens = tokenize(issue_title)

    for pull in pulls:
        haystack = f"{pull.get('title', '')} {pull.get('body', '')}".lower()
        if issue_number and f"#{issue_number}" in haystack:
            return True
        pr_tokens = tokenize(haystack)
        if issue_tokens and len(issue_tokens & pr_tokens) / len(issue_tokens) >= 0.6:
            return True
    return False


def label_names(issue: JsonDict) -> list[str]:
    labels = []
    for label in issue.get("labels", []):
        if isinstance(label, dict) and label.get("name"):
            labels.append(str(label["name"]).lower())
        elif isinstance(label, str):
            labels.append(label.lower())
    return labels


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 4
    }


def days_since(value: Any) -> int | None:
    if not value:
        return None
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            moment = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    elif isinstance(value, datetime):
        moment = value
    else:
        return None

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - moment.astimezone(timezone.utc)
    return max(0, delta.days)


def verdict_for(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 65:
        return "promising"
    if score >= 45:
        return "mixed"
    return "risky"


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(value)))


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _snapshot_full_name(snapshot: JsonDict) -> str:
    ref = snapshot.get("ref", {})
    if ref.get("owner") and ref.get("name"):
        return f"{ref['owner']}/{ref['name']}"
    return "unknown/repository"

