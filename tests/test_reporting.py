import json

from noinlinedscript.analysis import analyze_block
from noinlinedscript.config import ToolConfig
from noinlinedscript.models import EmbeddingContext, InlineBlock, InlineLanguage, ShBlockStyle
from noinlinedscript.reporting import format_json, format_text, is_violation


def _make_analyzed(source: str, line_count_override: int | None = None):
    block = InlineBlock(
        file_path="Jenkinsfile.test",
        start_line=10,
        end_line=20,
        language=InlineLanguage.SHELL,
        embedding_context=EmbeddingContext.JENKINSFILE,
        source=source,
        block_style=ShBlockStyle.TRIPLE_SINGLE,
    )
    return analyze_block(block)


class TestIsViolation:
    def test_below_threshold(self):
        result = _make_analyzed("echo hello")
        config = ToolConfig(max_line_count=5, max_complexity_score=10.0)
        assert not is_violation(result, config)

    def test_exceeds_line_count(self):
        source = "\n".join(f"echo line{i}" for i in range(10))
        result = _make_analyzed(source)
        config = ToolConfig(max_line_count=5, max_complexity_score=100.0)
        assert is_violation(result, config)

    def test_exceeds_score(self):
        source = "oc get pods | grep running\nfor i in $(seq 1 10); do\n  curl url\ndone"
        result = _make_analyzed(source)
        config = ToolConfig(max_line_count=100, max_complexity_score=5.0)
        assert is_violation(result, config)

    def test_allowed_by_allowlist(self):
        from noinlinedscript.config import AllowlistEntry

        source = "\n".join(f"echo line{i}" for i in range(10))
        result = _make_analyzed(source)
        config = ToolConfig(allowlist=[AllowlistEntry(file="Jenkinsfile.test", line=10)])
        assert not is_violation(result, config)


class TestFormatText:
    def test_contains_violation_marker(self):
        source = "\n".join(f"echo line{i}" for i in range(10))
        result = _make_analyzed(source)
        config = ToolConfig(max_line_count=5)
        text = format_text([result], config)
        assert "VIOLATION" in text

    def test_summary_line(self):
        result = _make_analyzed("echo hello")
        config = ToolConfig()
        text = format_text([result], config)
        assert "1 inline blocks found" in text

    def test_verbose_shows_non_violations(self):
        result = _make_analyzed("echo hello")
        config = ToolConfig()
        text = format_text([result], config, verbose=True)
        assert "ok" in text


    def test_warn_mode_uses_warning_marker(self):
        source = "\n".join(f"echo line{i}" for i in range(10))
        result = _make_analyzed(source)
        config = ToolConfig(max_line_count=5, warn=True)
        text = format_text([result], config)
        assert "WARNING" in text
        assert "VIOLATION" not in text


class TestFormatJson:
    def test_valid_json(self):
        result = _make_analyzed("echo hello")
        config = ToolConfig()
        output = format_json([result], config)
        data = json.loads(output)
        assert "blocks" in data
        assert "summary" in data
        assert data["summary"]["total_blocks"] == 1

    def test_shell_features_present(self):
        result = _make_analyzed("oc get pods | grep foo")
        config = ToolConfig()
        output = format_json([result], config)
        data = json.loads(output)
        assert "shell_features" in data["blocks"][0]
