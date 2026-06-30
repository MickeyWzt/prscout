from prscout.analysis import analyze_snapshot, detect_test_commands, score_issue


def test_detect_test_commands_from_files_and_readme():
    commands = detect_test_commands(
        ["pyproject.toml", "package.json", "go.mod"],
        "Run pnpm test for frontend checks.",
    )

    assert commands == ["python -m pytest", "pnpm test", "go test ./..."]


def test_score_issue_rewards_clear_beginner_bug():
    issue = {
        "number": 7,
        "title": "CLI crashes when config is missing",
        "html_url": "https://github.com/example/project/issues/7",
        "body": (
            "Steps to reproduce:\n"
            "1. Run the CLI with a missing config file.\n"
            "2. Observe the traceback.\n\n"
            "Expected behavior: print a clear configuration error.\n"
            "Actual behavior: the command crashes with a traceback."
        ),
        "labels": [{"name": "good first issue"}, {"name": "bug"}],
        "comments": 0,
        "assignees": [],
        "updated_at": "2999-01-01T00:00:00Z",
    }

    result = score_issue(issue, pulls=[])

    assert result.fit >= 75
    assert result.risk == "low"
    assert "beginner-friendly label" in result.why
    assert "bug label" in result.why


def test_score_issue_penalizes_possible_duplicate_pr():
    issue = {
        "number": 9,
        "title": "Fix Windows path separator handling",
        "body": "Expected behavior and actual behavior are documented.",
        "labels": [{"name": "good first issue"}, {"name": "bug"}],
        "comments": 0,
        "assignees": [],
        "updated_at": "2999-01-01T00:00:00Z",
    }
    pulls = [
        {
            "title": "Fix Windows path separator handling",
            "body": "Closes #9",
        }
    ]

    result = score_issue(issue, pulls=pulls)

    assert result.fit < 75
    assert "possible open PR overlap" in result.watch_out


def test_analyze_snapshot_returns_ranked_recommendation():
    snapshot = {
        "ref": {"owner": "example", "name": "project"},
        "repo": {
            "full_name": "example/project",
            "archived": False,
            "pushed_at": "2999-01-01T00:00:00Z",
            "license": {"key": "mit"},
        },
        "root_files": ["pyproject.toml"],
        "files": {
            "readme": True,
            "contributing": True,
            "license": True,
            "issue_templates": True,
            "workflows": True,
        },
        "readme": "Run pytest.",
        "issues": [
            {
                "number": 1,
                "title": "Add a regression test for parser errors",
                "html_url": "https://github.com/example/project/issues/1",
                "body": "Steps to reproduce and expected behavior are clear.",
                "labels": [{"name": "good first issue"}, {"name": "bug"}],
                "comments": 0,
                "assignees": [],
                "updated_at": "2999-01-01T00:00:00Z",
            }
        ],
        "pulls": [],
    }

    report = analyze_snapshot(snapshot)

    assert report.repository == "example/project"
    assert report.verdict in {"promising", "strong"}
    assert report.recommendations[0].number == 1
    assert "python -m pytest" in report.test_commands
