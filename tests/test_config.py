from noinlinedscript.config import AllowlistEntry, ToolConfig, load_config


class TestToolConfig:
    def test_defaults(self):
        config = ToolConfig()
        assert config.max_line_count == 5
        assert config.max_complexity_score == 10.0
        assert config.allowlist == []

    def test_is_allowed_by_file(self):
        config = ToolConfig(allowlist=[AllowlistEntry(file="scripts/_lib.sh")])
        assert config.is_allowed("scripts/_lib.sh", 220)
        assert not config.is_allowed("scripts/other.sh", 1)

    def test_is_allowed_by_file_and_line(self):
        config = ToolConfig(allowlist=[AllowlistEntry(file="scripts/_lib.sh", line=220)])
        assert config.is_allowed("scripts/_lib.sh", 220)
        assert not config.is_allowed("scripts/_lib.sh", 300)

    def test_is_allowed_glob(self):
        config = ToolConfig(allowlist=[AllowlistEntry(file="scripts/*.sh")])
        assert config.is_allowed("scripts/foo.sh", 1)
        assert not config.is_allowed("tests/foo.sh", 1)


class TestLoadConfig:
    def test_load_from_pyproject(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.noinlinedscript]
max_line_count = 10
max_complexity_score = 20.0
exclude_patterns = ["python3 -m"]

[[tool.noinlinedscript.allowlist]]
file = "scripts/_lib.sh"
line = 220
reason = "Simple JSON extraction"
""")
        config = load_config(str(pyproject))
        assert config.max_line_count == 10
        assert config.max_complexity_score == 20.0
        assert config.exclude_patterns == ["python3 -m"]
        assert len(config.allowlist) == 1
        assert config.allowlist[0].file == "scripts/_lib.sh"
        assert config.allowlist[0].line == 220

    def test_missing_file_returns_defaults(self):
        config = load_config("/nonexistent/pyproject.toml")
        assert config.max_line_count == 5

    def test_no_tool_section_returns_defaults(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'\n")
        config = load_config(str(pyproject))
        assert config.max_line_count == 5
