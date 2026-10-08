---
name: skill-linker
description: >
  Make selected repository skills available to local agents. Read the shared
  setup configuration, inspect the source and target tools, preview the links,
  then verify discovery in the intended runtime.
---

# Skill Linker

Use this skill to link repository skills without moving or editing their source files. The task is complete when the intended tool can find and use the selected skill, not just when a link exists.

## Configuration

Read `~/.config/agent-tools/agent-config.toml`. The linker and Explorer use the same settings:

```toml
[directories]
install_dir = "/absolute/path/to/asset-root"
symlinks_dir = "/absolute/path/to/.agents/skills"
```

For an existing setup, the script also reads `~/.config/ai-tools/ai-tools.toml` when the recommended file is absent. An explicit `--config /path/to/config.toml` takes precedence. If both files exist, the recommended path wins; inspect the configuration path printed by the script. Do not create a second configuration or migrate the user's files just to link one skill. Honor an explicitly selected configuration.

On a new machine, agree on the repository root and skills folder with the user and create the configuration as part of setup. Use absolute paths. Python 3.11 or newer is required. Keep `asset_config.py` beside `skill-linker.py` when copying this skill.

## Workflow

1. **Identify the source and tools.** Locate the existing repository and confirm which local tools/projects should use the skill. Inspect native skill roots, managed plugins, and same-name skills before changing anything. A marketplace package stays under its installer’s control; use that tool’s install or enable controls for it.
2. **Choose the source skill.** The script accepts a project relative to `install_dir`, or an explicit absolute path to an existing repository elsewhere. It supports a root `SKILL.md`, `skills/*/SKILL.md`, or immediate `*/SKILL.md` folders. Check for nested skills before linking a parent folder, and select individual folders if the runtime would discover them twice. Do not create a wrapper repository or relocate an existing checkout to satisfy the linker.
3. **Preview the links.** Run the bundled script with `--dry-run`, using exact skill names or `all`. Show source, destination, and any conflict. Misspellings produce suggestions and no changes.
4. **Apply the selected links.** Run the same command without `--dry-run` once the requested selection and destination are clear. An existing link to the same source is a no-op. Different targets require an intentional `--force` replacement; real files and directories are never overwritten. Preserve sources needed by other tools.
5. **Connect the target tool.** Check the compatibility guide and the installed tool's native discovery paths. If it reads the configured hub, no additional link is needed. Otherwise use `--target-dir` to link only the selected skills into the tool's verified skills directory. Preserve existing directories and other skills; do not replace an entire native directory with a hub link. Hosted runtimes need their supported package or project delivery instead of local symlinks.
6. **Verify in the intended runtime.** Resolve the links, confirm discovery from the relevant project, and try a representative invocation. Retire an obsolete route only after its replacement works and other tools' dependencies are checked. Report exactly what was verified; if you cannot inspect or invoke the target runtime, report that remaining check to the user.

## Commands

Run from this repository's root. Replace the example path with the source repository you want to use:

```bash
python3 skills/skill-linker/skill-linker.py --dry-run /absolute/path/to/project all
python3 skills/skill-linker/skill-linker.py /absolute/path/to/project all
```

For a repository under `install_dir`, use its relative path and selected names:

```bash
python3 skills/skill-linker/skill-linker.py your-username/your-project first-skill second-skill
```

Omit names to select interactively. For a repository with a root `SKILL.md`, the selectable name is the repository folder's name; `all` also selects it.

When the target tool needs its own skills directory, preview that destination first:

```bash
python3 skills/skill-linker/skill-linker.py --dry-run --target-dir ~/.claude/skills /absolute/path/to/project all
```

Use `--force` only after comparing the old and new targets for a deliberate override. For customization of a team or vendor skill, follow `skill-override-safeguard` before changing its source or delivery path.
