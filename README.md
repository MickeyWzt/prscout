# PRScout

[![CI](https://github.com/MickeyWzt/prscout/actions/workflows/ci.yml/badge.svg)](https://github.com/MickeyWzt/prscout/actions/workflows/ci.yml)

PRScout helps developers find realistic pull request entry points in GitHub
repositories.

Instead of only scoring repository health, PRScout asks a more practical
question:

> "Is this repository a good place for a careful newcomer to make a useful PR
> today, and where should they start?"

It checks repository activity, contribution signals, test hints, open issues,
and duplicate-PR risk, then recommends the most promising issues with a short
reasoning trail.

## Why This Exists

Many "good first issue" labels are noisy. Some issues already have active PRs.
Some repositories look popular but are inactive or hard to test. PRScout is a
small command-line assistant for contributors who want to avoid drive-by spam
and find work that maintainers are more likely to appreciate.

## Install

From PyPI:

```bash
python -m pip install prscout
```

For local development from a checkout:

```bash
python -m pip install -e .
```

PRScout uses only the Python standard library at runtime.

## Quick Start

Scan a repository:

```bash
prscout ev-flow/quark-engine
```

GitHub API requests work without a token for light use, but a token is
recommended:

```bash
set GITHUB_TOKEN=ghp_your_token_here
prscout ev-flow/quark-engine
```

On macOS/Linux:

```bash
export GITHUB_TOKEN=ghp_your_token_here
prscout ev-flow/quark-engine
```

You can also pass a full URL:

```bash
prscout https://github.com/ev-flow/quark-engine
```

JSON output is available for automation:

```bash
prscout ev-flow/quark-engine --json
```

Require stronger issue recommendations:

```bash
prscout ev-flow/quark-engine --min-fit 70
```

Try the bundled offline example without calling GitHub:

```bash
prscout --snapshot docs/examples/sample-snapshot.json
```

## What PRScout Looks For

PRScout favors repositories that have:

- recent maintenance activity
- a README, license, and contribution guide
- issue templates or GitHub Actions workflows
- open issues with clear scope, low comment noise, and helpful labels
- no obvious open PR already covering the same issue

It flags risks such as archived repositories, stale activity, missing
contribution docs, and noisy or already-contested issues.

## Example Output

```text
PRScout report for ev-flow/quark-engine
Score: 76/100 - promising

Best entry points
1. #936 -- `--rule` default path validated even when unused
   Fit: 88/100 | Risk: low
   Why: bug label, clear reproduction, low discussion, no obvious duplicate PR

Contributor checklist
- Read the contribution guide if present.
- Check open PRs for overlap before coding.
- Reproduce the issue locally.
- Keep the fix narrow and add a regression test.
```

## Development

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest
```

## Roadmap

- Detect more test commands from package files.
- Add `--save-snapshot` for reproducible offline reports.
- Add maintainer-friendly issue quality explanations.
- Add a small web demo after the CLI stabilizes.

## Contributing

PRScout is intentionally small. Good first contributions include better issue
scoring rules, more repository metadata signals, clearer output, and tests for
edge cases. See [CONTRIBUTING.md](CONTRIBUTING.md).
