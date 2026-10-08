"""Local preview server with a cross-platform file-manager action."""

import json
import platform
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

EXPLORER_DIR = Path(__file__).resolve().parent


class SkillsExplorerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/__show-in-file-manager":
            self.show_in_file_manager(parse_qs(parsed.query).get("path", [""])[0])
            return
        super().do_GET()

    def show_in_file_manager(self, raw_path):
        path = Path(raw_path).expanduser()
        if self.headers.get("X-Explorer-Action") != "reveal":
            self.send_json({"ok": False, "error": "Action not allowed"}, 403)
            return
        inventory_file = EXPLORER_DIR / "skills-local.json"
        try:
            inventory = json.loads(inventory_file.read_text()).get("inventory", [])
        except (OSError, ValueError):
            inventory = []
        allowed = {
            str(Path(item["truePath"]) / "SKILL.md")
            for item in inventory
            if item.get("hasSkillMd") and item.get("truePath") and not item["truePath"].endswith("SKILL.md")
        }
        allowed.update(
            item["truePath"] for item in inventory
            if item.get("hasSkillMd") and item.get("truePath", "").endswith("SKILL.md")
        )
        if not path.is_absolute() or str(path) not in allowed or not path.exists():
            self.send_json({"ok": False, "error": "File not found"}, 404)
            return

        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.Popen(["open", "-R", str(path)])
            elif system == "Windows":
                subprocess.Popen(["explorer.exe", f"/select,{path}"])
            else:
                subprocess.Popen(["xdg-open", str(path.parent)])
        except OSError as error:
            self.send_json({"ok": False, "error": str(error)}, 500)
            return

        self.send_json({"ok": True})

    def send_json(self, payload, status):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
    handler = partial(SkillsExplorerHandler, directory=str(EXPLORER_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"Serving at http://localhost:{port} -- press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
