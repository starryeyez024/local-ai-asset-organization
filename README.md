# Local AI Asset Organization

A reference for keeping AI agent assets understandable across local tools and hosted runtimes. The [documentation site](pages/index.html) explains the setup model, physical organization, and tool compatibility. The [AI Assets Explorer guide](pages/skills-explorer-guide.html) explains the searchable catalog and local audit view.

Keep each asset in a clear source location. Deliver it through the path or package the consuming tool actually supports. A symlink can be a convenient local adapter; shared repositories and hosted agents may need committed files, generated copies, or native configuration.

## What is in this repository

| Location | Purpose |
| --- | --- |
| [`pages/`](pages/index.html) | Four guides and the overview page for the published documentation site. |
| [`skills-explorer/`](skills-explorer/README.md) | Searchable skill catalog and local audit view. |
| [`skills/skill-linker/`](skills/skill-linker/SKILL.md) | Agent instructions and a script for selectively linking skills from one project. |
| [`skills/ai-asset-auditor/`](skills/ai-asset-auditor/SKILL.md) | Read-first inventory and migration planning procedure. |
| [`skills/skill-override-safeguard/`](skills/skill-override-safeguard/SKILL.md) | Procedure for personal overrides of team or vendor skills. |
| [`scripts/lola-post-install-hub-bridge.sh`](scripts/lola-post-install-hub-bridge.sh) | Optional bridge for a specific Lola installer behavior; read its version notes before use. |

The [documentation maintenance plan](PAGES-RESTRUCTURING-PLAN.md) records the design rationale. For current setup instructions, use the guides and commands below.

## Local configuration

The skill linker reads `~/.config/ai-tools/ai-tools.toml`. Create it on your own machine with absolute paths:

```toml
[directories]
install_dir = "/absolute/path/to/asset-root"
symlinks_dir = "/absolute/path/to/.agents/skills"
```

`install_dir` contains real repositories. `symlinks_dir` is the local hub in which the linker creates one symlink per selected skill. The linker does not create this configuration file. TOML does not expand `~` on its own; use absolute paths for portable behavior across adapters. Keep personal paths and secrets out of this repository.

The broader setup model can also use a canonical global `AGENTS.md`, a machine configuration file, and short tool-native instruction files. See the [agentic setup guide](pages/agentic-setup.html) for scope and path rules.

## Link selected skills

From this repository's root:

```bash
python3 skills/skill-linker/skill-linker.py ktotten/local-ai-asset-organization ai-asset-auditor skill-override-safeguard
```

The first argument is a project path relative to `install_dir`. The script looks for `skills/*/SKILL.md`, or `*/SKILL.md` when no organized skills are found. Omit skill names to choose interactively, or pass `all` to select every discovered skill. It may automatically choose a close name match, so review its output before relying on a newly linked skill.
The linker script requires Python 3.11 or newer.

Existing symlinks pointing elsewhere are left alone unless you pass `--force`. Real files and directories are always left alone. `--force` replaces a symlink without an interactive confirmation. The script does not install a `skill-linker` shell command; use the Python command above or invoke the agent skill through a runtime that has discovered it.

Before changing a shared skill, read the [override safeguard](skills/skill-override-safeguard/SKILL.md). The [auditor](skills/ai-asset-auditor/SKILL.md) is intended for a broader inventory and an explicit migration plan.

## Explore the catalog

```bash
cd skills-explorer
make run
# open http://localhost:8790
```

`make run` regenerates the catalog from `~/.agents/skills` and starts the local preview server. Set `SKILLS_ROOT=/another/skills/directory` to scan a different directory. The checked-in `skills.json` contains shareable catalog data. Regeneration also writes an ignored `skills-local.json` with local paths for the **Audit Skills** view. That local file stays on the machine and must not be committed or published. See the [Explorer README](skills-explorer/README.md) for individual commands.

## Verify a tool-facing setup

1. Identify the real source folder and the tool and runtime that need it.
2. Check the [compatibility matrix](pages/tool-compatibility.html) for the supported path or delivery method.
3. Confirm a local link resolves and the tool actually discovers the asset. For shared or hosted use, verify the committed or packaged copy in that runtime.
4. Record any intentional copy and how it is refreshed from its source.
