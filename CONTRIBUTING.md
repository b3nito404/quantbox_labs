# Development conventions

This document describes the conventions used across the QuantBox Labs codebase. It will
grow as the project matures.

## Branching model

The `main` branch must always remain stable and pass continuous integration. New work
happens on short lived branches named `feature/short-description`, for example
`feature/backtest-engine`. Changes are merged into `main` through pull requests, even
when working alone. This keeps a review step and a passing CI run before any change
lands on the main branch.

## Commit messages

Commit messages are written in English, in the imperative mood, and follow the
Conventional Commits format.

```
feat: add half life calculation for mean reverting spreads
fix: correct zscore window to exclude the current point twice
docs: update the QB01 README with CLI usage
test: add edge cases for generate_signals
chore: update CI workflow to cache pip dependencies
```

## Pull requests

Pull request titles follow the same convention as commit messages. The description
should state what changed, why it changed, and how it was verified, for example which
tests were added or which manual checks were performed.

## Before committing

Run the following from the `qb01` directory before pushing any change.

```bash
ruff check . --fix
mypy quantbox
pytest
```

Continuous integration runs the same checks on every push and pull request. Verifying
locally first avoids unnecessary CI failures.

## Adding a Python dependency

Dependencies are declared in `qb01/pyproject.toml`, never installed ad hoc without being
recorded. After editing the file, reinstall the package locally.

```bash
pip install -e ".[dev]"
```

## Testing expectations

Every new research module, indicator, or strategy component should be accompanied by at
least a minimal test in `qb01/tests/`. The goal is not exhaustive coverage but catching
logic errors early, in particular look ahead bias and incorrect statistical
calculations.
