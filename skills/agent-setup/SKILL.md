---
name: agent-setup
description: >
  Guide a person through personal AI setup from start to finish: build context through an interview, connect instructions and configuration, organize skills and scripts with the auditor and linker, and launch their local AI Asset Explorer. Use to start or resume onboarding, or complete one of these setup stages.
---

# Agent Setup

Be the user's guide throughout setup. Run the work in the current conversation;
read the specialist skills when their stage comes up instead of making the user
switch skills or repeat their context. Ask for preferences and decisions that
inspection cannot resolve; do the file, configuration, and command-line work.

## Start or resume

For full onboarding, explain the sequence briefly: discover the existing setup,
prepare personal configuration and context, organize selected assets, then open
the Explorer. Inspect first, then ask targeted questions about gaps in the findings.
A request for only one stage
does not authorize the rest. Skip completed stages after checking their state.

Keep a brief `setup-progress.md` in the private setup repository once its creation
is approved. Record each stage as pending, in progress, verified, deferred, or
blocked, with the actual config path, context files approved, selected tools,
audit decisions, Explorer directory and URL, and the next step. Keep sensitive
context out of this checklist. On resumption, read it and check the recorded
files before continuing. Save progress when the user pauses; do not restart the
interview or equate a deferred stage with a verified one.

A user can begin from a cloned or downloaded copy of this repository by asking
an assistant with local file access to read this file. No prior skill installation
is required. Resolve supporting files relative to this skill's directory. If the
checkout is incomplete, obtain the missing repository files before proceeding.

## Inspect and prepare

Read the user's existing instructions and configuration first. Check the requested
tools, their global instruction files, and any existing context location. Inspect
both `~/.config/agent-tools/agent-config.toml` and the older
`~/.config/ai-tools/ai-tools.toml` when present. Preserve unrelated configuration
keys, instruction content, symlinks, and existing Git history.

Follow the [configuration contract](../../docs/configuration-contract.md) when
reviewing settings and their consumers. Use complete dotted TOML keys in skills;
table headers supply their namespace. Match the user's existing schema rather
than inventing leaf prefixes or a second field table. Identify the config file a
consumer actually reads before treating similar names as conflicts. Keep native
application MCP, authentication, shell-policy, and trust settings in supported
native configuration files; the shared workflow TOML does not replace them.

Before choosing directory values or creating a configuration, read
[ai-asset-auditor](../ai-asset-auditor/SKILL.md) and perform its read-only discovery
phase for the relevant tools. Inspect configured paths, known native skill roots,
project-local skills in the user's working repositories, resolved symlink targets,
and installed-package records. Do not scan the entire disk or assume that every
installed tool is in active use. Skip absent conventional locations.

Summarize what was found and ask which detected tools the person uses, whether
there are custom skill or project locations to include, and which sources should
remain separate. Reuse answers already given. The user should not have to name
every directory or choose a layout before discovery. If a location is inaccessible,
record that gap rather than treating it as empty.

Use these findings to recommend `install_dir` and `symlinks_dir`. Preserve working
paths by default. A new user with no existing setup can use the example below;
it is not a reason to move an established setup. Show which maintained sources
will be represented by selected links in the Explorer's configured folder and
which managed packages stay outside that catalog. Discovery does not authorize
creating links, moving files, or cleaning up duplicates.

For standalone scripts, load the auditor's
[script procedure](../ai-asset-auditor/references/scripts.md). Inventory only
selected source roots and known caller locations. A new script-only user does
not need `install_dir`, `symlinks_dir`, or a skills hub: configure
`[script_catalog]` and its source bindings in the private TOML, then maintain
`script-catalog.toml` beside it. Keep bundled helpers inside their skill.
Use the helper at `../ai-asset-auditor/scripts/script-catalog.py` only when
that sibling package is actually present; if this setup skill is installed
alone, obtain the auditor package or use its documented procedure. Do not
claim that a standalone setup installation contains sibling files.

Use `~/.config/agent-tools/` for a new setup unless the user selects another path.
For an established setup, identify the scripts and tool settings that depend on
its current paths before proposing a migration. Creating the recommended config
changes which file this repository's linker and Explorer select by default.
Do not leave those consumers reading different settings accidentally.

Prepare the proposed files and changes for review in a temporary staging folder.
Show the destination, which files will change, and which tools will be connected.
Resolve competing instructions or context sources with the user. Apply the plan
once approved; existing approval of that concrete plan is sufficient. Retain
recoverable originals outside the tracked setup repo before editing existing files.

## Create or update the repository

Create the directory and initialize local Git if it is not already a repository.
Check for an enclosing repository before initializing; do not accidentally stage
the rest of the user's home or configuration directory. Local Git does not create
a private remote. Create or push a remote only when explicitly requested, and
verify its visibility is private before sending any content.

Use this layout:

```text
~/.config/agent-tools/
├── AGENTS.md
├── agent-config.toml
├── personal-context/
├── README.md
└── .gitignore
```

For a new setup, use this configuration. For an existing setup, preserve its
chosen asset and skills directories unless their migration is part of the plan.

```toml
[directories]
install_dir = "~/AI Assets"
symlinks_dir = "~/.agents/skills"
context_root = "~/.config/agent-tools/personal-context"

[instructions]
shared_file = "~/.config/agent-tools/AGENTS.md"
```

The linker and Explorer expand `~` for the directory values they consume. Expand
paths explicitly in other scripts or native tool configuration as needed.

Use the [personal context interview](references/personal-context.md) to help the
user build or review their context. Start small and let them defer optional topics.
Build `AGENTS.md` from the user's existing instructions and stated preferences.
Include the configuration path and when to consult individual context files.
Keep existing context in its established location if requested, updating
`context_root` accordingly. Only copy selected context into the repo when agreed;
do not invent personal information or import an entire notes vault. An empty
context folder is fine until the user has material to add.

Create the agreed asset root and skills folder if absent. Preserve any existing
contents or symlinks. Do not relocate repositories, managed packages, or skill
caches while creating the setup repo. Asset moves go through the audit stage below.

Write a short README identifying the active config, tool connections, verification
results, and how to restore the previous setup. Exclude `.env`, credentials, local
logs, generated catalogs, and backup files from Git. Inspect selected files before
staging; an ignore file does not remove secrets already in tracked content.

## Connect the selected tools

Use the [compatibility guide](../../pages/tool-compatibility.html) and confirm the
installed tool's supported instruction mechanism before editing it. Preserve
existing instructions and add or update a single reference to the shared file.
Resolve an existing symlink before writing so that its target is not overwritten
unintentionally. Repeating setup should not duplicate bootstrap instructions.

For a tool that reads a local instruction file, its bootstrap should tell the
agent to read the shared `AGENTS.md` and configuration using resolved paths.
Configure product-managed instructions through the supported interface when
available. If the interface is inaccessible, give the user only the specific
remaining action and prepared text. Hosted tools require selected context through
their own file or project mechanisms; a laptop path is not a connection.

For script-name lookup, add a short rule to the shared instructions: "When a
user or skill asks to run a registered script by name, use the resolver named
in the configured script catalog settings. Run the unique result with its
recorded interpreter, separate arguments, and working directory. Show
qualified candidates on ambiguity. Resolve an explicit skill-relative helper
from that skill's directory." Each selected desktop app also needs a native
bootstrap pointing to the shared instructions, the exact private config path,
and the absolute resolver path. The bootstrap must work before a script name
can be looked up. Preserve the app's existing instructions. Codex and ChatGPT
Work desktop have separate instruction connections; verify them separately.

## Verify the personal setup

Parse the written TOML and resolve all configured paths. Use the sibling
`skill-linker/asset_config.py` reader to confirm that the linker and Explorer will
select and read the intended config, without generating a catalog or adding skills.
For a custom location, record the required `--config` argument for both commands.
Inspect the resulting Git diff for unintended changes and sensitive content.

Check required keys in the actual scripts and resolved installed skill targets,
as well as examples and fixtures. When keys change, update these consumers
together. Use `directories.context_root` as the only personal-context folder
setting; migrate consumers of duplicate roots and remove the unused keys and
fallbacks in the same change. Distinguish
temporary shell bindings and output placeholders from TOML settings. Do not
claim runtime verification from a successful TOML parse alone.

Start a fresh session in each accessible target tool, from a representative
project, and ask it to identify the shared instruction and configuration files
and read a selected non-sensitive context file if one exists. Confirm the actual
paths against the configured values. File creation alone is not proof of runtime
discovery. Report inaccessible or failed runtime checks as pending in the handoff;
do not claim those tools are connected or retire their working old paths. Continue
independent stages when possible, carrying the pending check in the progress file.

For the desktop apps selected by the user, resolve and run a harmless registered
fixture by short name, qualified ID, and from a skill instruction, starting
outside its source checkout. Record OS, app version, entry point, result, and
evidence for Claude Code, Cursor, Codex, and ChatGPT Work separately. A Python
test or a file on disk does not prove an app read the instruction. Record an
unavailable interface as Not verified and continue independent setup work.

## Organize the assets

Continue [ai-asset-auditor](../ai-asset-auditor/SKILL.md) from the earlier discovery.
Carry forward the findings, paths, and user decisions; refresh findings affected
by setup changes instead of restarting the interview. Show the concrete asset
plan and apply approved changes under that skill's safeguards. The setup request alone does not approve
unknown moves or removals. If the user has no assets yet, record that result and
continue without installing a collection just to populate their catalog.

For selected skills that need delivery to a local tool, follow
[skill-linker](../skill-linker/SKILL.md), preview the links, and verify discovery
and a representative invocation. For content customization, follow
[skill-override-safeguard](../skill-override-safeguard/SKILL.md). Read these skills
as needed; the user remains in this conversation. Respect their confirmation
requirements and reuse approvals already covering the exact action.

## Set up the Explorer and finish

Follow [Explorer setup](references/explorer.md) to prepare the local catalog,
start its server, open it, and demonstrate a useful search. Offer this stage after
the audit; the user can also request it directly. Refresh it after approved asset
changes. Record that this catalog covers the configured folder and that managed
packages can remain outside it.

Finish with the setup location, tools verified, and any remaining user decision or
interface action, plus the Explorer URL and how to resume. Leave changes available
for review; commit or push
only when requested. Do not delete the old setup as an automatic final step.
