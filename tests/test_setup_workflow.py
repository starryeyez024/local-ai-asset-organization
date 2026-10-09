"""Exercise the documented setup without touching installed tools or user files."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
LINKER = REPO / "skills/skill-linker/skill-linker.py"
GENERATOR = REPO / "skills-explorer/generate-skills-json.py"
PREPARE_EXPLORER = REPO / "skills/agent-setup/scripts/prepare-explorer.py"
sys.path.insert(0, str(LINKER.parent))
from asset_config import default_config_path, read_directories

spec = importlib.util.spec_from_file_location("linker", LINKER)
linker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linker)


class SetupWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.assets = self.root / "AI Assets"
        self.hub = self.root / "chosen skills folder"
        self.config = self.root / ".config/agent-tools/agent-config.toml"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(f'[directories]\ninstall_dir = "{self.assets}"\nsymlinks_dir = "{self.hub}"\n')
        self.source = self.assets / "example/skills/skills/report"
        self.skill(self.source, "report")

    def skill(self, directory, name):
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(f'---\nname: {name}\ndescription: Draft a useful report.\n---\n\n# Report\nWrite a report.\n')

    def run_linker(self, *args, expected=0):
        result = subprocess.run([sys.executable, "-B", str(LINKER), "--config", str(self.config), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_documented_config_links_and_explorer_reads_same_folder(self):
        original = (self.source / "SKILL.md").read_bytes()
        self.run_linker("--dry-run", "example/skills", "report")
        self.assertFalse(self.hub.exists())
        self.run_linker("example/skills", "report")
        self.assertEqual((self.hub / "report").resolve(), self.source)
        self.run_linker("example/skills", "report")
        output = self.root / "catalog"
        import os
        env = dict(os.environ)
        env.pop("SKILLS_ROOT", None)
        result = subprocess.run([sys.executable, "-B", str(GENERATOR), "--config", str(self.config), "--output-dir", str(output)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        public = json.loads((output / "skills.json").read_text())
        private = json.loads((output / "skills-local.json").read_text())
        self.assertEqual(public["skillCount"], 1)
        self.assertEqual(public["skills"][0]["id"], "report")
        self.assertNotIn("inventory", public)
        self.assertNotIn(str(self.root), json.dumps(public))
        self.assertEqual(private["inventory"][0]["truePath"], str(self.source))
        self.assertEqual((self.source / "SKILL.md").read_bytes(), original)

    def test_preferred_config_and_legacy_fallback(self):
        legacy = self.root / ".config/ai-tools/ai-tools.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(self.config.read_text())
        with patch.object(Path, "home", return_value=self.root):
            self.assertEqual(linker.SkillLinker().config_path, self.config)
            self.config.unlink()
            self.assertEqual(linker.SkillLinker().config_path, legacy)

    def test_explicit_existing_single_skill_and_native_target(self):
        source = self.root / "existing checkout/humanizer"
        self.skill(source, "humanizer")
        target = self.root / "native/.claude/skills"
        self.run_linker("--target-dir", target, source, "humanizer")
        self.assertEqual((target / "humanizer").resolve(), source)
        self.assertFalse(self.hub.exists())

    def test_typo_does_not_link_a_different_skill_or_apply_partial_selection(self):
        result = self.run_linker("example/skills", "report", "repor", expected=1)
        self.assertIn("Did you mean", result.stdout)
        self.assertFalse(self.hub.exists())

    def test_real_content_is_preserved_even_with_force(self):
        existing = self.hub / "report"
        existing.mkdir(parents=True)
        (existing / "keep.txt").write_text("keep me")
        self.run_linker("--force", "example/skills", "report", expected=1)
        self.assertEqual((existing / "keep.txt").read_text(), "keep me")

    def test_conflict_preview_and_deliberate_replacement(self):
        self.hub.mkdir()
        previous = self.root / "previous"
        previous.mkdir()
        link = self.hub / "report"
        link.symlink_to(previous)
        self.run_linker("example/skills", "report", expected=1)
        self.run_linker("--dry-run", "--force", "example/skills", "report")
        self.assertEqual(link.resolve(), previous)
        self.run_linker("--force", "example/skills", "report")
        self.assertEqual(link.resolve(), self.source)
        self.assertTrue(previous.exists())

    def test_relative_source_cannot_escape_asset_root(self):
        self.run_linker("../../outside", "all", expected=1)
        self.assertFalse(self.hub.exists())

    def test_invalid_configuration_fails_before_writes(self):
        self.config.write_text('[directories]\ninstall_dir = "relative"\nsymlinks_dir = "also-relative"\n')
        self.run_linker("example/skills", "report", expected=1)
        self.assertFalse(self.hub.exists())
        self.config.write_text('directories = "not a table"')
        with self.assertRaises(ValueError):
            read_directories(self.config)

    def prepare_explorer(self, output, expected=0, override=None):
        env = dict(os.environ)
        env.pop("SKILLS_ROOT", None)
        if override:
            env["SKILLS_ROOT"] = str(override)
        result = subprocess.run([
            sys.executable, "-B", str(PREPARE_EXPLORER),
            "--config", str(self.config), "--output-dir", str(output),
        ], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_onboarding_prepares_and_refreshes_isolated_explorer(self):
        self.assertFalse((REPO / "skills-explorer/skills.json").exists())
        original = (self.source / "SKILL.md").read_bytes()
        self.run_linker("example/skills", "report")
        output = self.root / "local viewer"
        self.prepare_explorer(output)
        self.assertFalse((output / "sample-skills.json").exists())
        catalog = json.loads((output / "skills.json").read_text())
        self.assertEqual(catalog["skillCount"], 1)
        self.assertRegex(catalog["generatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
        self.assertNotIn("scannedDirectory", catalog)
        local = json.loads((output / "skills-local.json").read_text())
        self.assertEqual(local["scannedDirectory"], str(self.hub.resolve()))
        self.assertEqual(local["generatedAt"], catalog["generatedAt"])
        self.assertEqual(catalog["skills"][0]["id"], "report")
        for filename in ("serve.py", "index.html", "about.html"):
            self.assertEqual((output / filename).read_bytes(),
                             (REPO / "skills-explorer" / filename).read_bytes())
        self.assertEqual(json.loads((output / "skills-local.json").read_text())
                         ["inventory"][0]["truePath"], str(self.source))
        (output / "my-notes.txt").write_text("keep")
        self.skill(self.source.parent / "new-skill", "new-skill")
        self.run_linker("example/skills", "new-skill")
        self.prepare_explorer(output)
        self.assertEqual(json.loads((output / "skills.json").read_text())["skillCount"], 2)
        self.assertEqual((output / "my-notes.txt").read_text(), "keep")
        self.assertEqual((self.source / "SKILL.md").read_bytes(), original)
        self.assertFalse((REPO / "skills-explorer/skills.json").exists())

    def test_empty_catalog_is_valid_and_failed_refresh_preserves_it(self):
        self.hub.mkdir()
        output = self.root / "empty viewer"
        self.prepare_explorer(output)
        previous = (output / "skills.json").read_bytes()
        self.assertEqual(json.loads(previous)["skillCount"], 0)
        self.config.write_text("invalid toml [[")
        self.prepare_explorer(output, expected=1)
        self.assertEqual((output / "skills.json").read_bytes(), previous)

    def test_make_regen_uses_personal_output_and_explicit_config(self):
        self.run_linker("example/skills", "report")
        output = self.root / "personal explorer"
        env = dict(os.environ)
        env.pop("SKILLS_ROOT", None)
        result = subprocess.run([
            "make", "-C", str(REPO / "skills-explorer"), "regen",
            f"CONFIG={self.config}", f"EXPLORER_DIR={output}",
            f"PYTHON={sys.executable}",
        ], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((output / "serve.py").is_file())
        self.assertEqual(json.loads((output / "skills.json").read_text())["skillCount"], 1)
        self.assertFalse((REPO / "skills-explorer/skills.json").exists())

    def test_generator_defaults_to_personal_data_directory(self):
        self.run_linker("example/skills", "report")
        spec = importlib.util.spec_from_file_location("fixture_generator", GENERATOR)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        env = dict(os.environ)
        env.pop("SKILLS_ROOT", None)
        with patch.object(Path, "home", return_value=self.root), \
                patch.object(sys, "argv", [str(GENERATOR), "--config", str(self.config)]), \
                patch.dict(os.environ, env, clear=True):
            generator.main()
        output = self.root / ".local/share/ai-assets-explorer"
        self.assertEqual(json.loads((output / "skills.json").read_text())["skillCount"], 1)
        self.assertFalse((REPO / "skills-explorer/skills.json").exists())

    def test_explorer_refuses_unmanaged_output_and_public_repository(self):
        output = self.root / "existing"
        output.mkdir()
        (output / "index.html").write_text("user content")
        self.prepare_explorer(output, expected=1)
        self.assertEqual((output / "index.html").read_text(), "user content")
        self.prepare_explorer(REPO / "skills-explorer", expected=1)

    def test_explorer_refuses_environment_override_and_output_symlink(self):
        self.hub.mkdir()
        output = self.root / "viewer"
        self.prepare_explorer(output, expected=1, override=self.hub)
        self.assertFalse(output.exists())
        self.prepare_explorer(output)
        (output / "index.html").unlink()
        target = self.root / "keep.html"
        target.write_text("keep")
        (output / "index.html").symlink_to(target)
        self.prepare_explorer(output, expected=1)
        self.assertEqual(target.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
