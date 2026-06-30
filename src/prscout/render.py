from __future__ import annotations

import json
from dataclasses import asdict

from .models import RepoReport


def report_to_json(report: RepoReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True)


def report_to_text(report: RepoReport) -> str:
    lines = [
        f"PRScout report for {report.repository}",
        f"Score: {report.score}/100 - {report.verdict}",
        "",
    ]

    if report.summary:
        lines.append("Why this may be a good target")
        for item in report.summary:
            lines.append(f"- {item}")
        lines.append("")

    if report.risks:
        lines.append("Risks to check")
        for item in report.risks:
            lines.append(f"- {item}")
        lines.append("")

    if report.test_commands:
        lines.append("Likely test commands")
        for command in report.test_commands:
            lines.append(f"- {command}")
        lines.append("")

    lines.append("Best entry points")
    if not report.recommendations:
        lines.append("- No strong candidates found in the scanned open issues.")
    else:
        for index, issue in enumerate(report.recommendations, start=1):
            lines.append(
                f"{index}. #{issue.number} -- {issue.title}\n"
                f"   Fit: {issue.fit}/100 | Risk: {issue.risk}"
            )
            if issue.labels:
                lines.append(f"   Labels: {', '.join(issue.labels)}")
            if issue.why:
                lines.append(f"   Why: {', '.join(issue.why)}")
            if issue.watch_out:
                lines.append(f"   Watch out: {', '.join(issue.watch_out)}")
            if issue.url:
                lines.append(f"   Link: {issue.url}")
    lines.append("")

    lines.append("Contributor checklist")
    for item in report.checklist:
        lines.append(f"- {item}")

    return "\n".join(lines)

