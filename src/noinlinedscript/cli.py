from __future__ import annotations

import argparse
import os
import sys

from noinlinedscript.analysis import analyze_block
from noinlinedscript.config import ToolConfig, load_config
from noinlinedscript.models import AnalyzedBlock, InlineBlock
from noinlinedscript.parsers.jenkinsfile import parse_jenkinsfile
from noinlinedscript.parsers.shellscript import parse_shell_script
from noinlinedscript.reporting import format_json, format_text, is_violation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="noinlinedscript",
        description="Detect and evaluate inline scripts in Jenkinsfiles and shell scripts",
    )
    parser.add_argument("files", nargs="*", help="Files to check (default: auto-discover)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output JSON")
    parser.add_argument("--max-lines", type=int, default=None, help="Override max line count threshold")
    parser.add_argument("--max-score", type=float, default=None, help="Override max complexity score threshold")
    parser.add_argument("--config", type=str, default=None, help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all blocks, not just violations")
    parser.add_argument("--warn", "-w", action="store_true", help="Report violations but always exit 0")
    parser.add_argument("--jenkinsfiles-only", action="store_true", help="Only check Jenkinsfiles")
    parser.add_argument("--shellscripts-only", action="store_true", help="Only check shell scripts")

    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.max_lines is not None:
        config.max_line_count = args.max_lines
    if args.max_score is not None:
        config.max_complexity_score = args.max_score
    if args.json_output:
        config.json_output = True
    if args.verbose:
        config.verbose = True
    if args.warn:
        config.warn = True

    files = args.files if args.files else _discover_files()

    if args.jenkinsfiles_only:
        files = [f for f in files if _is_jenkinsfile(f)]
    elif args.shellscripts_only:
        files = [f for f in files if _is_shell_script(f)]

    all_blocks: list[InlineBlock] = []
    for file_path in files:
        try:
            if _is_jenkinsfile(file_path):
                all_blocks.extend(parse_jenkinsfile(file_path))
            elif _is_shell_script(file_path):
                all_blocks.extend(parse_shell_script(file_path))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}", file=sys.stderr)

    results = [analyze_block(b) for b in all_blocks]
    results = _apply_excludes(results, config)

    output_stream = sys.stderr if config.warn else sys.stdout
    if config.json_output:
        print(format_json(results, config), file=output_stream)
    else:
        print(format_text(results, config, verbose=config.verbose), file=output_stream)

    if config.warn:
        return 0
    violations = [r for r in results if is_violation(r, config)]
    return 1 if violations else 0


def _is_jenkinsfile(path: str) -> bool:
    basename = os.path.basename(path)
    return basename.startswith("Jenkinsfile")


def _is_shell_script(path: str) -> bool:
    return path.endswith(".sh")


def _discover_files() -> list[str]:
    files = []
    for root, _dirs, filenames in os.walk("."):
        for name in filenames:
            full = os.path.join(root, name)
            if _is_jenkinsfile(full) or _is_shell_script(full):
                files.append(full)
    return sorted(files)


def _apply_excludes(results: list[AnalyzedBlock], config: ToolConfig) -> list[AnalyzedBlock]:
    if not config.exclude_patterns:
        return results
    filtered = []
    for r in results:
        excluded = False
        for pattern in config.exclude_patterns:
            if pattern in r.block.source:
                excluded = True
                break
        if not excluded:
            filtered.append(r)
    return filtered
