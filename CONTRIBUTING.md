# Contributing to PRScout

Thanks for considering a contribution. PRScout aims to help contributors make
useful pull requests, so this repository should model that behavior too.

## Good First Contributions

Useful small changes include:

- improving issue scoring explanations
- adding support for another project type or test command
- adding tests for GitHub URL parsing edge cases
- improving error messages for rate limits or private repositories
- documenting real examples from public repositories

## Development Setup

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest
```

Runtime code should stay dependency-free unless a dependency removes meaningful
complexity.

## Pull Request Checklist

- Keep the change focused.
- Add or update tests for behavior changes.
- Include a short explanation of the user impact.
- Mention any GitHub API behavior you relied on.

## Code Style

Use clear names and small functions. Prefer straightforward standard-library
code over clever abstractions.

