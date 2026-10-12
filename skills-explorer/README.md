# AI Asset Explorer

A searchable catalog of valid `SKILL.md` entries and registered scripts. **Browse Assets** filters asset type and has a separate **Automation** group with **Automated** and **Manual** checkboxes. Both are checked initially; uncheck one to narrow results to the other category. Automated means a direct cron or launchd job definition was found; Manual means none was found in the scanned locations. Script cards show the matched job details. **Audit Skills** is a local inventory of skill entries, broken links, name collisions, and file age. Browsing never installs, invokes, or edits an asset.

Skill browse and audit cover the configured skills directory; scripts come from the private `script_catalog.path` in the setup configuration. The Explorer does not query marketplace registries, scan every tool's roots, or establish runtime enablement. A missing plugin skill may be installed elsewhere. Keep installer-managed files in place; do not add cache links just to include them here.

## Try the demo

Serve this repository over HTTP and open `skills-explorer/index.html`, or use the demo on the documentation site. The demo reads fictional `sample-skills.json` and `sample-scripts.json` entries with no local source files. It needs no configuration or generator. Audit and file-reveal actions are available only in a personal catalog.

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

The Makefile runs the preparation helper; the generators classify assets. The skills generator reads `directories.symlinks_dir` from `~/.config/agent-tools/agent-config.toml`, shared with the linker. It also supports the existing `~/.config/ai-tools/ai-tools.toml` when the recommended file is absent. The preparation helper requires an existing configuration so it can use the agreed skills folder. The standalone skills generator falls back to `~/.agents/skills` when called without a configuration. Use `--config /path/to/config.toml` with the generator to select a configuration, or `SKILLS_ROOT` to override the scan folder. It accepts symlinks and real skill directories and resolves each valid `SKILL.md`. The script generator uses the shared fixed keyword rules for **Work Stage**, **Tool**, and **Task Type**. Script action hints add stage matches for transfers, previews, and reviews; ambiguous scripts use Produce, as skills do. **Skill Maturity**, Skill Type, Agile Phase, and Role apply only to skills. No LLM or external API is involved in tagging. Setup writes three local files:

- `skills.json` contains the Browse Skills catalog. Descriptions and source labels can include personal or workplace information; keep this generated file local.
- `skills-local.json` includes absolute paths and the local audit inventory. It is ignored by Git. Keep it local and do not publish it.
- `scripts-local.json` includes registered script paths and direct matches to local scheduled job definitions. It is ignored by Git. Keep it local and do not publish it.

The reusable `scan-scheduled-jobs.py` command scans the user's `~/Library/LaunchAgents`, system `/Library/LaunchAgents` and `/Library/LaunchDaemons`, the user crontab, and readable `/etc/crontab` and `/etc/cron.d` files. It prints JSON with directly referenced script files and schedules; it does not run jobs. Pass repeated `--launchd-dir` or `--cron-file` options to scan a different set. The Explorer generator uses the same scanner and matches those file paths to the private script catalog. A match means a job definition refers to the file; it does not prove the job is loaded or runs successfully. Shell functions, indirect calls, and Windows Task Scheduler jobs are outside this first scanner's coverage.

The page tries the local skill audit file first. If only `skills.json` is present, it shows skills and hides Audit Skills. If neither file is available, it loads the fictional samples when present. Guided setup does not copy the samples into personal installations. The source-file action works only through the local preview server. Catalog data is a snapshot; run `make regen` after changing source assets, catalog records, or job definitions.

Skill type is read only from `metadata.skill-type` in the `SKILL.md` frontmatter. `atomic` identifies a small, focused skill intended for reuse by other skills; `workflow` identifies a skill that coordinates a broader sequence of work. Skills with missing or unsupported values appear as **Unclassified**. Names, descriptions, and skill dependencies do not determine the type.

```yaml
metadata:
  skill-type: atomic
```

Requires Python 3.11+ and Make for the shortcuts above; the setup skill can run the Python helper directly without Make. No Python packages are required. All generated catalogs are ignored by Git, and the generator defaults to the personal output directory. GitLab Pages publishes the guides, skills, and demo app. Its explicit file list includes only `index.html`, `about.html`, `sample-skills.json`, and `sample-scripts.json` from this directory; generated personal catalogs are excluded.
