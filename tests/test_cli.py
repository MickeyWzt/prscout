import json

import pytest

from prscout.cli import main


def write_snapshot(path):
    path.write_text(
        json.dumps(
            {
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
                    "contributing": False,
                    "license": True,
                    "issue_templates": False,
                    "workflows": True,
                },
                "readme": "Run pytest.",
                "issues": [
                    {
                        "number": 42,
                        "title": "CLI should explain rate limits",
                        "html_url": "https://github.com/example/project/issues/42",
                        "body": "Steps to reproduce and expected behavior are clear.",
                        "labels": [{"name": "good first issue"}, {"name": "bug"}],
                        "comments": 0,
                        "assignees": [],
                        "updated_at": "2999-01-01T00:00:00Z",
                    }
                ],
                "pulls": [],
            }
        ),
        encoding="utf-8",
    )


def test_cli_snapshot_text_output(tmp_path, capsys):
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot)

    exit_code = main(["--snapshot", str(snapshot)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PRScout report for example/project" in captured.out
    assert "#42 -- CLI should explain rate limits" in captured.out


def test_cli_snapshot_json_output(tmp_path, capsys):
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot)

    exit_code = main(["--snapshot", str(snapshot), "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["repository"] == "example/project"
    assert data["recommendations"][0]["number"] == 42


def test_cli_rejects_out_of_range_min_fit(tmp_path):
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot)

    with pytest.raises(SystemExit):
        main(["--snapshot", str(snapshot), "--min-fit", "101"])

