# AI Assets Explorer

A searchable catalog of valid `SKILL.md` entries found in a configured skills directory. **Browse Skills** shows names, descriptions, inferred tags, and source labels. **Audit Skills** is a local inventory of entries, broken links, name collisions, and file age. The Explorer does not install, invoke, or edit skills.

Both views cover only the configured directory. They do not query marketplace registries, scan every tool's roots, or establish runtime enablement. A missing plugin skill may be installed elsewhere. Keep installer-managed files in place; do not add cache links just to include them here. A complete runtime inventory requires separate package and discovery checks.

## Try the demo

Serve this repository over HTTP and open `skills-explorer/index.html`, or use the demo on the documentation site. The demo reads the bundled `sample-skills.json`: fictional entries with no source directories, scan timestamps, or local inventory. It needs no configuration or generator. Its About page explains how to set up a personal instance. Audit and file-reveal actions are available only in a personal catalog.

## Guided local setup

Ask your assistant to follow [agent-setup](../skills/agent-setup/SKILL.md). It prepares your catalog in `~/.local/share/ai-assets-explorer/`, starts the copied local server, and opens the browser. The [Explorer procedure](../skills/agent-setup/references/explorer.md) covers refreshes and resuming. Personal catalogs stay outside this repository and are not published during onboarding.

## Direct local setup

```bash
make run
# open http://localhost:8790
```

`make run` prepares or refreshes the app and catalogs in `~/.local/share/ai-assets-explorer/`, then starts the copied server bound to `127.0.0.1`. It uses your existing setup configuration; if none exists, start with agent-setup. You can run the steps separately:

```bash
make regen
make serve
PORT=8080 make serve
make regen CONFIG=/path/to/agent-config.toml
make run EXPLORER_DIR=/path/to/local/explorer
```

The generator reads `directories.symlinks_dir` from `~/.config/agent-tools/agent-config.toml`, shared with the linker. It also supports the existing `~/.config/ai-tools/ai-tools.toml` when the recommended file is absent. The preparation helper requires an existing configuration so it can use the agreed skills folder. The standalone generator falls back to `~/.agents/skills` when called without a configuration. Use `--config /path/to/config.toml` with the generator to select a configuration, or `SKILLS_ROOT` to override the scan folder. It accepts symlinks and real skill directories, resolves each valid `SKILL.md`, and assigns tags with fixed keyword rules. It writes two files:

- `skills.json` contains the Browse Skills catalog. Descriptions and source labels can include personal or workplace information; keep this generated file local.
- `skills-local.json` includes absolute paths and the local audit inventory. It is ignored by Git. Keep it local and do not publish it.

The page tries the local audit file first. If only `skills.json` is present, it shows Browse Skills and hides Audit Skills. If neither file is available, it loads `sample-skills.json` when present. Guided setup does not copy the sample into personal installations; a missing personal catalog still prompts the user to prepare it. The source-file action works only through the local preview server. Catalog data is a snapshot; run `make regen` after changing the source skills or generator rules.

Skill type is read only from `metadata.skill-type` in the `SKILL.md` frontmatter. `atomic` identifies a small, focused skill intended for reuse by other skills; `workflow` identifies a skill that coordinates a broader sequence of work. Skills with missing or unsupported values appear as **Unclassified**. Names, descriptions, and skill dependencies do not determine the type.

```yaml
metadata:
  skill-type: atomic
```

Requires Python 3.11+ and Make for the shortcuts above; the setup skill can run the Python helper directly without Make. No Python packages are required. Both generated catalogs are ignored by Git, and the generator defaults to the personal output directory. GitLab Pages publishes the guides, skills, and demo app. Its explicit file list includes only `index.html`, `about.html`, and `sample-skills.json` from this directory; generated personal catalogs are excluded.
