"""Check file-reveal responses without opening a desktop application."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


SERVER = Path(__file__).resolve().parents[1] / "skills-explorer/serve.py"
spec = importlib.util.spec_from_file_location("explorer_server", SERVER)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class FileRevealResponses(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "skill source"
        self.source.mkdir()
        self.skill_file = self.source / "SKILL.md"
        self.skill_file.write_text("# Example skill\n")
        self.inventory = self.root / "skills-local.json"
        self.inventory.write_text(json.dumps({"inventory": [
            {"hasSkillMd": True, "truePath": str(self.source)},
        ]}))
        self.root_patch = patch.object(server, "EXPLORER_DIR", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def reveal(self, path, headers=None):
        handler = object.__new__(server.SkillsExplorerHandler)
        handler.headers = headers if headers is not None else {"X-Explorer-Action": "reveal"}
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = io.BytesIO()
        # Use the real send_json to cover the missing success status regression.
        handler.show_in_file_manager(str(path))
        return handler.send_response.call_args.args[0], json.loads(handler.wfile.getvalue())

    def test_success_returns_200_after_launching_each_file_manager(self):
        cases = [
            ("Darwin", ["open", "-R", str(self.skill_file)]),
            ("Windows", ["explorer.exe", f"/select,{self.skill_file}"]),
            ("Linux", ["xdg-open", str(self.source)]),
        ]
        for system, command in cases:
            with self.subTest(system=system), \
                    patch.object(server.platform, "system", return_value=system), \
                    patch.object(server.subprocess, "Popen") as launch:
                self.assertEqual(self.reveal(self.skill_file), (200, {"ok": True}))
                launch.assert_called_once_with(command)

    def test_inventory_can_reference_skill_file_directly(self):
        self.inventory.write_text(json.dumps({"inventory": [
            {"hasSkillMd": True, "truePath": str(self.skill_file)},
        ]}))
        with patch.object(server.subprocess, "Popen") as launch:
            self.assertEqual(self.reveal(self.skill_file), (200, {"ok": True}))
            launch.assert_called_once()

    def test_missing_action_header_does_not_launch(self):
        with patch.object(server.subprocess, "Popen") as launch:
            self.assertEqual(self.reveal(self.skill_file, headers={}),
                             (403, {"ok": False, "error": "Action not allowed"}))
            launch.assert_not_called()

    def test_unknown_and_deleted_sources_do_not_launch(self):
        unknown = self.root / "other.md"
        unknown.write_text("unlisted source")
        with patch.object(server.subprocess, "Popen") as launch:
            self.assertEqual(self.reveal(unknown),
                             (404, {"ok": False, "error": "File not found"}))
            self.skill_file.unlink()
            self.assertEqual(self.reveal(self.skill_file),
                             (404, {"ok": False, "error": "File not found"}))
            launch.assert_not_called()

    def test_launch_failure_returns_error_response(self):
        with patch.object(server.subprocess, "Popen", side_effect=OSError("Launch failed")):
            self.assertEqual(self.reveal(self.skill_file),
                             (500, {"ok": False, "error": "Launch failed"}))


if __name__ == "__main__":
    unittest.main()
