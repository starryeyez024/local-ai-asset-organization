"""Prepare a user's local Explorer without modifying the published catalog."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/skill-linker"))
from asset_config import default_config_path

MARKER = ".agent-setup-explorer"
MARKER_CONTENT = "AI Assets Explorer local output v1\n"
VIEWER_FILES = ("index.html", "about.html", "serve.py")
GENERATED_FILES = ("skills.json", "skills-local.json", "scripts-local.json")


def prepare(config, output):
    config = config.expanduser().resolve()
    output = output.expanduser().resolve()
    if output == REPO or REPO in output.parents:
        raise ValueError("Choose a local output directory outside this repository.")
    if not config.is_file():
        raise ValueError(f"Configuration not found: {config}")
    if os.environ.get("SKILLS_ROOT"):
        raise ValueError("SKILLS_ROOT overrides the configuration; resolve that setting before setup.")
    marker = output / MARKER
    if output.exists():
        if not output.is_dir():
            raise ValueError(f"Output is not a directory: {output}")
        if any(output.iterdir()) and (not marker.is_file() or marker.read_text() != MARKER_CONTENT):
            raise ValueError(f"Existing directory is not managed by agent-setup: {output}")
    for name in (*VIEWER_FILES, *GENERATED_FILES, MARKER):
        target = output / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"Refusing to replace a link or directory: {target}")

    # Finish generation before changing a previously working local catalog.
    with tempfile.TemporaryDirectory(prefix="ai-explorer-") as temporary:
        staging = Path(temporary)
        subprocess.run([
            sys.executable, "-B", str(REPO / "skills-explorer/generate-skills-json.py"),
            "--config", str(config), "--output-dir", str(staging),
        ], check=True)
        subprocess.run([
            sys.executable, "-B", str(REPO / "skills-explorer/generate-scripts-json.py"),
            "--config", str(config), "--output-dir", str(staging),
        ], check=True)
        for name in VIEWER_FILES:
            shutil.copyfile(REPO / "skills-explorer" / name, staging / name)
        (staging / MARKER).write_text(MARKER_CONTENT)
        output.mkdir(parents=True, exist_ok=True)
        for name in (*VIEWER_FILES, *GENERATED_FILES, MARKER):
            shutil.copyfile(staging / name, output / name)
    print(f"Explorer prepared at {output}")
    print(f"Start its local server with Python: {output / 'serve.py'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config_path(),
                        help="Setup configuration (default: recommended location or existing legacy config)")
    parser.add_argument("--output-dir", type=Path,
                        default=Path.home() / ".local/share/ai-assets-explorer")
    args = parser.parse_args()
    try:
        prepare(args.config, args.output_dir)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
