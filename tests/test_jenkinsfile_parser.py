from noinlinedscript.models import EmbeddingContext, InlineLanguage, PythonEmbedStyle, ShBlockStyle
from noinlinedscript.parsers.jenkinsfile import parse_jenkinsfile


class TestTripleSingleQuote:
    def test_detects_block(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.triple_single_quote"))
        shell_blocks = [b for b in blocks if b.language == InlineLanguage.SHELL]
        assert len(shell_blocks) == 1
        block = shell_blocks[0]
        assert block.block_style == ShBlockStyle.TRIPLE_SINGLE
        assert block.embedding_context == EmbeddingContext.JENKINSFILE
        assert block.start_line == 5
        assert "set -e" in block.source
        assert "curl" in block.source

    def test_source_content(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.triple_single_quote"))
        shell_blocks = [b for b in blocks if b.language == InlineLanguage.SHELL]
        block = shell_blocks[0]
        assert "#!/bin/bash" in block.source
        assert "uv --version" in block.source


class TestTripleDoubleQuote:
    def test_detects_block(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.triple_double_quote"))
        shell_blocks = [b for b in blocks if b.language == InlineLanguage.SHELL]
        assert len(shell_blocks) == 1
        block = shell_blocks[0]
        assert block.block_style == ShBlockStyle.TRIPLE_DOUBLE
        assert block.start_line == 5
        assert "params.PROJECT_NAME" in block.source


class TestSingleLine:
    def test_detects_all_single_line_blocks(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.single_line"))
        assert len(blocks) == 3

    def test_double_quote_style(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.single_line"))
        double_blocks = [b for b in blocks if b.block_style == ShBlockStyle.SINGLE_DOUBLE]
        assert len(double_blocks) == 2
        assert "prereqs.sh" in double_blocks[0].source

    def test_single_quote_style(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.single_line"))
        single_blocks = [b for b in blocks if b.block_style == ShBlockStyle.SINGLE_SINGLE]
        assert len(single_blocks) == 1
        assert "uv sync" in single_blocks[0].source


class TestScriptCall:
    def test_detects_triple_quoted_script_call(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.script_call"))
        script_blocks = [b for b in blocks if b.block_style == ShBlockStyle.SCRIPT_CALL]
        assert len(script_blocks) == 2
        triple = script_blocks[0]
        assert "llminferenceservice" in triple.source
        assert triple.start_line == 6

    def test_detects_single_line_script_call(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.script_call"))
        script_blocks = [b for b in blocks if b.block_style == ShBlockStyle.SCRIPT_CALL]
        single = script_blocks[1]
        assert "oc get pods" in single.source


class TestConcatenated:
    def test_detects_concatenated_block(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.concatenated"))
        shell_blocks = [b for b in blocks if b.language == InlineLanguage.SHELL]
        assert len(shell_blocks) == 1
        block = shell_blocks[0]
        assert block.block_style == ShBlockStyle.TRIPLE_SINGLE
        assert "prereqs.sh" in block.source
        assert "mirror-rhoai-images.sh" in block.source


class TestNestedPython:
    def test_detects_nested_python(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.nested_python"))
        python_blocks = [b for b in blocks if b.language == InlineLanguage.PYTHON]
        assert len(python_blocks) == 1
        py_block = python_blocks[0]
        assert py_block.block_style == PythonEmbedStyle.DASH_C
        assert "json.load" in py_block.source
        assert py_block.parent_block is not None
        assert py_block.parent_block.language == InlineLanguage.SHELL


class TestCleanJenkinsfile:
    def test_tracked_sh_ignored(self, jenkinsfile_fixtures):
        blocks = parse_jenkinsfile(str(jenkinsfile_fixtures / "Jenkinsfile.clean"))
        assert blocks == []
