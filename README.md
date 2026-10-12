# Local AI Asset Organization

A reference for keeping AI agent assets understandable across local tools and hosted runtimes. The [documentation site](pages/index.html) explains the setup model, physical organization, and tool compatibility. The [AI Asset Explorer guide](pages/skills-explorer-guide.html) explains the searchable catalog and local audit view.

Give each asset a clear owner and update path. Link selected skills from repositories you maintain; let marketplace installers manage their own caches and installed copies. Keep scripts in their owning project or skill bundle and register selected standalone scripts by name in a private local catalog. Shared repositories and hosted agents may need committed files, generated copies, or native configuration.

## Start here

Open this checkout in an assistant with local file access and ask:

> Read `skills/agent-setup/SKILL.md` and guide me through setting up my AI tools. Help me build my personal context, organize my assets, and open my AI Asset Explorer. Check what already works and prepare changes for review before applying them.

The setup skill first inspects your configuration, known skill and script locations, and installed packages, then asks about tools or custom locations it could not establish. Those findings guide its setup recommendations. It conducts a short context interview, connects your tools, uses the auditor and linker for approved changes, and prepares a local Explorer. You stay in one conversation. Progress is recorded privately so you can say “continue my setup” later. The guides explain the stages; the commands below are available for direct use and maintenance.

## What is in this repository

| Location | Purpose |
| --- | --- |
| [`pages/`](pages/index.html) | Overview, guides, and a [quick reference](pages/quick-reference.html) for the published documentation site. |
| [`skills-explorer/`](skills-explorer/README.md) | Searchable skills and registered scripts, schedule associations, and local skill audit. |
| [`skills/agent-setup/`](skills/agent-setup/SKILL.md) | Guided onboarding: personal context interview, tool setup, asset audit and linking, and local Explorer launch. |
| [`skills/skill-linker/`](skills/skill-linker/SKILL.md) | Agent instructions and a script for selectively linking skills from one project. |
| [`skills/ai-asset-auditor/`](skills/ai-asset-auditor/SKILL.md) | Read-first inventory and migration planning procedure, with a standalone script catalog helper. |
| [`skills/skill-override-safeguard/`](skills/skill-override-safeguard/SKILL.md) | Procedure for personal overrides of team or vendor skills. |

## Local configuration

For assisted setup, ask your assistant to read [the agent setup skill](skills/agent-setup/SKILL.md) in this checkout and follow it for your tools. It prepares changes for review, applies the approved plan, and verifies the connections.

The linker and Explorer read `~/.config/agent-tools/agent-config.toml`. The recommended directory settings are:

```toml
[directories]
install_dir = "~/AI Assets"
symlinks_dir = "~/.agents/skills"
```

`install_dir` contains real repositories. `symlinks_dir` is the local hub in which the linker creates one symlink per selected skill. The setup skill creates this configuration; the linker and Explorer expand `~` to your home directory. Other scripts reading these settings must also expand it or use resolved absolute paths. Keep personal paths and secrets out of this repository.

The [agentic setup guide](pages/agentic-setup.html) explains how to keep this configuration with your private instructions and context. Existing installations using `~/.config/ai-tools/ai-tools.toml` continue to work when the new path is absent. Both commands accept `--config` to select a file explicitly. The Explorer also accepts `SKILLS_ROOT` to override its scan directory for one run.

## Find a script by name

Scripts remain in the repository that owns them. A helper private to a skill stays in that skill's `scripts/` folder. Register selected shared scripts in a private `script-catalog.toml`; bind each source ID to a checkout in `agent-config.toml`. The catalog is this project's convention, not a native cross-tool registry. A skills symlink hub is optional and is not a script discovery path. The AI Asset Explorer shows registered scripts beside skills and matches direct references in local launchd and cron job definitions.

The [script reference](skills/ai-asset-auditor/references/scripts.md) gives the schema, fictional macOS and Windows examples, and lookup rules. The setup skill adds a short instruction to each selected desktop app that points to the shared instructions, configuration, and resolver. Codex and ChatGPT Work desktop are connected and verified separately.

For direct use with Python 3.11+ and no extra package manager:

```text
python3 skills/ai-asset-auditor/scripts/script-catalog.py inventory --root example-tools=/path/to/checkout
python3 skills/ai-asset-auditor/scripts/script-catalog.py validate
python3 skills/ai-asset-auditor/scripts/script-catalog.py --json resolve example-tools/hello
```

On native Windows, use `py -3` in place of `python3` and a Windows path for the selected root. `inventory` works before a catalog exists. `resolve` returns the authoritative file, interpreter, separate arguments, working directory, and provenance without executing the target. Ambiguous names return qualified candidates. No catalog, command result, or private machine path belongs in this public repository.

The [script verification record](docs/script-verification.md) separates tested helper behavior from pending native Windows and desktop app checks.

## Link selected skills

From this repository's root:

```bash
python3 skills/skill-linker/skill-linker.py --dry-run /absolute/path/to/project all
python3 skills/skill-linker/skill-linker.py /absolute/path/to/project all
```

Replace the example path with the repository containing the skills you want. The source can be an absolute path to an existing checkout or a project path relative to `install_dir`. The script finds a root `SKILL.md`, `skills/*/SKILL.md`, or immediate `*/SKILL.md` folders. Supply exact names to select particular skills, omit names to choose interactively, or use `all`. Misspelled names produce suggestions without changing any links.

Python 3.11 or newer is required. `--dry-run` previews destinations and checks conflicts without writing files. Existing links to the same source are left in place; different targets require `--force`. Real files and directories are never replaced.

If a tool needs a native skills directory, use `--target-dir /absolute/path/to/tool/skills` after verifying that discovery path. The linker skill handles source selection, delivery, and runtime verification as one workflow. To get started before the skill is installed, ask your assistant to read `skills/skill-linker/SKILL.md` in this checkout and follow it for the project and tools you name.

Before changing a shared skill, read the [override safeguard](skills/skill-override-safeguard/SKILL.md). The [auditor](skills/ai-asset-auditor/SKILL.md) is intended for a broader inventory and an explicit migration plan.

## Explore the catalog

During onboarding, agent-setup runs its `scripts/prepare-explorer.py` helper and opens the generated viewer in `~/.local/share/ai-assets-explorer/`. The repository contains the application code; each user’s catalog is generated locally and stays outside Git. See the [Explorer setup procedure](skills/agent-setup/references/explorer.md).

To prepare and run a personal Explorer directly with an existing setup configuration:

```bash
cd skills-explorer
make run
# open http://localhost:8790
```

`make run` reads the skill directory and private script catalog from the same configuration, prepares the app and catalogs in `~/.local/share/ai-assets-explorer/`, and starts its local server. Use `CONFIG=/path/to/agent-config.toml` for another configuration or `EXPLORER_DIR=/path/to/local/explorer` for another output folder. All three generated JSON files stay local and are excluded from Git. GitLab Pages publishes the guides, skills, and an Explorer demo using only fictional sample data. See the [Explorer README](skills-explorer/README.md) for individual commands.

The Explorer scans one directory, not plugin registries or every tool's skills roots. It does not establish which skills are enabled or running. Do not add links into managed plugin caches just to include them in the catalog.

## Verify a tool-facing setup

1. Inventory the relevant tool's skill roots and installed packages from the intended project. Record source, installer, version, scope, and existing delivery routes.
2. Choose the owner and updater: maintained repository, marketplace package, or project/team source. Check the [compatibility matrix](pages/tool-compatibility.html) for delivery options.
3. Verify discovery and a representative invocation in that runtime. Installed, enabled, discovered, and successfully invoked are separate checks.
4. Retire obsolete links or installations only after the replacement works and other tools' dependencies are accounted for. Keep required or intentional copies documented.

## Marketplace packages

Use the package manager's install, update, and removal controls. A plugin can also be loaded from a local repository, so its package format alone does not establish marketplace ownership. Keep customized versions as deliberate forks with a recorded upstream source; use tool-specific controls to select the intended version.


## Check the setup workflow

Run `python3 -B -m unittest discover -s tests -v` from the repository root. The tests use temporary repositories, configurations, and skill folders; they do not change installed tools or user configuration.
