"""Verify private script data and conservative local job matching."""

import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[1]
GENERATOR = REPO / "skills-explorer/generate-scripts-json.py"
spec = importlib.util.spec_from_file_location("script_explorer", GENERATOR)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class ScriptExplorer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source with spaces"
        self.source.mkdir()
        self.script = self.source / "daily report.py"
        self.script.write_text("print('fixture')\n")
        self.jobs = self.root / "Library/LaunchAgents"
        self.jobs.mkdir(parents=True)
        self.catalog = self.root / "script-catalog.toml"
        self.catalog.write_text('''schema_version = 1
[[scripts]]
id = "example/daily-report"
name = "daily-report"
aliases = ["report"]
description = "Prepare a report."
source = "example"
entrypoint = "daily report.py"
runtime = "python"
args = []
working_dir = "."
platforms = ["macos", "linux", "windows"]
status = "active"
''')
        self.config = self.root / "agent-config.toml"
        self.config.write_text(f'[script_catalog]\npath = "{self.catalog}"\n'
                               f'[script_catalog.sources]\nexample = "{self.source}"\n')

    def job(self, name, args, schedule=None):
        data = {"Label": name, "ProgramArguments": args,
                "StartCalendarInterval": schedule or {"Hour": 8, "Minute": 5}}
        (self.jobs / f"{name}.plist").write_bytes(plistlib.dumps(data))

    def test_matches_direct_launchd_and_absolute_cron_path(self):
        self.job("com.example.report", ["/usr/bin/python3", str(self.script)])
        cron = f'5 8 * * * /usr/bin/python3 "{self.script}"\n'
        result = generator.build(self.config, self.root, self.jobs, cron, [])
        script = result["scripts"][0]
        self.assertEqual(script["file"], str(self.script))
        self.assertEqual([(job["kind"], job["schedule"]) for job in script["jobs"]],
                         [("launchd", "Daily 08:05"), ("cron", "5 8 * * *")])

    def test_matches_versioned_python_interpreter(self):
        self.job("com.example.versioned-python",
                 ["/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13",
                  str(self.script)])
        jobs = generator.build(self.config, self.root, self.jobs, "", [])["scripts"][0]["jobs"]
        self.assertEqual([job["label"] for job in jobs], ["com.example.versioned-python"])

    def test_scripts_share_skill_stage_tool_and_task_rules(self):
        script = generator.build(self.config, self.root, self.jobs, "", [])["scripts"][0]
        text = f'{script["name"]} {script["description"]} {" ".join(script["aliases"])}'
        self.assertEqual(script["tags"]["stage"], generator.script_stage_tags(text))
        self.assertEqual(script["tags"]["tool"], generator.skill_tags.auto_tag_tool(text))
        self.assertEqual(script["tags"]["task"], generator.skill_tags.auto_tag_task(text))
        self.assertIn("reporting", script["tags"]["task"])

    def test_shared_task_rules_recognize_script_actions(self):
        self.assertIn("prioritization", generator.skill_tags.auto_tag_task("prioritize tasks"))
        self.assertIn("synchronization", generator.skill_tags.auto_tag_task("sync notes"))
        self.assertIn("classification", generator.skill_tags.auto_tag_task("tag tasks"))

    def test_script_stage_hints_cover_transfer_and_review(self):
        self.assertEqual(generator.script_stage_tags("sync Gmail tasks into the vault"),
                         ["gather", "produce"])
        self.assertEqual(generator.script_stage_tags("generate-weekly-review"),
                         ["produce", "reflect"])
        self.assertEqual(generator.script_stage_tags("daily-commit"), ["produce"])

    def test_matches_shell_cd_but_ignores_function_name_and_prose(self):
        self.job("com.example.shell", ["/bin/zsh", "-c",
                 f'cd "{self.source}" && python3 "daily report.py"'])
        self.job("com.example.function", ["/bin/zsh", "-c", "daily-report"])
        self.job("com.example.echo", ["/bin/zsh", "-c", f'echo "{self.script}"'])
        jobs = generator.build(self.config, self.root, self.jobs, "", [])["scripts"][0]["jobs"]
        self.assertEqual([job["label"] for job in jobs], ["com.example.shell"])

    def test_scans_multiple_launchd_directories_and_system_cron(self):
        system_agents = self.root / "system/LaunchDaemons"
        system_agents.mkdir(parents=True)
        plist = system_agents / "com.example.system.plist"
        plist.write_bytes(plistlib.dumps({"Label": "com.example.system",
                                         "ProgramArguments": ["/usr/bin/python3", str(self.script)],
                                         "StartInterval": 300}))
        cron_file = self.root / "etc/crontab"
        cron_file.parent.mkdir()
        cron_file.write_text(f'5 8 * * * root /usr/bin/python3 "{self.script}"\n')
        jobs = generator.observed_jobs(self.root, [self.jobs, system_agents], "", [cron_file])
        self.assertEqual([(job["kind"], job["label"]) for job in jobs],
                         [("launchd", "com.example.system"), ("cron", "crontab line 1")])
        self.assertEqual(jobs[0]["schedule"], "Every 300 seconds")

    def test_private_generated_file_and_missing_catalog(self):
        output = self.root / "local output"
        result = subprocess.run([sys.executable, "-B", str(GENERATOR), "--config", str(self.config),
                                 "--output-dir", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((output / "scripts-local.json").read_text())["scripts"][0]["file"],
                         str(self.script))
        self.config.write_text("[directories]\n")
        self.assertEqual(generator.build(self.config, self.root, self.jobs, "", [])["scripts"], [])

    def test_unreadable_crontab_is_reported(self):
        warnings = []
        with patch.object(generator.subprocess, "run", return_value=Mock(returncode=1, stderr="permission denied")):
            generator.observed_jobs(self.root, self.jobs, cron_files=[], warnings=warnings)
        self.assertIn("permission denied", warnings[0])


if __name__ == "__main__":
    unittest.main()
