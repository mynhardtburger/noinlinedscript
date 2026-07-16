from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path


@dataclass
class AllowlistEntry:
    file: str
    line: int | None = None
    reason: str = ""


@dataclass
class ToolConfig:
    max_line_count: int = 5
    max_complexity_score: float = 10.0
    allowlist: list[AllowlistEntry] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    json_output: bool = False
    verbose: bool = False

    def is_allowed(self, file_path: str, start_line: int) -> bool:
        for entry in self.allowlist:
            if fnmatch(file_path, entry.file) or file_path.endswith(entry.file):
                if entry.line is None or entry.line == start_line:
                    return True
        return False


def load_config(config_path: str | None = None) -> ToolConfig:
    if config_path:
        path = Path(config_path)
    else:
        path = _find_pyproject()

    if path is None or not path.exists():
        return ToolConfig()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    tool_data = data.get("tool", {}).get("noinlinedscript", {})
    if not tool_data:
        return ToolConfig()

    config = ToolConfig()
    if "max_line_count" in tool_data:
        config.max_line_count = int(tool_data["max_line_count"])
    if "max_complexity_score" in tool_data:
        config.max_complexity_score = float(tool_data["max_complexity_score"])
    if "exclude_patterns" in tool_data:
        config.exclude_patterns = list(tool_data["exclude_patterns"])

    for entry_data in tool_data.get("allowlist", []):
        config.allowlist.append(AllowlistEntry(
            file=entry_data["file"],
            line=entry_data.get("line"),
            reason=entry_data.get("reason", ""),
        ))

    return config


def _find_pyproject() -> Path | None:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None
