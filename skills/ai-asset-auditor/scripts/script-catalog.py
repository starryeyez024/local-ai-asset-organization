#!/usr/bin/env python3
"""Read-only local script inventory and deterministic name lookup (Python 3.11+)."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import difflib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

SCHEMA_VERSION = 1
SCRIPT_SUFFIXES = {".py": "python", ".sh": "sh", ".bash": "bash", ".zsh": "zsh",
                   ".js": "node", ".mjs": "node", ".ps1": "powershell",
                   ".rb": "ruby", ".pl": "perl"}
DOC_SUFFIXES = {".md", ".txt", ".rst", ".pdf", ".html"}
DATA_SUFFIXES = {".json", ".toml", ".yaml", ".yml", ".csv", ".db"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox",
             ".mypy_cache", ".pytest_cache", ".next", "dist", "build", "logs",
             ".cache", "vendor"}
PRIVATE_NAMES = {".env", "credentials", "secrets", "private_key", "id_rsa"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$")
FINDING_PATTERNS = {
    "absolute_path": re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\\\Users\\\\)"),
    "location_derived_root": re.compile(r"(?:parent\s*\.\s*parent|dirname\s*\(|__file__|BASH_SOURCE)"),
    "sibling_resource": re.compile(r"(?:import\s+[\w.]+|from\s+[\w.]+\s+import|__dirname|Path\(__file__\))"),
}


class CatalogError(Exception):
    def __init__(self, code: str, message: str, **details: object):
        super().__init__(message)
        self.code = code
        self.details = details


def path_from(value: str, base: Path) -> Path:
    """Expand home and anchor relative paths to the containing config file."""
    expanded = Path(value).expanduser()
    return (expanded if expanded.is_absolute() else base / expanded).resolve()


def selected_config(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    preferred = Path.home() / ".config/agent-tools/agent-config.toml"
    legacy = Path.home() / ".config/ai-tools/ai-tools.toml"
    return preferred if preferred.exists() or not legacy.exists() else legacy


def read_toml(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CatalogError("configuration", f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogError("configuration", f"Expected a TOML table in {path}")
    return data


def settings(config_path: Path) -> dict:
    data = read_toml(config_path)
    section = data.get("script_catalog", {})
    if not isinstance(section, dict):
        raise CatalogError("configuration", "[script_catalog] must be a table")
    raw_sources = section.get("sources", {})
    raw_workdirs = section.get("working_dirs", {})
    raw_interpreters = section.get("interpreters", {})
    if not all(isinstance(value, dict) for value in (raw_sources, raw_workdirs, raw_interpreters)):
        raise CatalogError("configuration", "sources, working_dirs, and interpreters must be tables")
    sources = {}
    for key, value in raw_sources.items():
        if not isinstance(value, str) or not value.strip():
            raise CatalogError("configuration", f"Invalid source binding: {key}")
        sources[key] = path_from(value, config_path.parent)
    workdirs = {}
    for key, value in raw_workdirs.items():
        if not isinstance(value, str) or not value.strip():
            raise CatalogError("configuration", f"Invalid working directory binding: {key}")
        workdirs[key] = path_from(value, config_path.parent)
    interpreters = {}
    for key, value in raw_interpreters.items():
        if not isinstance(value, str) or not value.strip():
            raise CatalogError("configuration", f"Invalid interpreter binding: {key}")
        interpreters[key] = value
    catalog_value = section.get("path", "script-catalog.toml")
    if not isinstance(catalog_value, str) or not catalog_value.strip():
        raise CatalogError("configuration", "[script_catalog].path must be a path")
    return {"config": config_path, "catalog": path_from(catalog_value, config_path.parent),
            "sources": sources, "working_dirs": workdirs, "interpreters": interpreters}


def safe_relative(value: str, field: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or (os.name != "nt" and re.match(r"^[A-Za-z]:", value)):
        raise CatalogError("invalid_catalog", f"{field} must be relative to its source root: {value}")
    return path


def records(catalog_path: Path) -> list[dict]:
    data = read_toml(catalog_path)
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("scripts"), list):
        raise CatalogError("invalid_catalog", "Catalog needs schema_version = 1 and [[scripts]] records")
    result = []
    ids = set()
    spelling = defaultdict(set)
    for n, row in enumerate(data["scripts"], 1):
        if not isinstance(row, dict):
            raise CatalogError("invalid_catalog", f"Record {n} must be a table")
        required = ("id", "name", "aliases", "description", "source", "entrypoint",
                    "runtime", "args", "working_dir", "platforms", "status")
        missing = [key for key in required if key not in row]
        if missing:
            raise CatalogError("invalid_catalog", f"Record {n} missing: {', '.join(missing)}")
        rid = row["id"]
        if not isinstance(rid, str) or not ID_RE.fullmatch(rid):
            raise CatalogError("invalid_catalog", f"Record {n} has invalid qualified ID")
        if rid.casefold() in ids:
            raise CatalogError("invalid_catalog", f"Duplicate qualified ID: {rid}")
        ids.add(rid.casefold())
        for key in ("name", "description", "source", "runtime"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise CatalogError("invalid_catalog", f"{rid}: {key} must be nonempty text")
        for key in ("aliases", "args", "platforms"):
            if not isinstance(row[key], list) or any(not isinstance(v, str) for v in row[key]):
                raise CatalogError("invalid_catalog", f"{rid}: {key} must be a string array")
        if not isinstance(row["entrypoint"], str) or not isinstance(row["working_dir"], str):
            raise CatalogError("invalid_catalog", f"{rid}: entrypoint and working_dir must be text")
        safe_relative(row["entrypoint"], f"{rid}.entrypoint")
        safe_relative(row["working_dir"], f"{rid}.working_dir")
        if "working_dir_binding" in row and (not isinstance(row["working_dir_binding"], str) or not row["working_dir_binding"]):
            raise CatalogError("invalid_catalog", f"{rid}: invalid working_dir_binding")
        if row["status"] not in ("active", "archived"):
            raise CatalogError("invalid_catalog", f"{rid}: status must be active or archived")
        if not row["platforms"] or not set(row["platforms"]) <= {"macos", "windows", "linux"}:
            raise CatalogError("invalid_catalog", f"{rid}: invalid platforms")
        names = [row["name"], *row["aliases"], Path(row["entrypoint"]).name]
        if any(not value.strip() for value in names):
            raise CatalogError("invalid_catalog", f"{rid}: empty name or alias")
        for value in names:
            spelling[value.casefold()].add(value)
        result.append(row)
    collisions = {key: sorted(values) for key, values in spelling.items() if len(values) > 1}
    if collisions:
        raise CatalogError("case_collision", "Case-only script name collision", collisions=collisions)
    return result


def platform_name() -> str:
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    return "linux"


def target_for(row: dict, cfg: dict) -> tuple[Path, Path]:
    source = cfg["sources"].get(row["source"])
    if source is None:
        raise CatalogError("unbound_source", f"No source binding for {row['source']}", source=row["source"])
    target = (source / row["entrypoint"]).resolve()
    work_binding = row.get("working_dir_binding")
    work_root = cfg["working_dirs"].get(work_binding) if work_binding else source
    if work_root is None:
        raise CatalogError("unbound_working_dir", f"No working directory binding for {work_binding}", working_dir_binding=work_binding)
    working = (work_root / row["working_dir"]).resolve()
    if not target.is_relative_to(source) or not working.is_relative_to(work_root):
        raise CatalogError("invalid_catalog", f"{row['id']} escapes source binding {row['source']}")
    if not target.is_file():
        raise CatalogError("stale_entry", f"Missing target for {row['id']}", source=row["source"], target=str(target))
    if not working.is_dir():
        raise CatalogError("stale_entry", f"Missing working directory for {row['id']}", source=row["source"], working_dir=str(working))
    return target, working


def interpreter_for(runtime: str, cfg: dict) -> str:
    if runtime == "executable":
        return ""
    override = cfg["interpreters"].get(runtime)
    if override:
        candidate = path_from(override, cfg["config"].parent) if ("/" in override or "\\" in override or override.startswith("~")) else shutil.which(override)
        if candidate and Path(candidate).is_file():
            return str(candidate)
        raise CatalogError("missing_interpreter", f"Configured {runtime} interpreter is unavailable", runtime=runtime)
    if runtime == "python":
        return sys.executable
    default = {"sh": "sh", "bash": "bash", "zsh": "zsh", "node": "node", "powershell": "pwsh", "ruby": "ruby", "perl": "perl"}.get(runtime)
    if default is None:
        raise CatalogError("unsupported_runtime", f"Unknown runtime: {runtime}", runtime=runtime)
    if runtime in ("sh", "bash", "zsh") and os.name == "nt":
        raise CatalogError("missing_interpreter", "Shell scripts need an explicit Windows interpreter binding", runtime=runtime)
    found = shutil.which(default)
    if not found:
        raise CatalogError("missing_interpreter", f"Interpreter unavailable: {default}", runtime=runtime)
    return found


def invocation(row: dict, cfg: dict) -> dict:
    if platform_name() not in row["platforms"]:
        raise CatalogError("unsupported_platform", f"{row['id']} does not support {platform_name()}", platforms=row["platforms"])
    target, working = target_for(row, cfg)
    interpreter = interpreter_for(row["runtime"], cfg)
    argv = ([interpreter] if interpreter else []) + [str(target), *row["args"]]
    return {"schema_version": SCHEMA_VERSION, "status": "ok", "id": row["id"],
            "file": str(target), "interpreter": interpreter or None, "argv": argv,
            "args": row["args"], "working_dir": str(working), "runtime": row["runtime"],
            "provenance": {"catalog": str(cfg["catalog"]), "config": str(cfg["config"]),
                           "source": row["source"], "source_root": str(cfg["sources"][row["source"]]),
                           "working_dir_binding": row.get("working_dir_binding")}}


def resolve(name: str, rows: list[dict], cfg: dict) -> dict:
    exact = [row for row in rows if row["id"].casefold() == name.casefold()]
    if exact:
        row = exact[0]
    else:
        matches = [row for row in rows if row["status"] == "active" and name.casefold() in
                   {v.casefold() for v in [row["name"], *row["aliases"], Path(row["entrypoint"]).name]}]
        if len(matches) > 1:
            raise CatalogError("ambiguous", f"Ambiguous script name: {name}", candidates=sorted(r["id"] for r in matches))
        if not matches:
            available = sorted({v for row in rows if row["status"] == "active"
                                for v in [row["id"], row["name"], *row["aliases"], Path(row["entrypoint"]).name]})
            raise CatalogError("unknown", f"Unknown active script: {name}", suggestions=difflib.get_close_matches(name, available, n=3))
        row = matches[0]
    if row["status"] != "active":
        raise CatalogError("inactive", f"Script is archived: {row['id']}", id=row["id"])
    return invocation(row, cfg)


def git_owner(path: Path) -> str | None:
    try:
        run = subprocess.run(["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=2, check=False)
        return str(Path(run.stdout.strip()).resolve()) if run.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def classify(path: Path) -> tuple[str, str | None, list[str]]:
    if path.name.casefold().endswith(" alias") or path.suffix.casefold() == ".alias":
        return "alias", None, []
    try:
        with path.open("rb") as stream:
            head = stream.read(16384)
    except OSError:
        return "inaccessible", None, []
    if b"\0" in head:
        return "binary", None, []
    suffix = path.suffix.lower()
    if suffix in SCRIPT_SUFFIXES:
        kind, runtime = "script", SCRIPT_SUFFIXES[suffix]
    elif suffix in DOC_SUFFIXES:
        kind, runtime = "documentation", None
    elif suffix in DATA_SUFFIXES:
        kind, runtime = "data", None
    elif head.startswith(b"#!"):
        kind, runtime = "script", "unknown"
    elif suffix == "":
        kind, runtime = "uncertain", None
    else:
        kind, runtime = "other", None
    findings = []
    if kind == "script":
        sample = head.decode("utf-8", errors="replace")
        findings = [name for name, pattern in FINDING_PATTERNS.items() if pattern.search(sample)]
    return kind, runtime, findings


def inventory(roots: dict[str, Path], callers: list[Path], output: Path | None,
              limit: int, kind_filter: str | None) -> dict:
    items = []
    seen = set()
    issues = []
    for source_id, root in roots.items():
        if not root.is_dir():
            issues.append({"source": source_id, "issue": "missing_or_inaccessible_root"})
            continue
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d.casefold() not in SKIP_DIRS and not (Path(directory) / d).is_symlink())
            for filename in sorted(files):
                if (filename.startswith(".") or filename.lower() in PRIVATE_NAMES or
                        filename.lower().endswith((".log", ".key", ".pem", ".p12"))):
                    continue
                path = Path(directory) / filename
                try:
                    actual = path.resolve(strict=True)
                except (OSError, RuntimeError):
                    issues.append({"source": source_id, "path": str(path), "issue": "unreadable_target"})
                    continue
                if not actual.is_relative_to(root) or not actual.is_file():
                    issues.append({"source": source_id, "path": str(path), "issue": "outside_root_or_nonfile"})
                    continue
                if actual in seen:
                    continue
                seen.add(actual)
                kind, runtime, findings = classify(actual)
                if kind == "other":
                    continue
                owner = git_owner(actual)
                owner_path = Path(owner) if owner else None
                items.append({"source": source_id, "path": str(path), "relative_path": str(path.relative_to(root)),
                              "kind": kind, "runtime": runtime, "git_root": owner,
                              "git_relative_path": str(actual.relative_to(owner_path)) if owner_path and actual.is_relative_to(owner_path) else None,
                              "findings": findings})
    names = {Path(item["path"]).name for item in items if item["kind"] == "script"}
    caller_hits = []
    for caller in callers:
        if not caller.is_file() or caller.name.lower() in PRIVATE_NAMES:
            continue
        try:
            content = caller.read_text(encoding="utf-8", errors="replace")[:65536]
        except OSError:
            continue
        matched = sorted(name for name in names if name in content)
        if matched:
            caller_hits.append({"path": str(caller), "script_filenames": matched[:30]})
    shown = [item for item in items if not kind_filter or item["kind"] == kind_filter]
    result = {"schema_version": SCHEMA_VERSION, "status": "ok", "roots": {k: str(v) for k, v in roots.items()},
              "generated_at": datetime.now(timezone.utc).isoformat(), "counts": dict(Counter(i["kind"] for i in items)),
              "items": shown[:limit], "truncated_items": max(0, len(shown) - limit),
              "caller_hits": caller_hits, "issues": issues[:limit], "truncated_issues": max(0, len(issues) - limit)}
    if output:
        candidates = [i for i in items if i["kind"] == "script"]
        output.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "candidates": candidates}, indent=2) + "\n")
    return result


def emit(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
        return
    if result["status"] == "error":
        print(f"{result['code']}: {result['message']}")
        for key in ("candidates", "suggestions", "source", "target"):
            if key in result:
                print(f"  {key}: {result[key]}")
    elif "argv" in result:
        for key in ("id", "file", "interpreter", "args", "working_dir"):
            print(f"{key}: {result[key]}")
    elif "scripts" in result:
        for row in result["scripts"]:
            print(f"{row['id']}  {row['description']}")
    elif "records" in result:
        print(f"Validated {result['records']} records; failures: {len(result['failures'])}")
        for failure in result["failures"][:20]:
            print(f"  {failure['id']}: {failure['code']}: {failure['message']}")
    else:
        print(f"Inventory: {result['counts']}; issues: {len(result['issues'])}")
        for item in result["items"][:100]:
            if item["kind"] in ("script", "uncertain", "binary"):
                print(f"{item['kind']}: {item['source']}/{item['relative_path']}")
        omitted = max(0, len(result["items"]) - 100) + result["truncated_items"]
        if omitted:
            print(f"... {omitted} more items (use --json or --limit for details)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Setup TOML; defaults to preferred then legacy path")
    parser.add_argument("--json", action="store_true", help="Emit versioned JSON")
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("validate")
    lookup = sub.add_parser("resolve")
    lookup.add_argument("name")
    listing = sub.add_parser("list")
    listing.add_argument("--source")
    listing.add_argument("--status", choices=("active", "archived"), default="active")
    scan = sub.add_parser("inventory")
    scan.add_argument("--root", action="append", default=[], metavar="ID=PATH", help="Selected source root; repeatable")
    scan.add_argument("--caller", action="append", default=[], help="Explicit caller file to inspect")
    scan.add_argument("--output-candidates", type=Path, help="Explicit derived candidate JSON output")
    scan.add_argument("--kind", choices=("script", "binary", "documentation", "data", "alias", "uncertain", "inaccessible"))
    scan.add_argument("--limit", type=int, default=200, help="Maximum returned items and issues (1-1000)")
    args = parser.parse_args(argv)
    try:
        cfg = None
        if args.operation != "inventory" or not args.root or args.config:
            cfg = settings(selected_config(args.config))
        if args.operation == "inventory":
            if not 1 <= args.limit <= 1000:
                raise CatalogError("usage", "--limit must be between 1 and 1000")
            roots = dict(cfg["sources"]) if cfg and not args.root else {}
            for binding in args.root:
                if "=" not in binding:
                    raise CatalogError("usage", "--root needs ID=PATH")
                key, value = binding.split("=", 1)
                if not key or not value:
                    raise CatalogError("usage", "--root needs ID=PATH")
                roots[key] = Path(value).expanduser().resolve()
            if not roots:
                raise CatalogError("usage", "No source roots configured or selected")
            if args.output_candidates and cfg and args.output_candidates.expanduser().resolve() == cfg["catalog"]:
                raise CatalogError("usage", "Candidate output cannot overwrite the maintained catalog")
            result = inventory(roots, [Path(v).expanduser().resolve() for v in args.caller],
                               args.output_candidates, args.limit, args.kind)
        else:
            rows = records(cfg["catalog"])
            if args.operation == "resolve":
                result = resolve(args.name, rows, cfg)
            elif args.operation == "list":
                selected = [r for r in rows if r["status"] == args.status and (not args.source or r["source"] == args.source)]
                result = {"schema_version": SCHEMA_VERSION, "status": "ok", "scripts":
                          [{"id": r["id"], "name": r["name"], "description": r["description"], "source": r["source"],
                            "status": r["status"]} for r in selected]}
            else:
                failures = []
                for row in rows:
                    try:
                        target_for(row, cfg)
                        if row["status"] == "active" and platform_name() in row["platforms"]:
                            interpreter_for(row["runtime"], cfg)
                    except CatalogError as exc:
                        failures.append({"id": row["id"], "code": exc.code, "message": str(exc)})
                result = {"schema_version": SCHEMA_VERSION, "status": "ok" if not failures else "error",
                          "code": "validation_failed" if failures else None, "records": len(rows), "failures": failures}
        emit(result, args.json)
        return 0 if result["status"] == "ok" else 1
    except CatalogError as exc:
        emit({"schema_version": SCHEMA_VERSION, "status": "error", "code": exc.code,
              "message": str(exc), **exc.details}, args.json)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
