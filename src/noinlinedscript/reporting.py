from __future__ import annotations

import json
from pathlib import Path

from noinlinedscript.config import ToolConfig
from noinlinedscript.models import AnalyzedBlock


def is_violation(block: AnalyzedBlock, config: ToolConfig) -> bool:
    if config.is_allowed(block.block.file_path, block.block.start_line):
        return False
    return block.complexity.line_count > config.max_line_count or block.complexity.complexity_score > config.max_complexity_score


def format_text(results: list[AnalyzedBlock], config: ToolConfig, verbose: bool = False) -> str:
    violations = [r for r in results if is_violation(r, config)]
    items = results if verbose else violations

    lines: list[str] = []
    for item in items:
        b = item.block
        c = item.complexity
        violation = is_violation(item, config)

        rel_path = _relative_path(b.file_path)
        ctx = _context_label(item)
        style = b.block_style.value if b.block_style else "unknown"

        marker = ("WARNING" if config.warn else "VIOLATION") if violation else "ok"
        lines.append(f"{rel_path}:{b.start_line}-{b.end_line}  [{ctx}]  {style}  ({marker})")
        lines.append(f"  Lines: {c.line_count}  Score: {c.complexity_score:.1f}")

        if c.shell_features:
            sf = c.shell_features
            parts = []
            if sf.pipe_count:
                parts.append(f"{sf.pipe_count} pipes")
            if sf.command_substitution_count:
                parts.append(f"{sf.command_substitution_count} cmd-subst")
            if sf.conditional_count:
                parts.append(f"{sf.conditional_count} conditionals")
            if sf.loop_count:
                parts.append(f"{sf.loop_count} loops")
            if sf.heredoc_count:
                parts.append(f"{sf.heredoc_count} heredocs")
            if sf.process_substitution_count:
                parts.append(f"{sf.process_substitution_count} proc-subst")
            if sf.external_commands:
                parts.append(f"cmds: {', '.join(sf.external_commands)}")
            if parts:
                lines.append(f"  Shell: {', '.join(parts)}")

        if c.python_features:
            pf = c.python_features
            parts = []
            if pf.import_count:
                parts.append(f"{pf.import_count} imports")
            if pf.function_def_count:
                parts.append(f"{pf.function_def_count} functions")
            if pf.class_def_count:
                parts.append(f"{pf.class_def_count} classes")
            if pf.try_except_count:
                parts.append(f"{pf.try_except_count} try/except")
            if parts:
                lines.append(f"  Python: {', '.join(parts)}")

        if b.parent_block:
            lines.append(f"  Nested in: {b.parent_block.language.value} block at line {b.parent_block.start_line}")

        lines.append("")

    if not config.no_summary:
        total = len(results)
        violation_count = len(violations)
        lines.append(f"Summary: {total} inline blocks found, {violation_count} exceed thresholds")
        lines.append(f"  Thresholds: max_line_count={config.max_line_count}, max_complexity_score={config.max_complexity_score}")

    if violations and config.guidance:
        lines.append("")
        lines.append(config.guidance)

    return "\n".join(lines)


def format_json(results: list[AnalyzedBlock], config: ToolConfig) -> str:
    violations = [r for r in results if is_violation(r, config)]

    blocks_data = []
    for item in results:
        b = item.block
        c = item.complexity
        block_data = {
            "file": _relative_path(b.file_path),
            "start_line": b.start_line,
            "end_line": b.end_line,
            "language": b.language.value,
            "embedding_context": b.embedding_context.value,
            "block_style": b.block_style.value if b.block_style else None,
            "line_count": c.line_count,
            "total_lines": c.total_lines,
            "complexity_score": c.complexity_score,
            "is_violation": is_violation(item, config),
        }

        if c.shell_features:
            sf = c.shell_features
            block_data["shell_features"] = {
                "pipe_count": sf.pipe_count,
                "command_substitution_count": sf.command_substitution_count,
                "conditional_count": sf.conditional_count,
                "loop_count": sf.loop_count,
                "heredoc_count": sf.heredoc_count,
                "process_substitution_count": sf.process_substitution_count,
                "external_commands": sf.external_commands,
            }

        if c.python_features:
            pf = c.python_features
            block_data["python_features"] = {
                "import_count": pf.import_count,
                "function_def_count": pf.function_def_count,
                "class_def_count": pf.class_def_count,
                "try_except_count": pf.try_except_count,
            }

        if b.parent_block:
            block_data["nested_in"] = {
                "language": b.parent_block.language.value,
                "start_line": b.parent_block.start_line,
            }

        blocks_data.append(block_data)

    output: dict = {
        "blocks": blocks_data,
        "config": {
            "max_line_count": config.max_line_count,
            "max_complexity_score": config.max_complexity_score,
            "warn": config.warn,
        },
    }
    if not config.no_summary:
        output["summary"] = {
            "total_blocks": len(results),
            "violations": len(violations),
        }
    if violations and config.guidance:
        output["guidance"] = config.guidance

    return json.dumps(output, indent=2)


def _context_label(item: AnalyzedBlock) -> str:
    b = item.block
    lang = b.language.value
    ctx = b.embedding_context.value.replace("_", " ")
    return f"{lang} in {ctx}"


def _relative_path(file_path: str) -> str:
    try:
        return str(Path(file_path).relative_to(Path.cwd()))
    except ValueError:
        return file_path
