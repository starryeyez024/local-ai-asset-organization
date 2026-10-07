---
name: skill-linker
description: >
  Selectively link skills from a project under the configured physical asset root
  into the local skills hub. Use when the user wants one, several, or all skills
  from a downloaded project available locally.
---

# Skill Linker

Use this skill for selective local symlinks. It does not edit, move, copy, or install the source skill folders. A link is a local delivery path, not a guarantee that every tool or hosted runtime will discover the skill; check the repository's compatibility guide for the target runtime.

## Configuration

Read `~/.config/ai-tools/ai-tools.toml` before linking. The script expects:

```toml
[directories]
install_dir = "/absolute/path/to/asset-root"
symlinks_dir = "/absolute/path/to/.agents/skills"
```

The file must already exist. Use the configured paths; do not create a second configuration file or infer an install root from an example. The linker can create `symlinks_dir` if it is missing.
The script requires Python 3.11 or newer so it can parse TOML with the standard library.

## Run

From this repository's root, invoke the bundled script explicitly:

```bash
python3 skills/skill-linker/skill-linker.py ktotten/local-ai-asset-organization ai-asset-auditor skill-override-safeguard
```

The project argument is relative to `install_dir` and must stay inside it. Skill names are optional:

```bash
python3 skills/skill-linker/skill-linker.py ktotten/local-ai-asset-organization
python3 skills/skill-linker/skill-linker.py ktotten/local-ai-asset-organization all
```

With no names, the script lists discovered skills and prompts for space-separated names or `all`. It first scans `skills/*/SKILL.md`; if none are found, it scans `*/SKILL.md` at the project root. It does not recursively discover nested skill folders. Close name matches are selected automatically and printed; review them before relying on a link.

For an intentional replacement of an existing symlink, use `--force`:

```bash
python3 skills/skill-linker/skill-linker.py --force ktotten/local-ai-asset-organization skill-override-safeguard
```

Without `--force`, a symlink pointing elsewhere is reported and skipped. With `--force`, the script replaces an existing symlink without a prompt. It never replaces a real file or directory. Review the current and proposed target before using `--force`, especially for a same-name skill from another project.

## Boundaries

- The script uses the local project folder path, not the Git remote, to locate source skills.
- It does not list available projects when a project path is wrong; it reports the path it checked.
- It does not detect nested `SKILL.md` files or decide which of two same-name skills should win across different tool roots.
- It does not verify that Cursor, Codex, Claude Code, or a hosted agent discovered the new link. Test that in the intended runtime.
- For a team or vendor skill override, follow `skill-override-safeguard` before changing the source or repointing a link.
