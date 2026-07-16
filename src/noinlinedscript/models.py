from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class InlineLanguage(Enum):
    SHELL = "shell"
    PYTHON = "python"


class EmbeddingContext(Enum):
    JENKINSFILE = "jenkinsfile"
    SHELL_SCRIPT = "shell_script"


class ShBlockStyle(Enum):
    TRIPLE_SINGLE = "triple_single_quote"
    TRIPLE_DOUBLE = "triple_double_quote"
    SINGLE_SINGLE = "single_single_quote"
    SINGLE_DOUBLE = "single_double_quote"
    SCRIPT_CALL = "script_call"


class PythonEmbedStyle(Enum):
    DASH_C = "dash_c"
    HEREDOC = "heredoc"
    STDIN_HEREDOC = "stdin_heredoc"


@dataclass
class InlineBlock:
    file_path: str
    start_line: int
    end_line: int
    language: InlineLanguage
    embedding_context: EmbeddingContext
    source: str
    block_style: ShBlockStyle | PythonEmbedStyle | None = None
    parent_block: InlineBlock | None = None


@dataclass
class ShellFeatures:
    pipe_count: int = 0
    command_substitution_count: int = 0
    conditional_count: int = 0
    loop_count: int = 0
    heredoc_count: int = 0
    process_substitution_count: int = 0
    external_commands: list[str] = field(default_factory=list)


@dataclass
class PythonFeatures:
    import_count: int = 0
    function_def_count: int = 0
    class_def_count: int = 0
    try_except_count: int = 0


@dataclass
class ComplexityResult:
    line_count: int
    total_lines: int
    shell_features: ShellFeatures | None = None
    python_features: PythonFeatures | None = None
    complexity_score: float = 0.0


@dataclass
class AnalyzedBlock:
    block: InlineBlock
    complexity: ComplexityResult
