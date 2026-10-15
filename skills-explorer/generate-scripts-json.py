#!/usr/bin/env python3
"""Build a private, read-only Explorer view of registered scripts and local jobs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import shlex
import subprocess
import sys

RESOLVER = Path(__file__).resolve().parents[1] / "skills/ai-asset-auditor/scripts/script-catalog.py"
spec = importlib.util.spec_from_file_location("script_catalog", RESOLVER)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

# Reuse the Explorer's deterministic Work Stage, Tool, and Task Type rules.
# Skill-only labels (skill type, maturity, agile phase, role) do not apply.
SKILL_GENERATOR = Path(__file__).resolve().parent / "generate-skills-json.py"
skill_spec = importlib.util.spec_from_file_location("skill_catalog_generator", SKILL_GENERATOR)
skill_tags = importlib.util.module_from_spec(skill_spec)
skill_spec.loader.exec_module(skill_tags)

SCRIPT_STAGE_HINTS = {
    "gather": [r"\bcaptur", r"\bsync", r"\bmerge", r"\bpreview", r"\baudit"],
    "produce": [r"\bbackup", r"\bcommit", r"\bclean", r"\bdedupe", r"\bsync",
                r"\bmerge", r"\btag", r"\bapply", r"\baudit"],
    "reflect": [r"\bweekly[- ](?:review|synthesis)\b"],
}


def script_stage_tags(text: str) -> list[str]:
    """Apply shared stage rules, then script action hints and the skill fallback."""
    tags = set(skill_tags.auto_tag_stage(text))
    for stage, patterns in SCRIPT_STAGE_HINTS.items():
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            tags.add(stage)
    return sorted(tags or {"produce"}, key=skill_tags.STAGE_ORDER.index)


def command_paths(arguments: list[str], working_dir: Path) -> set[Path]:
    """Recognize explicit script file arguments; never execute a job command."""
    if not arguments:
        return set()
    tokens = list(arguments)
    if "-c" in tokens:
        index = tokens.index("-c")
        if index + 1 < len(tokens):
            try:
                tokens = shlex.split(tokens[index + 1])
            except ValueError:
                return set()
    paths: set[Path] = set()
    cwd = working_dir
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in ("&&", ";", "||", "|"):
            segments.append([])
        else:
            segments[-1].append(token)
    interpreters = {"python", "python3", "bash", "zsh", "sh", "node", "ruby", "perl", "pwsh",
                    "powershell"}
    for segment in segments:
        if not segment:
            continue
        command = Path(segment[0]).name
        if command == "cd" and len(segment) > 1:
            candidate = Path(segment[1]).expanduser()
            cwd = (candidate if candidate.is_absolute() else cwd / candidate).resolve()
            continue
        if command == "env" and len(segment) > 1:
            segment = [item for item in segment[1:] if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", item)]
            if not segment:
                continue
            command = Path(segment[0]).name
        target = None
        if Path(segment[0]).suffix.lower() in catalog.SCRIPT_SUFFIXES:
            target = segment[0]
        elif command in interpreters or re.fullmatch(r"python\d+(?:\.\d+)*", command):
            args = [item for item in segment[1:] if not item.startswith("-")]
            if args and Path(args[0]).suffix.lower() in catalog.SCRIPT_SUFFIXES:
                target = args[0]
        if target:
            candidate = Path(target).expanduser()
            paths.add((candidate if candidate.is_absolute() else cwd / candidate).resolve())
    return paths


def schedule_text(job: dict) -> str:
    interval = job.get("StartInterval")
    if isinstance(interval, int) and interval > 0:
        return f"Every {interval} seconds"
    entries = job.get("StartCalendarInterval")
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list) or not entries:
        return "Schedule not specified"
    weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    labels = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        day = entry.get("Weekday")
        prefix = f"{weekdays[day]} " if isinstance(day, int) and 0 <= day <= 6 else "Daily "
        if "Hour" in entry and "Minute" in entry:
            labels.append(f"{prefix}{entry['Hour']:02d}:{entry['Minute']:02d}")
        else:
            labels.append(prefix.strip())
    return ", ".join(labels) if labels else "Schedule not specified"


def launchd_jobs(directory: Path) -> list[dict]:
    jobs = []
    if not directory.is_dir():
        return jobs
    for plist in sorted(directory.glob("*.plist")):
        try:
            job = plistlib.loads(plist.read_bytes())
        except (OSError, ValueError, plistlib.InvalidFileException):
            continue
        if not isinstance(job, dict) or job.get("Disabled") is True:
            continue
        args = job.get("ProgramArguments")
        if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
            program = job.get("Program")
            args = [program] if isinstance(program, str) else []
        working = Path(job.get("WorkingDirectory") or Path.home()).expanduser()
        paths = command_paths(args, working)
        if paths:
            jobs.append({"kind": "launchd", "label": str(job.get("Label") or plist.stem),
                         "schedule": schedule_text(job), "definition": str(plist), "paths": paths})
    return jobs


def cron_jobs(lines: str, home: Path, definition: str = "user crontab", system: bool = False) -> list[dict]:
    jobs = []
    for number, line in enumerate(lines.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", stripped):
            continue
        parts = stripped.split(None, 6 if system else 5)
        required = 7 if system else 6
        if len(parts) < required:
            continue
        try:
            args = shlex.split(parts[6 if system else 5])
        except ValueError:
            continue
        paths = command_paths(args, home)
        if paths:
            jobs.append({"kind": "cron", "label": f"{Path(definition).name} line {number}",
                         "schedule": " ".join(parts[:5]), "definition": definition, "paths": paths})
    return jobs


def observed_jobs(home: Path, launch_agents: Path | list[Path] | None = None,
                  crontab_text: str | None = None, cron_files: list[Path] | None = None,
                  warnings: list[str] | None = None) -> list[dict]:
    directories = ([launch_agents] if isinstance(launch_agents, Path) else launch_agents)
    if directories is None:
        directories = [home / "Library/LaunchAgents", Path("/Library/LaunchAgents"),
                       Path("/Library/LaunchDaemons")]
    jobs = [job for directory in directories for job in launchd_jobs(directory)]
    if crontab_text is None and sys.platform != "win32":
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                crontab_text = result.stdout
            else:
                crontab_text = ""
                if warnings is not None and "no crontab" not in result.stderr.lower():
                    warnings.append(f"User crontab could not be read: {result.stderr.strip() or result.returncode}")
        except (OSError, subprocess.TimeoutExpired) as error:
            crontab_text = ""
            if warnings is not None:
                warnings.append(f"User crontab could not be read: {error}")
    jobs.extend(cron_jobs(crontab_text or "", home))
    files = cron_files if cron_files is not None else [Path("/etc/crontab"), *sorted(Path("/etc/cron.d").glob("*"))]
    for cron_file in files:
        try:
            content = cron_file.read_text()
        except OSError as error:
            if warnings is not None and cron_file.exists():
                warnings.append(f"Cron file could not be read: {cron_file}: {error}")
            continue
        jobs.extend(cron_jobs(content, home, str(cron_file), system=True))
    return jobs


def build(config: Path, home: Path | None = None, launch_agents: Path | None = None,
          crontab_text: str | None = None, cron_files: list[Path] | None = None) -> dict:
    home = home or Path.home()
    config_data = catalog.read_toml(config)
    if "script_catalog" not in config_data:
        return {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "scripts": []}
    cfg = catalog.settings(config)
    rows = catalog.records(cfg["catalog"])
    warnings: list[str] = []
    jobs = observed_jobs(home, launch_agents, crontab_text, cron_files, warnings)
    scripts = []
    for row in rows:
        try:
            target, working = catalog.target_for(row, cfg)
            file_path = str(target)
            status = row["status"]
        except catalog.CatalogError:
            file_path = ""
            working = None
            status = "missing"
        matched = [
            {key: job[key] for key in ("kind", "label", "schedule", "definition")}
            for job in jobs if file_path and Path(file_path) in job["paths"]
        ]
        tag_text = " ".join((row["name"], row["description"], *row["aliases"]))
        repository = (skill_tags.source_repository(Path(file_path)) if file_path else
                      {"sourceOrg": "", "sourceRepo": "", "sourceLabel": "Unclassified"})
        scripts.append({"id": row["id"], "name": row["name"], "description": row["description"],
                        "aliases": row["aliases"], "source": row["source"], "file": file_path,
                        "sourceOrg": repository["sourceOrg"], "sourceRepo": repository["sourceRepo"],
                        "sourceLabel": repository["sourceLabel"],
                        "workingDirectory": str(working) if working else "", "runtime": row["runtime"],
                        "platforms": row["platforms"], "status": status, "jobs": matched,
                        "tags": {"stage": script_stage_tags(tag_text),
                                 "tool": skill_tags.auto_tag_tool(tag_text),
                                 "task": skill_tags.auto_tag_task(tag_text),
                                 "repository": [repository["sourceLabel"]]}})
    return {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "scripts": scripts, "scanWarnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = build(args.config.expanduser().resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "scripts-local.json").write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
