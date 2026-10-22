"""Local preview server with a cross-platform file-manager action."""

import argparse
import json
import platform
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

EXPLORER_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = 8980


def selected_port(override=None):
    if override is not None:
        port = override
    elif (EXPLORER_DIR / ".explorer-port").is_file():
        try:
            port = int((EXPLORER_DIR / ".explorer-port").read_text().strip())
        except ValueError as error:
            raise ValueError("Invalid saved Explorer port") from error
    else:
        port = DEFAULT_PORT
    if not 1 <= port <= 65535:
        raise ValueError("Explorer port must be between 1 and 65535")
    return port


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
        try:
            script_inventory = json.loads((EXPLORER_DIR / "scripts-local.json").read_text()).get("scripts", [])
        except (OSError, ValueError):
            script_inventory = []
        allowed.update(item["file"] for item in script_inventory if item.get("file"))
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

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, help="Override the saved port for this server run")
    args = parser.parse_args()
    port = selected_port(args.port)
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
