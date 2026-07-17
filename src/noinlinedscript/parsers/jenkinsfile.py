from __future__ import annotations

import re

from noinlinedscript.models import EmbeddingContext, InlineBlock, InlineLanguage, ShBlockStyle
from noinlinedscript.parsers.shellscript import parse_shell_source

_SH_TRIPLE_SINGLE = re.compile(r"""^(\s*(?:(?:def\s+)?\S+\s*=\s*)?sh\s+)'''""")
_SH_TRIPLE_DOUBLE = re.compile(r'''^(\s*(?:(?:def\s+)?\S+\s*=\s*)?sh\s+)"""''')
_SH_SCRIPT_CALL = re.compile(r"""^\s*(?:(?:def\s+)?\S+\s*=\s*)?sh\s*\(\s*script\s*:\s*""")
_SH_SINGLE_LINE = re.compile(r"""^\s*(?:(?:def\s+)?\S+\s*=\s*)?sh\s+(?=['"])""")
_TRACKED_SH = re.compile(r"^\s*trackedSh\s*\(")


def parse_jenkinsfile(file_path: str) -> list[InlineBlock]:
    with open(file_path) as f:
        lines = f.readlines()

    blocks: list[InlineBlock] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if _TRACKED_SH.match(line):
            i += 1
            continue

        result = _try_triple_quote(lines, i, file_path, "'''", ShBlockStyle.TRIPLE_SINGLE)
        if result:
            block, consumed = result
            blocks.append(block)
            _detect_nested_python(block, blocks)
            i += consumed
            continue

        result = _try_triple_quote(lines, i, file_path, '"""', ShBlockStyle.TRIPLE_DOUBLE)
        if result:
            block, consumed = result
            blocks.append(block)
            _detect_nested_python(block, blocks)
            i += consumed
            continue

        result = _try_script_call(lines, i, file_path)
        if result:
            block, consumed = result
            blocks.append(block)
            _detect_nested_python(block, blocks)
            i += consumed
            continue

        result = _try_single_line(lines, i, file_path)
        if result:
            block, consumed = result
            blocks.append(block)
            _detect_nested_python(block, blocks)
            i += consumed
            continue

        i += 1

    return blocks


def _try_triple_quote(lines: list[str], start: int, file_path: str, quote: str, style: ShBlockStyle) -> tuple[InlineBlock, int] | None:
    line = lines[start]

    pattern = _SH_TRIPLE_SINGLE if quote == "'''" else _SH_TRIPLE_DOUBLE

    m = pattern.match(line)
    if not m:
        return None

    prefix_end = m.end()
    source_parts = []
    first_content = line[prefix_end:]

    closing = first_content.find(quote)
    if closing != -1:
        source_parts.append(first_content[:closing])
        end_line = start
        consumed = 1
        remaining = first_content[closing + len(quote) :]
        if _is_concatenation(remaining):
            concat_result = _collect_concatenated(lines, start, consumed, source_parts, quote)
            if concat_result:
                consumed, end_line = concat_result
    else:
        source_parts.append(first_content.rstrip("\n"))
        consumed = 1
        end_line = start
        for j in range(start + 1, len(lines)):
            consumed += 1
            candidate = lines[j]
            closing = candidate.find(quote)
            if closing != -1:
                source_parts.append(candidate[:closing])
                end_line = j
                remaining = candidate[closing + len(quote) :]
                if _is_concatenation(remaining):
                    concat_result = _collect_concatenated(lines, start, consumed, source_parts, quote)
                    if concat_result:
                        consumed, end_line = concat_result
                break
            source_parts.append(candidate.rstrip("\n"))
            end_line = j

    source = "\n".join(source_parts)
    return InlineBlock(
        file_path=file_path,
        start_line=start + 1,
        end_line=end_line + 1,
        language=InlineLanguage.SHELL,
        embedding_context=EmbeddingContext.JENKINSFILE,
        source=source,
        block_style=style,
    ), consumed


def _is_concatenation(text: str) -> bool:
    return bool(re.match(r"""\s*\+\s*""", text.strip()))


def _collect_concatenated(lines: list[str], start: int, consumed: int, source_parts: list[str], quote: str) -> tuple[int, int] | None:
    j = start + consumed
    end_line = start + consumed - 1
    while j < len(lines):
        line = lines[j]
        consumed += 1

        open_idx = line.find(quote)
        if open_idx == -1:
            j += 1
            continue

        after_open = line[open_idx + len(quote) :]
        close_idx = after_open.find(quote)
        if close_idx != -1:
            source_parts.append(after_open[:close_idx])
            end_line = j
            remaining = after_open[close_idx + len(quote) :]
            if _is_concatenation(remaining):
                j += 1
                continue
            return consumed, end_line

        source_parts.append(after_open.rstrip("\n"))
        for k in range(j + 1, len(lines)):
            consumed += 1
            candidate = lines[k]
            closing = candidate.find(quote)
            if closing != -1:
                source_parts.append(candidate[:closing])
                end_line = k
                remaining = candidate[closing + len(quote) :]
                if _is_concatenation(remaining):
                    j = k + 1
                    break
                return consumed, end_line
            source_parts.append(candidate.rstrip("\n"))
            end_line = k
        else:
            return consumed, end_line
        continue

    return consumed, end_line


def _try_script_call(lines: list[str], start: int, file_path: str) -> tuple[InlineBlock, int] | None:
    line = lines[start]
    m = _SH_SCRIPT_CALL.match(line)
    if not m:
        return None

    after_colon = line[m.end() :]
    after_colon = after_colon.lstrip()

    for quote in ('"""', "'''"):
        if after_colon.startswith(quote):
            return _extract_script_call_triple(lines, start, file_path, quote, after_colon[len(quote) :])

    for quote_char in ('"', "'"):
        if after_colon.startswith(quote_char):
            return _extract_script_call_single(lines, start, file_path, quote_char, after_colon[1:])

    return None


def _extract_script_call_triple(lines: list[str], start: int, file_path: str, quote: str, first_content: str) -> tuple[InlineBlock, int] | None:
    source_parts = []
    consumed = 1

    closing = first_content.find(quote)
    if closing != -1:
        source_parts.append(first_content[:closing])
        end_line = start
    else:
        source_parts.append(first_content.rstrip("\n"))
        end_line = start
        for j in range(start + 1, len(lines)):
            consumed += 1
            candidate = lines[j]
            closing = candidate.find(quote)
            if closing != -1:
                source_parts.append(candidate[:closing])
                end_line = j
                break
            source_parts.append(candidate.rstrip("\n"))
            end_line = j

    source = "\n".join(source_parts)
    return InlineBlock(
        file_path=file_path,
        start_line=start + 1,
        end_line=end_line + 1,
        language=InlineLanguage.SHELL,
        embedding_context=EmbeddingContext.JENKINSFILE,
        source=source,
        block_style=ShBlockStyle.SCRIPT_CALL,
    ), consumed


def _extract_script_call_single(lines: list[str], start: int, file_path: str, quote_char: str, content: str) -> tuple[InlineBlock, int] | None:
    closing = _find_unescaped_quote(content, quote_char)
    if closing is None:
        return None

    source = content[:closing]
    return InlineBlock(
        file_path=file_path,
        start_line=start + 1,
        end_line=start + 1,
        language=InlineLanguage.SHELL,
        embedding_context=EmbeddingContext.JENKINSFILE,
        source=source,
        block_style=ShBlockStyle.SCRIPT_CALL,
    ), 1


def _try_single_line(lines: list[str], start: int, file_path: str) -> tuple[InlineBlock, int] | None:
    line = lines[start]
    m = _SH_SINGLE_LINE.match(line)
    if not m:
        return None

    after_sh = line[m.end() :]
    quote_char = after_sh[0] if after_sh else None
    if quote_char not in ('"', "'"):
        return None

    if after_sh.startswith('"""') or after_sh.startswith("'''"):
        return None

    content = after_sh[1:]
    closing = _find_unescaped_quote(content, quote_char)
    if closing is None:
        return None

    source = content[:closing]
    style = ShBlockStyle.SINGLE_DOUBLE if quote_char == '"' else ShBlockStyle.SINGLE_SINGLE

    return InlineBlock(
        file_path=file_path,
        start_line=start + 1,
        end_line=start + 1,
        language=InlineLanguage.SHELL,
        embedding_context=EmbeddingContext.JENKINSFILE,
        source=source,
        block_style=style,
    ), 1


def _find_unescaped_quote(text: str, quote_char: str) -> int | None:
    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote_char:
            return i
        i += 1
    return None


def _detect_nested_python(shell_block: InlineBlock, all_blocks: list[InlineBlock]) -> None:
    if shell_block.language != InlineLanguage.SHELL:
        return
    nested = parse_shell_source(shell_block.source, shell_block.file_path, line_offset=shell_block.start_line - 1)
    for nb in nested:
        nb.parent_block = shell_block
        all_blocks.append(nb)
