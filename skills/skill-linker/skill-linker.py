#!/usr/bin/env python3
"""
skill-linker: Selective symlink creation for AI project skills.

Creates symlinks from individual skills in an AI project directory into the
configured skill hub.

Usage:
  python3 skills/skill-linker/skill-linker.py <project-name> [skill1] [skill2] ...
  python3 skills/skill-linker/skill-linker.py <project-name>  # interactive mode
  python3 skills/skill-linker/skill-linker.py --force <project-name> [skill1] [skill2] ...
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import difflib
from asset_config import default_config_path, read_directories


class SkillLinker:
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with config file location."""
        self.config_path = Path(config_path).expanduser() if config_path else default_config_path()
        self.config = self._read_config()
        self.install_dir = Path(self.config["install_dir"]).expanduser()
        self.symlinks_dir = Path(self.config["symlinks_dir"]).expanduser()

    def _read_config(self) -> Dict[str, str]:
        """Read the shared setup configuration."""
        if not self.config_path.exists():
            self._error(f"Config file not found: {self.config_path}")
            self._error("Create ~/.config/agent-tools/agent-config.toml with these directories:")
            self._error("""
[directories]
install_dir = "/absolute/path/to/asset-root"
symlinks_dir = "/absolute/path/to/.agents/skills"
""")
            sys.exit(1)

        try:
            return read_directories(self.config_path)
        except ValueError as e:
            self._error(f"Error reading config: {e}")
            sys.exit(1)

    def _discover_skills(self, project_path: Path) -> Dict[str, Path]:
        """
        Scan project for skills (directories containing SKILL.md).
        Returns dict: {skill_name: skill_folder_path}
        
        Supports a single root SKILL.md, or two multi-skill structures:
        1. skills/*/SKILL.md (organized in skills/ subdirectory)
        2. */SKILL.md (skills at root level)
        """
        skills = {}

        if (project_path / "SKILL.md").is_file():
            return {project_path.name: project_path}
        
        # First, try organized structure: skills/*/SKILL.md
        skills_dir = project_path / "skills"
        if skills_dir.exists():
            for skill_folder in skills_dir.iterdir():
                if skill_folder.is_dir():
                    skill_md = skill_folder / "SKILL.md"
                    if skill_md.is_file():
                        skills[skill_folder.name] = skill_folder
        
        # If no organized skills found, try root-level structure: */SKILL.md
        if not skills:
            for item in project_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    skill_md = item / "SKILL.md"
                    if skill_md.is_file():
                        skills[item.name] = item

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
                # Suggest close names, but never link a different skill silently.
                fuzzy = self._fuzzy_match(requested, available_names)
                if fuzzy:
                    self._log(f"  '{requested}' was not found. Did you mean '{fuzzy}'?")
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
                if not symlink_path.is_symlink():
                    self._log(f"  ⚠ {symlink_path.name} is real content, not a symlink — skipping")
                    return False
                if not force:
                    existing_target = self._check_existing_symlink(symlink_path)
                    if symlink_path.resolve() == target_path.resolve():
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

    def run(self, project_name: str, requested_skills: List[str], force: bool = False, dry_run: bool = False) -> int:
        """
        Main execution logic.
        Returns 0 on success, 1 on failure.
        """
        # Phase 1: Locate project
        source = Path(project_name).expanduser()
        project_path = (self.install_dir / source).resolve()
        if not source.is_absolute() and not project_path.is_relative_to(self.install_dir.resolve()):
            self._error("Relative project paths must stay inside the install directory. Use an explicit absolute path for an existing repository elsewhere.")
            return 1
        if not project_path.is_dir():
            self._error(f"Project not found: {project_path}")
            self._error(f"Install directory: {self.install_dir}")
            return 1

        self._log(f"Configuration: {self.config_path}")
        self._log(f"📁 Project: {project_path}")

        # Phase 2: Discover skills
        available_skills = self._discover_skills(project_path)
        if not available_skills:
            self._error(f"No SKILL.md found at {project_path}, skills/*/, or */.")
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

        # Handle "all" keyword
        if requested_skills == ["all"]:
            resolved_skills = available_skills
            unmatched = []
        else:
            resolved_skills, unmatched = self._resolve_skill_names(requested_skills, available_skills)

            if unmatched:
                self._error(f"Skills not found: {', '.join(unmatched)}. No links changed.")
                return 1

            if not resolved_skills:
                self._error("No skills to link.")
                return 1

        # Report conflicts before making any change, including in preview mode.
        conflicts = []
        for name, target in resolved_skills.items():
            link = self.symlinks_dir / name
            if link.is_symlink():
                if link.resolve() != target.resolve() and not force:
                    conflicts.append(f"{link} already points to {link.readlink()}; use --force only for an intended replacement")
            elif link.exists():
                conflicts.append(f"{link} contains real content and will not be replaced")
        if conflicts:
            for conflict in conflicts:
                self._error(conflict)
            return 1
        if dry_run:
            for name, target in sorted(resolved_skills.items()):
                self._log(f"Would link: {self.symlinks_dir / name} -> {target}")
            self._log("Preview only; no links changed.")
            return 0

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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, help="Use a specific setup TOML file")
    parser.add_argument("--target-dir", type=Path, help="Link into a verified native tool directory instead of the configured hub")
    parser.add_argument("--dry-run", action="store_true", help="Preview links without changing files")
    parser.add_argument("--force", action="store_true", help="Replace conflicting symlinks; never replace real content")
    parser.add_argument("project", help="Project relative to install_dir, or an absolute path to an existing source")
    parser.add_argument("skills", nargs="*", help="Exact skill names, or all; omit to choose interactively")
    args = parser.parse_args()
    linker = SkillLinker(config_path=args.config)
    if args.target_dir is not None:
        target = args.target_dir.expanduser()
        if not target.is_absolute():
            parser.error("--target-dir must be an absolute path")
        linker.symlinks_dir = target
    exit_code = linker.run(args.project, args.skills, force=args.force, dry_run=args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
