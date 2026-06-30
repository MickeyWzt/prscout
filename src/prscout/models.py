from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass
class IssueRecommendation:
    number: int
    title: str
    url: str
    fit: int
    risk: str
    labels: list[str] = field(default_factory=list)
    why: list[str] = field(default_factory=list)
    watch_out: list[str] = field(default_factory=list)


@dataclass
class RepoReport:
    repository: str
    score: int
    verdict: str
    summary: list[str]
    risks: list[str]
    test_commands: list[str]
    recommendations: list[IssueRecommendation]
    checklist: list[str]

