#!/usr/bin/env python3
"""
skill-linker: Selective symlink creation for AI project skills.

Creates symlinks from individual skills in an AI project directory into
~/.agents/skills, with fuzzy matching on skill names.

Usage:
  skill-linker <project-name> [skill1] [skill2] ...
  skill-linker <project-name>  # interactive mode
  skill-linker --force <project-name> [skill1] [skill2] ...  # replace existing symlinks
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import difflib


class SkillLinker:
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with config file location."""
        self.config_path = config_path or Path.home() / ".config" / "ai-tools" / "ai-tools.toml"
        self.config = self._read_config()
        self.install_dir = Path(self.config["install_dir"]).expanduser()
        self.symlinks_dir = Path(self.config["symlinks_dir"]).expanduser()

    def _read_config(self) -> Dict[str, str]:
        """Read and parse ai-tools.toml config file."""
        if not self.config_path.exists():
            self._error(f"Config file not found: {self.config_path}")
            self._error("Create ~/.config/ai-tools/ai-tools.toml with:")
            self._error("""
[directories]
install_dir = "~/AI Tools"
symlinks_dir = "~/.agents/skills"
""")
            sys.exit(1)

        config = {"install_dir": "~/AI Tools", "symlinks_dir": "~/.agents/skills"}
        try:
            with open(self.config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("["):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"')
                        if key in ["install_dir", "symlinks_dir"]:
                            config[key] = value
        except Exception as e:
            self._error(f"Error reading config: {e}")
            sys.exit(1)

        return config

    def _discover_skills(self, project_path: Path) -> Dict[str, Path]:
        """
        Scan project for skills (directories containing SKILL.md).
        Returns dict: {skill_name: skill_folder_path}
        """
        skills = {}
        
        # Look for skills/*/SKILL.md pattern
        skills_dir = project_path / "skills"
        if not skills_dir.exists():
            self._error(f"No 'skills' directory found in {project_path}")
            return skills

        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir():
                skill_md = skill_folder / "SKILL.md"
                if skill_md.exists():
                    skills[skill_folder.name] = skill_folder

        return skills

    def _fuzzy_match(self, requested: str, available: List[str], threshold: float = 0.6) -> Optional[str]:
        """
        Fuzzy match a requested skill name against available skills.
        Returns the best match if confidence > threshold, else None.
        """
        matches = difflib.get_close_matches(requested, available, n=1, cutoff=threshold)
        return matches[0] if matches else None

    def _resolve_skill_names(self, requested_names: List[str], available_skills: Dict[str, Path]) -> Tuple[Dict[str, Path], List[str]]:
        """
        Resolve requested skill names to actual skill paths.
        Returns (resolved_skills, unmatched_names)
        """
        resolved = {}
        unmatched = []
        available_names = list(available_skills.keys())

        for requested in requested_names:
            if requested in available_skills:
                # Exact match
                resolved[requested] = available_skills[requested]
            else:
                # Try fuzzy match
                fuzzy = self._fuzzy_match(requested, available_names)
                if fuzzy:
                    self._log(f"  '{requested}' → fuzzy matched to '{fuzzy}'")
                    resolved[fuzzy] = available_skills[fuzzy]
                else:
                    unmatched.append(requested)

        return resolved, unmatched

    def _check_existing_symlink(self, symlink_path: Path) -> Optional[str]:
        """
        Check if symlink exists and return what it points to.
        Returns None if no symlink exists, or the target path if it does.
        """
        if symlink_path.is_symlink():
            return str(symlink_path.readlink())
        elif symlink_path.exists():
            return "REAL_DIR"  # It's a real directory, not a symlink
        return None

    def _create_symlink(self, symlink_path: Path, target_path: Path, force: bool = False) -> bool:
        """
        Create a symlink. Returns True on success, False otherwise.
        """
        try:
            if symlink_path.exists() or symlink_path.is_symlink():
                if not force:
                    existing_target = self._check_existing_symlink(symlink_path)
                    if existing_target == "REAL_DIR":
                        self._log(f"  ⚠ {symlink_path.name} is a real directory, not a symlink — skipping")
                        return False
                    elif existing_target == str(target_path):
                        self._log(f"  ✓ {symlink_path.name} already points to correct target")
                        return True
                    else:
                        self._log(f"  ⚠ {symlink_path.name} already points to: {existing_target}")
                        return False
                # Force: remove old symlink
                symlink_path.unlink()

            # Create parent directory if needed
            symlink_path.parent.mkdir(parents=True, exist_ok=True)

            # Create symlink
            symlink_path.symlink_to(target_path)
            return True
        except Exception as e:
            self._error(f"  ✗ Failed to create symlink for {symlink_path.name}: {e}")
            return False

    def _log(self, message: str):
        """Print info message."""
        print(message)

    def _error(self, message: str):
        """Print error message to stderr."""
        print(f"✗ {message}", file=sys.stderr)

    def run(self, project_name: str, requested_skills: List[str], force: bool = False) -> int:
        """
        Main execution logic.
        Returns 0 on success, 1 on failure.
        """
        # Phase 1: Locate project
        project_path = self.install_dir / project_name
        if not project_path.exists():
            self._error(f"Project not found: {project_path}")
            self._error(f"Install directory: {self.install_dir}")
            return 1

        self._log(f"📁 Project: {project_path}")

        # Phase 2: Discover skills
        available_skills = self._discover_skills(project_path)
        if not available_skills:
            self._error(f"No skills found in {project_path}/skills/")
            return 1

        self._log(f"📚 Found {len(available_skills)} skill(s): {', '.join(sorted(available_skills.keys()))}")

        # Phase 3: Resolve requested skill names
        if not requested_skills:
            # Interactive mode
            self._log("\nWhich skills do you want to link? (space-separated names, or 'all')")
            user_input = input("> ").strip()
            if user_input.lower() == "all":
                requested_skills = list(available_skills.keys())
            else:
                requested_skills = user_input.split()

        resolved_skills, unmatched = self._resolve_skill_names(requested_skills, available_skills)

        if unmatched:
            self._error(f"Skills not found (or fuzzy-matched): {', '.join(unmatched)}")

        if not resolved_skills:
            self._error("No skills to link.")
            return 1

        self._log(f"\n🔗 Linking {len(resolved_skills)} skill(s):")

        # Phase 4: Create symlinks
        success_count = 0
        for skill_name, skill_path in sorted(resolved_skills.items()):
            symlink_path = self.symlinks_dir / skill_name
            if self._create_symlink(symlink_path, skill_path, force=force):
                self._log(f"  ✓ {skill_name}")
                success_count += 1

        # Phase 5: Verify
        self._log(f"\n✅ Successfully linked {success_count}/{len(resolved_skills)} skill(s)")

        if success_count == len(resolved_skills):
            return 0
        else:
            return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    force = False
    args = sys.argv[1:]
    
    if args[0] == "--force":
        force = True
        args = args[1:]
    
    if not args:
        print(__doc__)
        sys.exit(1)

    project_name = args[0]
    requested_skills = args[1:] if len(args) > 1 else []

    linker = SkillLinker()
    exit_code = linker.run(project_name, requested_skills, force=force)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
