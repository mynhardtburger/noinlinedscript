# noinlinedscript

Detects inline shell/python scripts in Jenkinsfiles and inline Python in shell scripts, evaluates their complexity, and flags blocks that should be extracted into standalone files for proper linting.

## Install

```
uv pip install .
```

## Usage

```
noinlinedscript Jenkinsfile.* scripts/*.sh
```

```
Jenkinsfile.test:191-268  [shell in jenkinsfile]  triple_double_quote  (VIOLATION)
  Lines: 70  Score: 92.5
  Shell: 2 pipes, 5 cmd-subst, 3 conditionals, 2 loops, cmds: oc

scripts/update-build-status.sh:48-134  [python in shell script]  stdin_heredoc  (VIOLATION)
  Lines: 74  Score: 75.0
  Python: 1 imports

Summary: 12 inline blocks found, 2 exceed thresholds
```

Auto-discover all `Jenkinsfile*` and `*.sh` in the current tree:

```
noinlinedscript
```

## Pre-commit

```yaml
- repo: https://github.com/OWNER/noinlinedscript
  rev: v0.1.0
  hooks:
    - id: noinlinedscript
```

During a transition period, add `args: [--warn]` to report without blocking:

```yaml
    - id: noinlinedscript
      args: [--warn]
```

For local development without a remote repo:

```yaml
- repo: local
  hooks:
    - id: noinlinedscript
      name: no-inline-scripts
      entry: noinlinedscript
      language: python
      files: '(Jenkinsfile.*|\.sh)$'
```

## Parameters

| Flag | Description |
|------|-------------|
| `--warn`, `-w` | Report violations but always exit 0 (for transition periods) |
| `--json` | JSON output instead of human-readable |
| `--verbose`, `-v` | Show all blocks, not just violations |
| `--max-lines N` | Override max line count threshold (default: 5) |
| `--max-score N` | Override max complexity score threshold (default: 10.0) |
| `--config PATH` | Path to config file (default: nearest `pyproject.toml`) |
| `--jenkinsfiles-only` | Only check Jenkinsfiles |
| `--shellscripts-only` | Only check shell scripts |

## Configuration

In `pyproject.toml`:

```toml
[tool.noinlinedscript]
max_line_count = 5
max_complexity_score = 10.0
exclude_patterns = ["python3 -m"]

[[tool.noinlinedscript.allowlist]]
file = "scripts/_lib.sh"
line = 220
reason = "Simple JSON field extraction"
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No violations |
| 1 | Violations found |
| 2 | Error |
