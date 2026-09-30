#!/usr/bin/env python3
"""
Scan the ~/.agents/skills symlink farm for ixd-firefly AI-first skill files
and generate a tagged skills.json.

Usage:
    python3 generate-skills-json.py

    Set SKILLS_ROOT to scan a different skills directory; defaults to
    ~/.agents/skills.

        SKILLS_ROOT=/some/other/path python3 generate-skills-json.py

Reads SKILL.md files by walking ~/.agents/skills -- a flat, symlink-only farm
where each entry is named after a skill id and points at wherever that skill's
real folder currently lives (a mix of ~/AI Assets/... and legacy ~/Sites/...
paths, since the personal AI Asset Management System migration is still in
progress). This farm is the canonical, migration-proof list of "all installed
skills" that Cursor and Codex CLI read natively, so scanning it here means
this generator keeps working regardless of where any individual skill's real
folder physically lives today or moves to next.

For each farm entry we resolve the symlink to its real target, then infer
which of the 6 known ai-first-* modules the skill belongs to by looking for
the module name as a path component of that resolved target. Farm entries
that don't resolve to a known ai-first module (e.g. skills from other repos
that also get symlinked into the same farm) are skipped with a warning.
Extracts frontmatter, auto-tags by keyword analysis, writes skills.json.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()

# Threshold used by the "Maintain" inventory view to flag a skill's SKILL.md
# as stale (rendered in red in the UI) if it hasn't been touched in this long.
STALE_THRESHOLD_DAYS = 60

# The canonical, flat symlink farm of all installed skills. Cursor and Codex
# CLI read this natively; each entry is a symlink (occasionally a real dir)
# named after the skill id, pointing at the skill's real folder wherever it
# currently lives. Override with the SKILLS_ROOT env var to point the
# generator at a different directory (e.g. for testing); defaults to the
# real farm at ~/.agents/skills when unset.
AGENTS_SKILLS_FARM = Path(os.environ.get("SKILLS_ROOT", str(HOME / ".agents" / "skills")))

AI_FIRST_MODULES = [
    "ai-first-product-management",
    "ai-first-program-management",
    "ai-first-data-scientist",
    "ai-first-ux-design",
    "ai-first-ux-research",
    "uie-ai-first-content-creation",
]

MODULE_TO_ROLE = {
    "ai-first-product-management": "product-manager",
    "ai-first-program-management": "program-manager",
    "ai-first-data-scientist": "data-scientist",
    "ai-first-ux-design": "ux-designer",
    "ai-first-ux-research": "ux-researcher",
    "uie-ai-first-content-creation": "content-creator",
}

MODULE_DISPLAY = {
    "ai-first-product-management": "Product Management",
    "ai-first-program-management": "Program Management",
    "ai-first-data-scientist": "Data Science",
    "ai-first-ux-design": "UX Design",
    "ai-first-ux-research": "UX Research",
    "uie-ai-first-content-creation": "Content Creation",
}

TOOL_KEYWORDS = {
    "jira": [r"\bjira\b", r"\bepic\b", r"\bstory\b", r"\bsprint\b", r"\bticket\b", r"\bbacklog\b", r"\bissue\b"],
    "confluence": [r"\bconfluence\b", r"\bwiki\b"],
    "figma": [r"\bfigma\b", r"\bdesign.spec\b", r"\bmockup\b"],
    "analytics": [r"\banalytics\b", r"\bmetric\b", r"\btelemetry\b", r"\bdashboard\b", r"\bdata\b", r"\bsentiment\b"],
    "dita": [r"\bdita\b", r"\bdocumentation\b", r"\bcontent.management\b"],
    "git": [r"\bgit\b", r"\bmerge.request\b", r"\bbranch\b", r"\bcommit\b"],
    "google-docs": [r"\bgoogle.drive\b", r"\bgoogle.doc\b", r"\bdrive\b"],
    "slack": [r"\bslack\b", r"\bchannel\b", r"\bthread\b"],
    "design-system": [r"\bpatternfly\b", r"\bpf\b", r"\bdesign.system\b", r"\bcomponent\b", r"\btoken\b"],
}

TASK_KEYWORDS = {
    "planning": [r"\bplan\b", r"\bplanning\b", r"\bagenda\b", r"\bceremony\b", r"\bpi\b", r"\broadmap\b"],
    "analysis": [r"\banalyz\b", r"\banalysis\b", r"\baudit\b", r"\bassess\b", r"\bcompare\b", r"\breview\b", r"\bscore\b", r"\bprofile\b", r"\bheuristic\b"],
    "generation": [r"\bgenerat\b", r"\bdraft\b", r"\bcreate\b", r"\bauthor\b", r"\bwrite\b", r"\bproduc\b"],
    "validation": [r"\bvalidat\b", r"\bcheck\b", r"\bverif\b", r"\bcompliance\b", r"\bregression\b"],
    "reporting": [r"\breport\b", r"\bstatus\b", r"\bsummar\b", r"\bdashboard\b", r"\bupdate\b"],
    "discovery": [r"\bdiscover\b", r"\bresearch\b", r"\bintake\b", r"\bsignal\b", r"\bingest\b", r"\bscan\b", r"\bexplor\b"],
    "prioritization": [r"\bprioritiz\b", r"\brank\b", r"\brice\b", r"\bwsjf\b", r"\bscore\b", r"\bweight\b"],
    "handoff": [r"\bhandoff\b", r"\bhand.off\b", r"\bformat.handoff\b", r"\bpublish\b", r"\brelease\b"],
    "monitoring": [r"\bmonitor\b", r"\btrack\b", r"\bdetect\b", r"\bhealth\b", r"\bdrift\b", r"\bblocker\b"],
    "communication": [r"\bcomms\b", r"\bcommunicat\b", r"\bstakeholder\b", r"\bannounce\b", r"\bnewsletter\b"],
    "risk-management": [r"\brisk\b", r"\bmitigation\b", r"\bblocker\b", r"\bfeasibility\b", r"\bgap\b"],
    "refinement": [r"\bacceptance.criteria\b", r"\brefinement\b", r"\bepic\b", r"\bstory\b", r"\bbrief\b"],
}

# Where a skill sits in the agile/delivery lifecycle. Checked in priority order:
# retrospective signals are the most specific (looking back at completed work),
# planning signals are next (forward-looking, before work starts), everything
# else defaults to "in-progress" (tracking/reporting/coordinating live work).
PHASE_KEYWORDS = {
    "retrospective": [
        r"\bretro\b", r"\bretrospective\b", r"\blessons.learned\b", r"\bpost.mortem\b",
        r"\bprogram.health\b", r"\bbaseline\b", r"\bhistorical\b", r"\btrend\b",
    ],
    "planning": [
        r"\bplan\b", r"\bplanning\b", r"\broadmap\b", r"\bdiscovery\b", r"\bintake\b",
        r"\bprioritiz\b", r"\bcapacity\b", r"\bfeasibility\b", r"\bobjective\b",
        r"\bpi.planning\b", r"\bbacklog\b", r"\bwsjf\b", r"\brice\b",
    ],
}
PHASE_ORDER = ["retrospective", "planning", "in-progress"]
PHASE_DEFAULT = "in-progress"

# What kind of contribution a skill makes, independent of *when* it's used (that's
# PHASE above). A skill can match more than one bucket (esp. workflows, which chain
# gather -> produce -> reflect internally); atomic skills usually land in exactly one.
STAGE_KEYWORDS = {
    "gather": [
        r"\bingest", r"\bcollect", r"\bdiscover", r"\bresearch", r"\bintake\b",
        r"\bretriev", r"\bexplor", r"\bscan\b", r"\bquery\b", r"\bfetch", r"\bload\b",
        r"\bwatch\b", r"\bmonitor\b", r"\btrack\b", r"\blook.up\b", r"\bidentify\b",
        r"\bpull\b",
    ],
    "produce": [
        r"\bgenerat", r"\bdraft", r"\bcreate", r"\bauthor", r"\bwrite", r"\bproduc",
        r"\bformat", r"\bcompos", r"\bbuild\b", r"\brecommend", r"\banalyz", r"\bassess",
        r"\bscore\b", r"\bprioritiz", r"\brank\b", r"\bplan\b", r"\bplanning\b",
        r"\bvalidat", r"\bcheck\b", r"\bverif", r"\bcompar", r"\breview\b",
    ],
    "reflect": [
        r"\bretro\b", r"\bretrospective\b", r"\blessons.learned\b", r"\bpost.mortem\b",
        r"\bprogram.health\b", r"\bbaseline", r"\bhistorical\b", r"\btrend",
        r"\bhow.(you|we).work\b",
    ],
}
STAGE_ORDER = ["gather", "produce", "reflect"]


def extract_section(text: str, headings: list[str]) -> str:
    """Return the body text of the first matching '## Heading' section (up to the next '## ' or '---')."""
    for heading in headings:
        pattern = rf"^##\s+{re.escape(heading)}\s*$"
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not match:
            continue
        start = match.end()
        rest = text[start:]
        end_match = re.search(r"^##\s+|^---\s*$", rest, re.MULTILINE)
        body = rest[: end_match.start()] if end_match else rest
        return body.strip()
    return ""


def extract_table_rows(section_text: str) -> list[list[str]]:
    """Parse a markdown table into rows of cell strings (header row excluded)."""
    rows = []
    lines = [l for l in section_text.split("\n") if l.strip().startswith("|")]
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Skip separator rows like |---|---|
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else []  # drop header row


def strip_md_inline(text: str) -> str:
    """Strip bold/italic/backtick markdown markers for cleaner display text."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    return text.strip()


def extract_inputs(text: str) -> list[dict]:
    section = extract_section(text, ["Inputs", "Inputs to request or accept"])
    if not section:
        return []
    inputs = []
    for row in extract_table_rows(section):
        if len(row) < 2:
            continue
        name = strip_md_inline(row[0])
        required = ""
        if len(row) >= 3:
            required = strip_md_inline(row[2]).lower()
        inputs.append({"name": name, "required": required.startswith("y")})
    return inputs


def extract_required_skills(text: str) -> list[dict]:
    section = extract_section(text, ["Required skills"])
    if not section:
        return []
    skills = []
    for row in extract_table_rows(section):
        if len(row) < 2:
            continue
        raw = row[1]
        id_match = re.search(r"`([a-z0-9-]+)`", raw)
        skill_id = id_match.group(1) if id_match else ""
        label = strip_md_inline(re.sub(r"\s*\(`[a-z0-9-]+`\)", "", raw)).strip() or skill_id
        if skill_id:
            skills.append({"id": skill_id, "label": label})
    return skills


def extract_trigger(text: str) -> str:
    section = extract_section(text, ["Trigger", "When to Use", "When to use"])
    if not section:
        return ""
    # Collapse to plain text, drop markdown table/list markers, take first ~400 chars
    plain = re.sub(r"[|`*_]", "", section)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:400]


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown text (simple parser, no PyYAML needed)."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result = {}
    current_key = None
    current_val = ""
    in_metadata = False
    for line in block.split("\n"):
        if line.startswith("  ") and current_key:
            stripped = line.strip()
            if in_metadata and ":" in stripped and not stripped.startswith("-"):
                k, v = stripped.split(":", 1)
                if not isinstance(result.get("metadata"), dict):
                    result["metadata"] = {}
                result["metadata"][k.strip()] = v.strip().strip('"').strip("'")
            else:
                in_metadata = False
                current_val += " " + stripped
                result[current_key] = current_val.strip()
        else:
            in_metadata = False
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                current_key = k.strip()
                current_val = v.strip().strip('"').strip("'")
                if current_key == "metadata" and current_val == "":
                    result["metadata"] = {}
                    in_metadata = True
                    continue
                if current_val == ">":
                    current_val = ""
                elif current_val.startswith("[") and current_val.endswith("]"):
                    items = current_val[1:-1].split(",")
                    result[current_key] = [i.strip().strip('"').strip("'") for i in items if i.strip()]
                    current_key = None
                    continue
                result[current_key] = current_val
    return result


def auto_tag_tool(text: str) -> list[str]:
    tags = []
    lower = text.lower()
    for tool, patterns in TOOL_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                tags.append(tool)
                break
    return sorted(set(tags))


def auto_tag_task(text: str) -> list[str]:
    tags = []
    lower = text.lower()
    for task, patterns in TASK_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                tags.append(task)
                break
    return sorted(set(tags))


def auto_tag_stage(text: str) -> list[str]:
    lower = text.lower()
    tags = []
    for stage, patterns in STAGE_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                tags.append(stage)
                break
    return sorted(set(tags), key=STAGE_ORDER.index)


def auto_tag_phase(text: str) -> str:
    lower = text.lower()
    for phase in ["retrospective", "planning"]:
        for pattern in PHASE_KEYWORDS[phase]:
            if re.search(pattern, lower):
                return phase
    return PHASE_DEFAULT


def resolve_module(skill_file: Path) -> str:
    """Infer the module for a resolved SKILL.md path. First checks for known
    ixd-firefly module names in path components. For non-ixd-firefly skills,
    detects a parent-directory name (e.g., 'anthropics', 'global-engineering',
    'rhecosystemappeng') and uses that as the module label. Falls back to
    'other' if no parent directory can be identified."""
    parts = skill_file.parts
    
    # Check for known ixd-firefly modules first
    for module in AI_FIRST_MODULES:
        if module in parts:
            return module
    
    # For non-ixd-firefly skills, try to detect a meaningful parent dir name.
    # Look for names that appear under /AI Assets/ or similar top-level org paths
    # by finding the first component after the home directory.
    try:
        # Get the relative path from home, if applicable
        if str(HOME) in str(skill_file):
            rel_path = skill_file.relative_to(HOME)
            parts = rel_path.parts
            # parts[0] is usually 'AI Assets', 'Sites', etc.
            # parts[1] if present could be 'ixd-firefly', 'anthropics', etc.
            if len(parts) > 1 and parts[0] in ("AI Assets", "Sites"):
                org_or_module = parts[1]
                if org_or_module and org_or_module not in ("ixd-firefly", "."):
                    return org_or_module.lower().replace(" ", "-")
            elif len(parts) > 0 and parts[0] not in ("AI Assets", "Sites", "."):
                return parts[0].lower().replace(" ", "-")
    except (ValueError, IndexError):
        pass
    
    return "other"


def find_skill_files() -> list[tuple[str, Path]]:
    """Discover skills by walking the ~/.agents/skills symlink farm and resolving
    each entry to its real SKILL.md file. Determines the module for each skill:
    ixd-firefly skills are identified by their path, while non-ixd-firefly skills
    are assigned a module based on their parent directory name (e.g., 'anthropics',
    'rhecosystemappeng') or defaulting to 'other' if unrecognizable."""
    if not AGENTS_SKILLS_FARM.exists():
        print(f"Error: skills farm not found at {AGENTS_SKILLS_FARM}", file=sys.stderr)
        return []

    results = []
    seen_real_paths = set()
    skipped_broken = 0
    included_non_ixd = 0

    for entry in sorted(AGENTS_SKILLS_FARM.iterdir()):
        if entry.name.startswith("."):
            continue

        try:
            real = entry.resolve(strict=True)
        except (OSError, RuntimeError):
            print(f"Warning: broken symlink in skills farm: {entry.name}", file=sys.stderr)
            skipped_broken += 1
            continue

        # Farm entries are usually a symlink to a directory containing SKILL.md,
        # but tolerate a symlink straight to a SKILL.md file too.
        if real.is_dir():
            skill_file = real / "SKILL.md"
        elif real.name == "SKILL.md":
            skill_file = real
        else:
            skill_file = None

        if skill_file is None or not skill_file.exists():
            print(f"Warning: no SKILL.md found for farm entry '{entry.name}' -> {real}", file=sys.stderr)
            skipped_broken += 1
            continue

        # Dedup in case multiple farm entries resolve to the same real skill.
        if skill_file in seen_real_paths:
            continue

        module = resolve_module(skill_file)
        # Now includes ALL skills (ixd-firefly and non-ixd-firefly)
        if module not in AI_FIRST_MODULES:
            included_non_ixd += 1

        seen_real_paths.add(skill_file)
        results.append((module, skill_file))

    if skipped_broken:
        print(f"Skipped {skipped_broken} broken/invalid farm entries", file=sys.stderr)
    if included_non_ixd:
        print(
            f"Included {included_non_ixd} non-ixd-firefly skills with detected or default module labels",
            file=sys.stderr,
        )

    return results


def _frontmatter_name(skill_md: Path) -> str:
    """Read just the frontmatter `name:` field of a SKILL.md, falling back to
    its parent folder name -- same convention process_skill() uses."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    fm = parse_frontmatter(text)
    return fm.get("name") or skill_md.parent.name


def build_inventory() -> tuple[list[dict], dict]:
    """Walk EVERY entry in the skills farm -- not just the ones that resolve to
    a known ixd-firefly module -- for the 'Maintain' audit view. Reports each
    entry's true (resolved) path, whether its symlink is broken, whether it has
    a SKILL.md, how stale that SKILL.md is, whether it's also surfaced in the
    curated `skills` array, and flags two kinds of duplicate issues: the same
    real skill symlinked into the farm under more than one name, and two
    different real skills whose SKILL.md frontmatter claims the same `name`."""
    if not AGENTS_SKILLS_FARM.exists():
        return [], {}

    entries = []
    for entry in sorted(AGENTS_SKILLS_FARM.iterdir()):
        if entry.name.startswith("."):
            continue

        is_symlink = entry.is_symlink()
        broken = False
        real_dir = None
        skill_file = None

        if is_symlink:
            try:
                real = entry.resolve(strict=True)
            except (OSError, RuntimeError):
                broken = True
                real = entry.resolve(strict=False)
            true_path = str(real)
            if not broken:
                if real.is_dir():
                    real_dir = real
                    skill_file = real / "SKILL.md"
                elif real.name == "SKILL.md" and real.is_file():
                    skill_file = real
                    real_dir = real.parent
                # else: symlink target exists but isn't a skill folder/file --
                # leave skill_file unset so hasSkillMd comes out false below.
        else:
            real_dir = entry
            true_path = str(entry)
            if entry.is_dir():
                skill_file = entry / "SKILL.md"

        has_skill_md = bool(skill_file and skill_file.exists())
        if not has_skill_md:
            skill_file = None

        mtime_iso = None
        days_since = None
        fm_name = ""
        if skill_file is not None:
            try:
                mtime = skill_file.stat().st_mtime
                mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                mtime_iso = mtime_dt.date().isoformat()
                days_since = (datetime.now(tz=timezone.utc) - mtime_dt).days
            except OSError:
                pass
            fm_name = _frontmatter_name(skill_file)

        module = resolve_module(skill_file) if skill_file is not None else None

        entries.append({
            "name": entry.name,
            "isSymlink": is_symlink,
            "truePath": true_path,
            "broken": broken,
            "hasSkillMd": has_skill_md,
            "skillMdModified": mtime_iso,
            "daysSinceModified": days_since,
            "inCuratedView": module is not None,
            "module": module,
            "_realDir": str(real_dir) if real_dir else None,  # internal, dropped before output
            "_fmName": fm_name,  # internal, dropped before output
        })

    # Redundant symlinks: different farm entry names resolving to the same real folder.
    names_by_real_dir = {}
    for e in entries:
        if e["_realDir"]:
            names_by_real_dir.setdefault(e["_realDir"], []).append(e["name"])

    # Name collisions: same frontmatter `name:` field claimed from different real folders.
    real_dirs_by_fm_name = {}
    names_by_fm_name = {}
    for e in entries:
        if e["_fmName"]:
            real_dirs_by_fm_name.setdefault(e["_fmName"], set()).add(e["_realDir"])
            names_by_fm_name.setdefault(e["_fmName"], []).append(e["name"])

    for e in entries:
        redundant = []
        if e["_realDir"] and len(names_by_real_dir.get(e["_realDir"], [])) > 1:
            redundant = sorted(n for n in names_by_real_dir[e["_realDir"]] if n != e["name"])

        collisions = []
        if e["_fmName"] and len(real_dirs_by_fm_name.get(e["_fmName"], set())) > 1:
            collisions = sorted(set(n for n in names_by_fm_name[e["_fmName"]] if n != e["name"]))

        e["duplicates"] = {"redundantSymlinks": redundant, "nameCollisions": collisions}
        e["hasDuplicateIssue"] = bool(redundant) or bool(collisions)

        del e["_realDir"]
        del e["_fmName"]

    entries.sort(key=lambda e: e["name"])

    stats = {
        "total": len(entries),
        "broken": sum(1 for e in entries if e["broken"]),
        "withSkillMd": sum(1 for e in entries if e["hasSkillMd"]),
        "duplicateIssues": sum(1 for e in entries if e["hasDuplicateIssue"]),
        "stale": sum(1 for e in entries if e["daysSinceModified"] is not None and e["daysSinceModified"] > STALE_THRESHOLD_DAYS),
        "fresh": sum(1 for e in entries if e["daysSinceModified"] is not None and e["daysSinceModified"] <= STALE_THRESHOLD_DAYS),
        "inCuratedView": sum(1 for e in entries if e["inCuratedView"]),
        "notInCuratedView": sum(1 for e in entries if not e["inCuratedView"]),
        "staleThresholdDays": STALE_THRESHOLD_DAYS,
    }

    return entries, stats


def process_skill(module: str, skill_path: Path) -> dict | None:
    text = skill_path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    name = fm.get("name", skill_path.parent.name)
    description = fm.get("description", "").strip()

    if not description or description == "Stub skill. Definition pending.":
        status = "stub"
    else:
        status = fm.get("status", "active")

    if status == "stub":
        description = "Stub skill. Definition pending."

    display_name = name.replace("agents__", "").replace("shared__", "").replace("__", " / ").replace("-", " ").replace("_", " ").title()

    search_text = f"{name} {description}"
    body_start = text.find("---", 3)
    if body_start != -1:
        body_preview = text[body_start + 3:body_start + 1003]
        search_text += " " + body_preview

    role = MODULE_TO_ROLE.get(module, "other")
    # Generate module display name: convert hyphens/underscores to spaces and title case.
    # For known modules, use the mapping; for others (non-ixd-firefly), construct from module name.
    if module in MODULE_DISPLAY:
        module_display = MODULE_DISPLAY[module]
    else:
        module_display = module.replace("-", " ").replace("_", " ").title()
    
    tool_tags = auto_tag_tool(search_text)
    task_tags = auto_tag_task(search_text)
    phase_tag = auto_tag_phase(search_text) if status != "stub" else PHASE_DEFAULT
    stage_tags = auto_tag_stage(search_text) if status != "stub" else []
    if not stage_tags and status != "stub":
        stage_tags = ["produce"]

    if not task_tags and status != "stub":
        if "ingest" in name:
            task_tags = ["discovery"]
        elif "generate" in name or "draft" in name:
            task_tags = ["generation"]
        elif "validate" in name or "check" in name:
            task_tags = ["validation"]
        elif "workflow" in name:
            task_tags = ["planning"]
        elif "collect" in name or "explore" in name or "map" in name:
            task_tags = ["discovery"]
        elif "summarize" in name:
            task_tags = ["reporting"]
        elif "merge" in name or "prepare" in name:
            task_tags = ["handoff"]

    metadata = fm.get("metadata", {})
    persona = metadata.get("persona", "") if isinstance(metadata, dict) else ""
    owning_agent = metadata.get("owning_agent", "") if isinstance(metadata, dict) else ""
    skill_type = metadata.get("skill-type", "") if isinstance(metadata, dict) else ""
    agents_field = fm.get("agents", [])
    if isinstance(agents_field, str):
        agents_field = [agents_field]

    if status == "stub":
        trigger, inputs, required_skills = "", [], []
    else:
        trigger = extract_trigger(text)
        inputs = extract_inputs(text)
        required_skills = extract_required_skills(text)

    return {
        "id": name,
        "displayName": display_name,
        "description": description,
        "module": module,
        "moduleDisplay": module_display,
        "status": status,
        "persona": persona,
        "owningAgent": owning_agent or (agents_field[0] if agents_field else ""),
        "skillType": skill_type or ("workflow" if name.startswith("workflow-") else "atomic"),
        "trigger": trigger,
        "inputs": inputs,
        "requiredSkills": required_skills,
        "sourcePath": f"{module}/skills/{skill_path.parent.name}/SKILL.md",
        "tags": {
            "tool": tool_tags,
            "role": [role],
            "task": task_tags,
            "type": [skill_type or ("workflow" if name.startswith("workflow-") else "atomic")],
            "phase": [phase_tag],
            "stage": stage_tags,
        },
    }


def main():
    if not AGENTS_SKILLS_FARM.exists():
        print(f"Error: skills farm not found at {AGENTS_SKILLS_FARM}", file=sys.stderr)
        sys.exit(1)

    skill_files = find_skill_files()
    print(f"Found {len(skill_files)} skill files", file=sys.stderr)

    skills = []
    for module, path in skill_files:
        skill = process_skill(module, path)
        if skill:
            skills.append(skill)

    seen_ids = set()
    deduped = []
    for s in skills:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            deduped.append(s)
        else:
            print(f"Dedup: skipping duplicate {s['id']} from {s['module']}", file=sys.stderr)

    # Workflows chain gather -> produce -> reflect across the atomic skills they call.
    # Union each workflow's own keyword-derived stage tags with the stage tags of every
    # required skill it references, so a workflow shows every stage it actually touches.
    stage_lookup = {s["id"]: set(s["tags"]["stage"]) for s in deduped}
    for s in deduped:
        if s["skillType"] == "workflow" and s.get("requiredSkills"):
            combined = set(s["tags"]["stage"])
            for req in s["requiredSkills"]:
                combined |= stage_lookup.get(req["id"], set())
            if combined:
                s["tags"]["stage"] = sorted(combined, key=STAGE_ORDER.index)

    all_tools = sorted({t for s in deduped for t in s["tags"]["tool"]})
    all_roles = sorted({r for s in deduped for r in s["tags"]["role"]})
    all_tasks = sorted({t for s in deduped for t in s["tags"]["task"]})
    all_types = sorted({t for s in deduped for t in s["tags"]["type"]})
    all_phases = sorted({p for s in deduped for p in s["tags"]["phase"]}, key=PHASE_ORDER.index)
    all_stages = sorted({t for s in deduped for t in s["tags"]["stage"]}, key=STAGE_ORDER.index)

    inventory, inventory_stats = build_inventory()
    print(
        f"Inventory: {inventory_stats.get('total', 0)} farm entries "
        f"({inventory_stats.get('broken', 0)} broken, "
        f"{inventory_stats.get('duplicateIssues', 0)} with duplicate issues, "
        f"{inventory_stats.get('stale', 0)} stale >{STALE_THRESHOLD_DAYS}d)",
        file=sys.stderr,
    )

    output = {
        "generated": "auto",
        "skillCount": len(deduped),
        "activeCount": sum(1 for s in deduped if s["status"] != "stub"),
        "stubCount": sum(1 for s in deduped if s["status"] == "stub"),
        "filterOptions": {
            "type": all_types,
            "phase": all_phases,
            "stage": all_stages,
            "tool": all_tools,
            "role": all_roles,
            "task": all_tasks,
        },
        "skills": sorted(deduped, key=lambda s: s["displayName"]),
        "inventory": inventory,
        "inventoryStats": inventory_stats,
    }

    out_path = Path(__file__).resolve().parent / "skills.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(deduped)} skills ({output['activeCount']} active, {output['stubCount']} stubs) to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
