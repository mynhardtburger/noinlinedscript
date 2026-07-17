import json

from noinlinedscript.cli import main


class TestCli:
    def test_exit_zero_on_clean_file(self, jenkinsfile_fixtures, capsys):
        result = main([str(jenkinsfile_fixtures / "Jenkinsfile.clean")])
        assert result == 0
        captured = capsys.readouterr()
        assert "0 exceed thresholds" in captured.out

    def test_exit_one_on_violations(self, jenkinsfile_fixtures, capsys):
        result = main([str(jenkinsfile_fixtures / "Jenkinsfile.triple_double_quote")])
        assert result == 1

    def test_json_output(self, jenkinsfile_fixtures, capsys):
        main([str(jenkinsfile_fixtures / "Jenkinsfile.triple_single_quote"), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "blocks" in data
        assert "summary" in data

    def test_verbose_flag(self, jenkinsfile_fixtures, capsys):
        main([str(jenkinsfile_fixtures / "Jenkinsfile.single_line"), "--verbose"])
        captured = capsys.readouterr()
        assert "ok" in captured.out

    def test_max_lines_override(self, jenkinsfile_fixtures, capsys):
        result = main([str(jenkinsfile_fixtures / "Jenkinsfile.triple_double_quote"), "--max-lines", "100", "--max-score", "1000"])
        assert result == 0

    def test_shell_scripts(self, shellscript_fixtures, capsys):
        result = main([str(shellscript_fixtures / "python_heredoc.sh")])
        assert result == 1

    def test_no_files_returns_zero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        result = main([])
        assert result == 0


class TestWarnMode:
    def test_warn_exits_zero_with_violations(self, jenkinsfile_fixtures):
        result = main([str(jenkinsfile_fixtures / "Jenkinsfile.triple_double_quote"), "--warn"])
        assert result == 0

    def test_warn_prints_to_stderr(self, jenkinsfile_fixtures, capsys):
        main([str(jenkinsfile_fixtures / "Jenkinsfile.triple_double_quote"), "--warn"])
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "exceed thresholds" in captured.err

    def test_warn_with_verbose(self, jenkinsfile_fixtures, capsys):
        main([str(jenkinsfile_fixtures / "Jenkinsfile.single_line"), "--warn", "--verbose"])
        captured = capsys.readouterr()
        assert "ok" in captured.err


class TestFileDiscovery:
    def test_discovers_jenkinsfiles_and_sh(self, tmp_path, monkeypatch):
        (tmp_path / "Jenkinsfile.test").write_text("pipeline {}\n")
        (tmp_path / "script.sh").write_text("#!/bin/bash\necho hello\n")
        (tmp_path / "readme.md").write_text("# readme\n")
        monkeypatch.chdir(tmp_path)
        result = main([])
        assert result == 0
