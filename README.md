# Local AI Asset Organization

A reference for keeping AI agent assets understandable across local tools and hosted runtimes. The [documentation site](pages/index.html) explains the setup model, physical organization, and tool compatibility. The [AI Assets Explorer guide](pages/skills-explorer-guide.html) explains the searchable catalog and local audit view.

Give each asset a clear owner and update path. Link selected skills from repositories you maintain; let marketplace installers manage their own caches and installed copies. Shared repositories and hosted agents may need committed files, generated copies, or native configuration.

## What is in this repository

| Location | Purpose |
| --- | --- |
| [`pages/`](pages/index.html) | Four guides and the overview page for the published documentation site. |
| [`skills-explorer/`](skills-explorer/README.md) | Searchable skill catalog and local audit view. |
| [`skills/skill-linker/`](skills/skill-linker/SKILL.md) | Agent instructions and a script for selectively linking skills from one project. |
| [`skills/ai-asset-auditor/`](skills/ai-asset-auditor/SKILL.md) | Read-first inventory and migration planning procedure. |
| [`skills/skill-override-safeguard/`](skills/skill-override-safeguard/SKILL.md) | Procedure for personal overrides of team or vendor skills. |
| [`scripts/lola-post-install-hub-bridge.sh`](scripts/lola-post-install-hub-bridge.sh) | Unsupported relocation experiment; excluded from the recommended setup because it can move unrelated skills. |

The [documentation maintenance plan](PAGES-RESTRUCTURING-PLAN.md) records the design rationale. For current setup instructions, use the guides and commands below.

## Local configuration

The skill linker reads `~/.config/ai-tools/ai-tools.toml`. Create it on your own machine with absolute paths:

```toml
[directories]
install_dir = "/absolute/path/to/asset-root"
symlinks_dir = "/absolute/path/to/.agents/skills"
```

`install_dir` contains real repositories. `symlinks_dir` is the local hub in which the linker creates one symlink per selected skill. The linker does not create this configuration file. TOML does not expand `~` on its own; use absolute paths for portable behavior across adapters. Keep personal paths and secrets out of this repository.

The [agentic setup guide](pages/agentic-setup.html) proposes a private repository at `~/.config/agent-tools/`. That migration is optional and not implemented by these tools. The linker still defaults to the configuration above; creating only the proposed `agent-config.toml` will not configure it. Preserve working paths until their consumers and native entry points are updated and tested.

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

The Explorer scans one directory, not plugin registries or every tool's skills roots. It does not establish which skills are enabled or running. Do not add links into managed plugin caches just to include them in the catalog.

## Verify a tool-facing setup

1. Inventory the relevant tool's skill roots and installed packages from the intended project. Record source, installer, version, scope, and existing delivery routes.
2. Choose the owner and updater: maintained repository, marketplace package, or project/team source. Check the [compatibility matrix](pages/tool-compatibility.html) for delivery options.
3. Verify discovery and a representative invocation in that runtime. Installed, enabled, discovered, and successfully invoked are separate checks.
4. Retire obsolete links or installations only after the replacement works and other tools' dependencies are accounted for. Keep required or intentional copies documented.

## Marketplace packages

Use the package manager's install, update, and removal controls. A plugin can also be loaded from a local repository, so its package format alone does not establish marketplace ownership. Keep customized versions as deliberate forks with a recorded upstream source; use tool-specific controls to select the intended version.

The Lola bridge is not part of this workflow. A temporary-fixture test showed that it relocates every immediate real directory in the chosen skills folder, including unrelated skills, under the supplied module name. Leave Lola's delivery files under Lola's control.
