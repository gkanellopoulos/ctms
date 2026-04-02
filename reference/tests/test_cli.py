"""CLI integration tests via Click CliRunner."""

import json
from pathlib import Path

from click.testing import CliRunner

from ctms.cli.main import cli


VECTORS_DIR = Path(__file__).resolve().parent.parent.parent / "vectors"


class TestCanonicalize:

    def test_stdout_output(self):
        """ctms canonicalize prints canonical form to stdout."""
        runner = CliRunner()
        tool_file = str(VECTORS_DIR / "weather-tool-object.json")
        result = runner.invoke(cli, ["canonicalize", tool_file])

        assert result.exit_code == 0
        # Output should be valid JSON on a single line (plus newline from echo).
        output = result.output.strip()
        parsed = json.loads(output)
        assert parsed["name"] == "get_weather"

    def test_digest_flag(self):
        """--digest prints SHA-256 digest to stderr."""
        runner = CliRunner(mix_stderr=False)
        tool_file = str(VECTORS_DIR / "weather-tool-object.json")
        result = runner.invoke(cli, ["canonicalize", tool_file, "--digest"])

        assert result.exit_code == 0
        assert "sha256:" in result.stderr

    def test_output_file(self, tmp_path):
        """--output writes canonical form to file."""
        runner = CliRunner()
        tool_file = str(VECTORS_DIR / "weather-tool-object.json")
        out_file = str(tmp_path / "canonical.txt")
        result = runner.invoke(cli, ["canonicalize", tool_file, "--output", out_file])

        assert result.exit_code == 0
        content = Path(out_file).read_bytes()
        parsed = json.loads(content)
        assert parsed["name"] == "get_weather"


class TestInspect:

    def test_text_output(self):
        """ctms inspect shows STM fields in text format."""
        runner = CliRunner()
        stm_file = str(VECTORS_DIR / "weather-stm.json")
        result = runner.invoke(cli, ["inspect", stm_file])

        assert result.exit_code == 0
        assert "Subject:" in result.output
        assert "get_weather" in result.output

    def test_json_output(self):
        """ctms inspect --output-format json returns valid JSON."""
        runner = CliRunner()
        stm_file = str(VECTORS_DIR / "weather-stm.json")
        result = runner.invoke(cli, ["inspect", stm_file, "--output-format", "json"])

        assert result.exit_code == 0
        info = json.loads(result.output)
        assert info["ctmsVersion"] == "1.0"
        assert info["manifestVersion"] == "1.0"


class TestVerifyOffline:

    def test_offline_pass(self, tmp_path):
        """ctms verify --offline passes when tool matches STM."""
        from ctms._types import ManifestVersion
        from ctms.canonicalize import canonicalize
        from ctms.stm import build_stm

        # Build a valid STM for the weather tool.
        tool_file = VECTORS_DIR / "weather-tool-object.json"
        tool_object = json.loads(tool_file.read_bytes())
        canonical_form = canonicalize(tool_object)

        stm_dict = build_stm(
            subject_name="test/weather/get_weather",
            canonical_form=canonical_form,
            manifest_version=ManifestVersion(major=1, minor=0),
            server_version="1.0.0",
            signing_timestamp="2026-03-25T10:00:00Z",
            signature="dGVzdA==",
        )
        stm_file = tmp_path / "test.stm.json"
        stm_file.write_text(json.dumps(stm_dict, indent=2))

        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", str(tool_file), str(stm_file), "--offline",
        ])

        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_offline_fail(self, tmp_path):
        """ctms verify --offline fails when tool has been tampered."""
        from ctms._types import ManifestVersion
        from ctms.canonicalize import canonicalize
        from ctms.stm import build_stm

        # Build STM from original tool.
        tool_file = VECTORS_DIR / "weather-tool-object.json"
        tool_object = json.loads(tool_file.read_bytes())
        canonical_form = canonicalize(tool_object)

        stm_dict = build_stm(
            subject_name="test/weather/get_weather",
            canonical_form=canonical_form,
            manifest_version=ManifestVersion(major=1, minor=0),
            server_version="1.0.0",
            signing_timestamp="2026-03-25T10:00:00Z",
            signature="dGVzdA==",
        )
        stm_file = tmp_path / "test.stm.json"
        stm_file.write_text(json.dumps(stm_dict, indent=2))

        # Write a tampered tool file.
        tampered = dict(tool_object)
        tampered["description"] = "TAMPERED"
        tampered_file = tmp_path / "tampered.json"
        tampered_file.write_text(json.dumps(tampered, indent=2))

        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", str(tampered_file), str(stm_file), "--offline",
        ])

        assert result.exit_code == 1
