from __future__ import annotations

import re

from noinlinedscript.models import EmbeddingContext, InlineBlock, InlineLanguage, PythonEmbedStyle

_PYTHON_CMD = re.compile(r"python3?")
_HEREDOC_DELIM = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def parse_shell_script(file_path: str) -> list[InlineBlock]:
    with open(file_path) as f:
        lines = f.readlines()
    return _parse_lines(lines, file_path, EmbeddingContext.SHELL_SCRIPT)


def parse_shell_source(source: str, file_path: str, line_offset: int = 0) -> list[InlineBlock]:
    lines = source.splitlines(keepends=True)
    return _parse_lines(lines, file_path, EmbeddingContext.JENKINSFILE, line_offset)


def _parse_lines(lines: list[str], file_path: str, context: EmbeddingContext, line_offset: int = 0) -> list[InlineBlock]:
    blocks: list[InlineBlock] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        python_pos = _find_python_invocation(stripped)
        if python_pos is not None:
            rest = stripped[python_pos:]

            if _is_module_call(rest):
                i += 1
                continue

            result = _try_parse_dash_c(rest, lines, i, file_path, context, line_offset)
            if result:
                block, consumed = result
                blocks.append(block)
                i += consumed
                continue

            result = _try_parse_heredoc(rest, lines, i, file_path, context, line_offset)
            if result:
                block, consumed = result
                blocks.append(block)
                i += consumed
                continue

        i += 1
    return blocks


def _find_python_invocation(line: str) -> int | None:
    for m in re.finditer(r"\bpython3?\b", line):
        start = m.start()
        after = line[m.end() :]
        if after.startswith(" -c ") or after.startswith(" -c'") or after.startswith(' -c"'):
            return start
        if re.match(r"\s+-\s+", after) or re.match(r"\s+<<", after) or re.match(r"\s*$", after):
            if re.search(r"<<-?\s*['\"]?\w+['\"]?", after):
                return start
    return None


def _is_module_call(rest: str) -> bool:
    return bool(re.match(r"python3?\s+-m\b", rest))


def _try_parse_dash_c(rest: str, lines: list[str], line_idx: int, file_path: str, context: EmbeddingContext, line_offset: int) -> tuple[InlineBlock, int] | None:
    m = re.match(r"python3?\s+-c\s+", rest)
    if not m:
        return None

    after_flag = rest[m.end() :]
    if not after_flag:
        return None

    quote_char = after_flag[0]
    if quote_char not in ('"', "'"):
        return None

    code_start = after_flag[1:]
    source_lines = []
    consumed = 1

    closing_idx = _find_closing_quote(code_start, quote_char)
    if closing_idx is not None:
        source_lines.append(code_start[:closing_idx])
    else:
        source_lines.append(code_start.rstrip("\n"))
        for j in range(line_idx + 1, len(lines)):
            consumed += 1
            candidate = lines[j]
            closing_idx = _find_closing_quote(candidate, quote_char)
            if closing_idx is not None:
                source_lines.append(candidate[:closing_idx])
                break
            source_lines.append(candidate.rstrip("\n"))

    source = "\n".join(source_lines)
    start_line = line_idx + 1 + line_offset
    end_line = line_idx + consumed + line_offset

    return InlineBlock(
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        language=InlineLanguage.PYTHON,
        embedding_context=context,
        source=source,
        block_style=PythonEmbedStyle.DASH_C,
    ), consumed


def _find_closing_quote(text: str, quote_char: str) -> int | None:
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote_char:
            return i
        i += 1
    return None


def _try_parse_heredoc(rest: str, lines: list[str], line_idx: int, file_path: str, context: EmbeddingContext, line_offset: int) -> tuple[InlineBlock, int] | None:
    m_python = re.match(r"python3?(\s+-\s+\S.*?)?\s*", rest)
    if not m_python:
        return None

    remaining = rest[m_python.start() :]
    m_delim = _HEREDOC_DELIM.search(remaining)
    if not m_delim:
        return None

    delimiter = m_delim.group(1)
    has_stdin_dash = bool(re.search(r"\bpython3?\s+-\s+", remaining))

    style = PythonEmbedStyle.STDIN_HEREDOC if has_stdin_dash else PythonEmbedStyle.HEREDOC

    source_lines = []
    consumed = 1
    for j in range(line_idx + 1, len(lines)):
        consumed += 1
        candidate = lines[j].rstrip("\n")
        if candidate.strip() == delimiter:
            break
        source_lines.append(candidate)

    source = "\n".join(source_lines)
    start_line = line_idx + 1 + line_offset
    end_line = line_idx + consumed + line_offset

    return InlineBlock(
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        language=InlineLanguage.PYTHON,
        embedding_context=context,
        source=source,
        block_style=style,
    ), consumed
