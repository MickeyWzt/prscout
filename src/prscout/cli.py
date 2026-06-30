from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from .analysis import analyze_snapshot
from .github import GitHubAPIError, GitHubClient, parse_repo_ref
from .render import report_to_json, report_to_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prscout",
        description="Find realistic pull request entry points in a GitHub repo.",
    )
    parser.add_argument(
        "repository",
        nargs="?",
        help="Repository as owner/repo or https://github.com/owner/repo.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of issue recommendations to show. Default: 5.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a text report.",
    )
    parser.add_argument(
        "--token",
        help="GitHub token. Defaults to GITHUB_TOKEN if set.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Analyze a previously saved snapshot JSON file instead of GitHub.",
    )
    parser.add_argument(
        "--save-snapshot",
        type=Path,
        help="Save raw GitHub data to this JSON file before analysis.",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help="GitHub API base URL. Useful for tests or GitHub Enterprise.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-request GitHub timeout in seconds. Default: 30.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retries for transient GitHub network errors. Default: 2.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        snapshot = load_snapshot(args)
        report = analyze_snapshot(snapshot, recommendation_limit=args.limit)
    except (GitHubAPIError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"prscout: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(report_to_json(report))
    else:
        print(report_to_text(report))
    return 0


def load_snapshot(args: argparse.Namespace) -> dict:
    if args.snapshot:
        return json.loads(args.snapshot.read_text(encoding="utf-8"))

    if not args.repository:
        raise ValueError("Repository is required unless --snapshot is used.")

    ref = parse_repo_ref(args.repository)
    token = args.token or os.environ.get("GITHUB_TOKEN")
    client = GitHubClient(
        token=token,
        api_base=args.api_base,
        timeout=args.timeout,
        retries=args.retries,
    )
    snapshot = client.fetch_snapshot(ref, issue_limit=max(args.limit * 5, 30))

    if args.save_snapshot:
        args.save_snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.save_snapshot.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return snapshot


if __name__ == "__main__":
    raise SystemExit(main())
