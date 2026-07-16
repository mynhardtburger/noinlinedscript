from noinlinedscript.models import EmbeddingContext, InlineLanguage, PythonEmbedStyle
from noinlinedscript.parsers.shellscript import parse_shell_script, parse_shell_source


class TestPythonDashC:
    def test_single_line_double_quote(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "python_dash_c.sh"))
        dash_c_blocks = [b for b in blocks if b.block_style == PythonEmbedStyle.DASH_C]
        single_line = dash_c_blocks[0]
        assert single_line.language == InlineLanguage.PYTHON
        assert single_line.embedding_context == EmbeddingContext.SHELL_SCRIPT
        assert single_line.start_line == 5
        assert "json.load" in single_line.source

    def test_multi_line_double_quote(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "python_dash_c.sh"))
        dash_c_blocks = [b for b in blocks if b.block_style == PythonEmbedStyle.DASH_C]
        multi_line = dash_c_blocks[1]
        assert multi_line.start_line == 8
        assert "import json, sys" in multi_line.source
        assert "finalizers" in multi_line.source

    def test_single_line_single_quote(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "python_dash_c.sh"))
        dash_c_blocks = [b for b in blocks if b.block_style == PythonEmbedStyle.DASH_C]
        single_quote = dash_c_blocks[2]
        assert single_quote.start_line == 18
        assert "access_token" in single_quote.source

    def test_python_m_excluded(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "python_dash_c.sh"))
        assert len(blocks) == 3


class TestPythonHeredoc:
    def test_simple_heredoc(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "python_heredoc.sh"))
        heredoc = blocks[0]
        assert heredoc.language == InlineLanguage.PYTHON
        assert heredoc.block_style == PythonEmbedStyle.HEREDOC
        assert heredoc.start_line == 7
        assert "import json, sys" in heredoc.source
        assert "PYEOF" not in heredoc.source

    def test_stdin_heredoc_with_args(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "python_heredoc.sh"))
        stdin_heredoc = blocks[1]
        assert stdin_heredoc.block_style == PythonEmbedStyle.STDIN_HEREDOC
        assert stdin_heredoc.start_line == 18
        assert "sys.argv[1]" in stdin_heredoc.source
        assert "REGEOF" not in stdin_heredoc.source


class TestNoInline:
    def test_clean_script_returns_empty(self, shellscript_fixtures):
        blocks = parse_shell_script(str(shellscript_fixtures / "no_inline.sh"))
        assert blocks == []


class TestParseShellSource:
    def test_parse_from_string_with_offset(self):
        source = 'oc get pods | python3 -c "import json,sys; print(json.load(sys.stdin))"\n'
        blocks = parse_shell_source(source, "Jenkinsfile.test", line_offset=10)
        assert len(blocks) == 1
        assert blocks[0].start_line == 11
        assert blocks[0].embedding_context == EmbeddingContext.JENKINSFILE
