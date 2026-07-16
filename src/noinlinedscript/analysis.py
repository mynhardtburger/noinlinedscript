from __future__ import annotations

import re

from noinlinedscript.models import (
    AnalyzedBlock,
    ComplexityResult,
    InlineBlock,
    InlineLanguage,
    PythonFeatures,
    ShellFeatures,
)

KNOWN_EXTERNAL_COMMANDS = frozenset({
    "oc", "kubectl", "kustomize", "helm",
    "aws", "mc", "skopeo",
    "jq", "yq",
    "make", "go", "npm",
    "curl", "wget",
    "git", "sed", "awk", "grep", "find",
    "base64", "openssl", "htpasswd",
    "tar", "unzip", "zip",
    "docker", "podman",
})


def analyze_block(block: InlineBlock) -> AnalyzedBlock:
    total_lines = _count_total_lines(block.source)
    line_count = _count_effective_lines(block.source, block.language)

    if block.language == InlineLanguage.SHELL:
        features = _analyze_shell(block.source)
        score = _score_shell(line_count, features)
        return AnalyzedBlock(
            block=block,
            complexity=ComplexityResult(
                line_count=line_count,
                total_lines=total_lines,
                shell_features=features,
                complexity_score=score,
            ),
        )
    else:
        features = _analyze_python(block.source)
        score = _score_python(line_count, features)
        return AnalyzedBlock(
            block=block,
            complexity=ComplexityResult(
                line_count=line_count,
                total_lines=total_lines,
                python_features=features,
                complexity_score=score,
            ),
        )


def _count_total_lines(source: str) -> int:
    lines = source.strip().splitlines()
    return len(lines)


def _count_effective_lines(source: str, language: InlineLanguage) -> int:
    count = 0
    for line in source.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and not stripped.startswith("#!"):
            continue
        count += 1
    return count


def _analyze_shell(source: str) -> ShellFeatures:
    lines = source.splitlines()

    pipe_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        pipe_count += len(re.findall(r"(?<!\|)\|(?!\|)", stripped))

    cmd_sub_count = sum(1 for line in lines for _ in re.finditer(r"\$\(", line))

    conditional_count = sum(1 for line in lines if re.match(r"\s*(if|case)\b", line))
    loop_count = sum(1 for line in lines if re.match(r"\s*(for|while)\b", line))

    heredoc_count = sum(1 for line in lines for _ in re.finditer(r"<<-?\s*['\"]?\w+", line))

    proc_sub_count = sum(1 for line in lines for _ in re.finditer(r"[<>]\(", line))

    external_commands = _detect_external_commands(source)

    return ShellFeatures(
        pipe_count=pipe_count,
        command_substitution_count=cmd_sub_count,
        conditional_count=conditional_count,
        loop_count=loop_count,
        heredoc_count=heredoc_count,
        process_substitution_count=proc_sub_count,
        external_commands=external_commands,
    )


def _detect_external_commands(source: str) -> list[str]:
    found = set()
    for cmd in KNOWN_EXTERNAL_COMMANDS:
        if re.search(rf"\b{re.escape(cmd)}\b", source):
            found.add(cmd)
    return sorted(found)


def _analyze_python(source: str) -> PythonFeatures:
    lines = source.splitlines()

    import_count = sum(1 for line in lines if re.match(r"\s*(import|from\s+\S+\s+import)\b", line))
    func_def_count = sum(1 for line in lines if re.match(r"\s*def\s+", line))
    class_def_count = sum(1 for line in lines if re.match(r"\s*class\s+", line))
    try_except_count = sum(1 for line in lines if re.match(r"\s*try\s*:", line))

    return PythonFeatures(
        import_count=import_count,
        function_def_count=func_def_count,
        class_def_count=class_def_count,
        try_except_count=try_except_count,
    )


def _score_shell(line_count: int, features: ShellFeatures) -> float:
    return (
        line_count * 1.0
        + features.pipe_count * 1.5
        + features.command_substitution_count * 1.0
        + features.conditional_count * 2.0
        + features.loop_count * 3.0
        + features.heredoc_count * 2.0
        + features.process_substitution_count * 2.0
        + len(features.external_commands) * 0.5
    )


def _score_python(line_count: int, features: PythonFeatures) -> float:
    return (
        line_count * 1.0
        + features.import_count * 1.0
        + features.function_def_count * 3.0
        + features.class_def_count * 5.0
        + features.try_except_count * 2.0
    )
