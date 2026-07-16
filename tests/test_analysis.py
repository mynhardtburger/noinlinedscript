from noinlinedscript.analysis import analyze_block
from noinlinedscript.models import EmbeddingContext, InlineBlock, InlineLanguage, ShBlockStyle, PythonEmbedStyle


def _shell_block(source: str) -> InlineBlock:
    return InlineBlock(
        file_path="test.sh",
        start_line=1,
        end_line=1,
        language=InlineLanguage.SHELL,
        embedding_context=EmbeddingContext.JENKINSFILE,
        source=source,
        block_style=ShBlockStyle.TRIPLE_SINGLE,
    )


def _python_block(source: str) -> InlineBlock:
    return InlineBlock(
        file_path="test.sh",
        start_line=1,
        end_line=1,
        language=InlineLanguage.PYTHON,
        embedding_context=EmbeddingContext.SHELL_SCRIPT,
        source=source,
        block_style=PythonEmbedStyle.HEREDOC,
    )


class TestLineCount:
    def test_excludes_blank_lines(self):
        result = analyze_block(_shell_block("echo hello\n\necho world"))
        assert result.complexity.line_count == 2

    def test_excludes_comments(self):
        result = analyze_block(_shell_block("# comment\necho hello"))
        assert result.complexity.line_count == 1

    def test_keeps_shebang(self):
        result = analyze_block(_shell_block("#!/bin/bash\necho hello"))
        assert result.complexity.line_count == 2

    def test_total_lines_counts_all(self):
        result = analyze_block(_shell_block("#!/bin/bash\n\n# comment\necho hello"))
        assert result.complexity.total_lines == 4


class TestShellFeatures:
    def test_pipe_detection(self):
        result = analyze_block(_shell_block("oc get pods | grep running | wc -l"))
        assert result.complexity.shell_features.pipe_count == 2

    def test_pipe_excludes_or(self):
        result = analyze_block(_shell_block('oc get pods || echo "failed"'))
        assert result.complexity.shell_features.pipe_count == 0

    def test_command_substitution(self):
        result = analyze_block(_shell_block('echo "version: $(uv --version)"'))
        assert result.complexity.shell_features.command_substitution_count == 1

    def test_conditionals(self):
        source = "if [ -f file ]; then\n  echo yes\nfi\ncase $x in\n  a) ;;\nesac"
        result = analyze_block(_shell_block(source))
        assert result.complexity.shell_features.conditional_count == 2

    def test_loops(self):
        source = "for i in 1 2 3; do\n  echo $i\ndone\nwhile true; do\n  sleep 1\ndone"
        result = analyze_block(_shell_block(source))
        assert result.complexity.shell_features.loop_count == 2

    def test_heredocs(self):
        result = analyze_block(_shell_block("cat <<EOF\nhello\nEOF"))
        assert result.complexity.shell_features.heredoc_count == 1

    def test_external_commands(self):
        result = analyze_block(_shell_block("oc get pods\ncurl http://example.com\ngit status"))
        cmds = result.complexity.shell_features.external_commands
        assert "oc" in cmds
        assert "curl" in cmds
        assert "git" in cmds


class TestPythonFeatures:
    def test_imports(self):
        result = analyze_block(_python_block("import json\nfrom sys import stdin"))
        assert result.complexity.python_features.import_count == 2

    def test_function_defs(self):
        result = analyze_block(_python_block("def foo():\n    pass\ndef bar():\n    pass"))
        assert result.complexity.python_features.function_def_count == 2

    def test_class_defs(self):
        result = analyze_block(_python_block("class Foo:\n    pass"))
        assert result.complexity.python_features.class_def_count == 1

    def test_try_except(self):
        result = analyze_block(_python_block("try:\n    x()\nexcept:\n    pass"))
        assert result.complexity.python_features.try_except_count == 1


class TestComplexityScore:
    def test_trivial_oneliner(self):
        result = analyze_block(_shell_block("echo hello"))
        assert result.complexity.complexity_score == 1.0

    def test_complex_block(self):
        source = "#!/bin/bash\nset -e\noc get pods | grep running\nfor i in $(seq 1 10); do\n  curl http://test\ndone"
        result = analyze_block(_shell_block(source))
        score = result.complexity.complexity_score
        assert score > 10.0

    def test_python_score_with_imports(self):
        source = "import json\nimport sys\ndata = json.load(sys.stdin)\nprint(data)"
        result = analyze_block(_python_block(source))
        assert result.complexity.complexity_score == 6.0  # 4 lines + 2 imports
