"""Contract tests for the standalone auditor package's script catalog helper."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "skills/ai-asset-auditor/scripts/script-catalog.py"
FIXTURE = REPO / "tests/fixtures/script-catalog"


class ScriptCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "agent-config.toml"
        self.catalog = self.root / "catalog.toml"
        shutil.copyfile(FIXTURE / "catalog.toml", self.catalog)
        self.source = FIXTURE / "source"
        self.write_config()

    def write_config(self, extra=""):
        self.config.write_text(
            '[script_catalog]\npath = "catalog.toml"\n'
            '[script_catalog.sources]\n'
            f'example-tools = {json.dumps(str(self.source))}\n'
            f'other-tools = {json.dumps(str(self.source))}\n' + extra,
            encoding="utf-8",
        )

    def run_helper(self, *arguments, expected=0, cwd=None):
        run = subprocess.run(
            [sys.executable, "-B", str(HELPER), "--config", str(self.config), "--json", *arguments],
            cwd=cwd or self.root, text=True, capture_output=True,
        )
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return json.loads(run.stdout)

    def test_qualified_unique_alias_filename_and_unrelated_directory(self):
        for name in ("example-tools/hello", "hello", "greet", "hello.py"):
            with self.subTest(name=name):
                result = self.run_helper("resolve", name, cwd=self.root)
                self.assertEqual(result["id"], "example-tools/hello")
                self.assertEqual(result["argv"][2:], ["two words", "a&b"])
                self.assertEqual(result["working_dir"], str(self.source))
                self.assertEqual(result["provenance"]["source"], "example-tools")
        helper = self.run_helper("resolve", "helper")
        self.assertEqual(helper["working_dir"], str(self.source / "skills/greeter"))

    def test_ambiguity_unknown_archived_and_stale(self):
        ambiguous = self.run_helper("resolve", "report", expected=1)
        self.assertEqual(ambiguous["code"], "ambiguous")
        self.assertEqual(ambiguous["candidates"], ["example-tools/report", "other-tools/report"])
        self.assertEqual(self.run_helper("resolve", "example-tools/report")["status"], "ok")
        self.assertEqual(self.run_helper("resolve", "hell", expected=1)["code"], "unknown")
        self.assertEqual(self.run_helper("resolve", "old", expected=1)["code"], "unknown")
        self.assertEqual(self.run_helper("resolve", "example-tools/old", expected=1)["code"], "inactive")
        self.assertEqual(self.run_helper("resolve", "missing", expected=1)["code"], "stale_entry")

    def test_validate_list_and_case_collision(self):
        result = self.run_helper("validate", expected=1)
        self.assertEqual(result["failures"][0]["code"], "stale_entry")
        listing = self.run_helper("list")
        self.assertNotIn("example-tools/old", [item["id"] for item in listing["scripts"]])
        self.assertEqual(len(self.run_helper("list", "--status", "archived")["scripts"]), 1)
        self.catalog.write_text(self.catalog.read_text().replace('name = "hello"', 'name = "REPORT"'))
        collision = self.run_helper("resolve", "greet", expected=1)
        self.assertEqual(collision["code"], "case_collision")
        plain = subprocess.run([sys.executable, "-B", str(HELPER), "--config", str(self.config), "validate"],
                               text=True, capture_output=True)
        self.assertEqual(plain.returncode, 1)
        self.assertIn("case_collision", plain.stdout)

    def test_source_root_change_and_interpreter_override(self):
        alternate = self.root / "new source & Unicode Ω"
        shutil.copytree(self.source, alternate)
        self.source = alternate
        self.write_config(f'[script_catalog.interpreters]\npython = {json.dumps(sys.executable)}\n')
        result = self.run_helper("resolve", "hello")
        self.assertEqual(result["id"], "example-tools/hello")
        self.assertEqual(result["file"], str((alternate / "scripts/hello.py").resolve()))
        self.assertEqual(result["interpreter"], str(Path(sys.executable).resolve()))

    def test_working_directory_can_have_separate_private_binding(self):
        workspace = self.root / "workspace & notes"
        workspace.mkdir()
        self.catalog.write_text(self.catalog.read_text().replace(
            'working_dir = "."\nplatforms', 'working_dir = "."\nworking_dir_binding = "workspace"\nplatforms', 1))
        with self.config.open("a") as stream:
            stream.write(f'[script_catalog.working_dirs]\nworkspace = {json.dumps(str(workspace))}\n')
        result = self.run_helper("resolve", "hello")
        self.assertEqual(result["working_dir"], str(workspace.resolve()))
        self.assertEqual(result["provenance"]["working_dir_binding"], "workspace")

    def test_missing_config_and_missing_interpreter(self):
        self.config.unlink()
        self.assertEqual(self.run_helper("resolve", "hello", expected=1)["code"], "configuration")
        self.write_config('[script_catalog.interpreters]\npython = "no-such-python-for-fixture"\n')
        self.assertEqual(self.run_helper("resolve", "hello", expected=1)["code"], "missing_interpreter")

    def test_config_precedence_and_relative_paths(self):
        home = self.root / "home"
        preferred = home / ".config/agent-tools/agent-config.toml"
        legacy = home / ".config/ai-tools/ai-tools.toml"
        preferred.parent.mkdir(parents=True)
        legacy.parent.mkdir(parents=True)
        relative_catalog = preferred.parent / "script-catalog.toml"
        shutil.copyfile(self.catalog, relative_catalog)
        content = ('[script_catalog]\npath = "script-catalog.toml"\n'
                   f'[script_catalog.sources]\nexample-tools = {json.dumps(str(self.source))}\n'
                   f'other-tools = {json.dumps(str(self.source))}\n')
        preferred.write_text(content)
        legacy.write_text(content.replace('script-catalog.toml', 'missing.toml'))
        env = dict(os.environ, HOME=str(home))
        command = [sys.executable, "-B", str(HELPER), "--json", "resolve", "hello"]
        run = subprocess.run(command, cwd=self.root, env=env, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["provenance"]["catalog"], str(relative_catalog.resolve()))
        preferred.unlink()
        run = subprocess.run(command, cwd=self.root, env=env, text=True, capture_output=True)
        self.assertEqual(json.loads(run.stdout)["code"], "configuration")

    def test_unsupported_platform_and_catalog_output_guard(self):
        current = "macos" if sys.platform == "darwin" else "windows" if os.name == "nt" else "linux"
        replacement = 'platforms = ["windows"]' if current != "windows" else 'platforms = ["macos"]'
        self.catalog.write_text(self.catalog.read_text().replace(
            'platforms = ["macos", "windows", "linux"]', replacement, 1))
        self.assertEqual(self.run_helper("resolve", "hello", expected=1)["code"], "unsupported_platform")
        result = self.run_helper("inventory", "--root", f"example-tools={self.source}",
                                 "--output-candidates", str(self.catalog), expected=1)
        self.assertEqual(result["code"], "usage")

    def test_inventory_is_read_only_and_does_not_follow_external_links(self):
        source = self.root / "source"
        source.mkdir()
        script = source / "script with spaces & Ω.py"
        script.write_text("#!/usr/bin/env python3\nraise RuntimeError('never execute me')\n")
        extensionless = source / "run-me"
        extensionless.write_text("#!/usr/bin/env python3\nprint('not run')\n")
        (source / "note.md").write_text("documentation")
        (source / "data.json").write_text("{}")
        (source / "secret.env").write_text("TOKEN=do-not-display")
        (source / "binary").write_bytes(b"\x00\x01")
        outside = self.root / "outside.py"
        outside.write_text("print('outside')")
        try:
            (source / "outside-link.py").symlink_to(outside)
        except OSError:
            pass
        result = self.run_helper("inventory", "--root", f"selected={source}")
        kinds = {item["relative_path"]: item["kind"] for item in result["items"]}
        self.assertEqual(kinds[script.name], "script")
        self.assertEqual(kinds[extensionless.name], "script")
        self.assertEqual(kinds["binary"], "binary")
        self.assertEqual(kinds["note.md"], "documentation")
        self.assertEqual(kinds["data.json"], "data")
        self.assertNotIn("secret.env", kinds)
        self.assertNotIn("outside-link.py", kinds)
        self.assertEqual(script.read_text().count("never execute me"), 1)

    def test_independent_auditor_package(self):
        package = self.root / "auditor"
        shutil.copytree(HELPER.parent.parent, package)
        run = subprocess.run([sys.executable, "-B", str(package / "scripts/script-catalog.py"),
                              "--config", str(self.config), "--json", "resolve", "hello"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["id"], "example-tools/hello")

    def test_inventory_uses_enclosing_git_toplevel(self):
        root = self.root / "vault repo"
        nested = root / "08-Local setup/Scripts & Prompts"
        nested.mkdir(parents=True)
        (nested / "sample.py").write_text("print('fixture')\n")
        init = subprocess.run(["git", "init", "-q", str(root)], capture_output=True, text=True)
        self.assertEqual(init.returncode, 0, init.stderr)
        result = self.run_helper("inventory", "--root", f"nested={nested}")
        item = next(i for i in result["items"] if i["relative_path"] == "sample.py")
        self.assertEqual(item["git_root"], str(root.resolve()))
        self.assertEqual(item["git_relative_path"], "08-Local setup/Scripts & Prompts/sample.py")


if __name__ == "__main__":
    unittest.main()
