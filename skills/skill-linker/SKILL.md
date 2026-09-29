---
name: skill-linker
description: >
  Help create selective symlinks from a newly-downloaded AI asset project (with multiple skills) into
  ~/.agents/skills directory. Instead of symlinking an entire project folder, this skill lets
  you choose 1, some, or all skills from that project and symlink just the ones you want.
  Manages the ~/.config/ai-tools.ai-tools.toml config file to remember your install and
  symlink directories across uses.
---

# Skill Linker

## Why this exists

When you download a new project containing many skills (50, 100, or more), you typically only
want to use a handful of them. Symlinking the entire project folder into `~/.agents/skills`
makes all skills available at once, which clutters your namespace and wastes tool-discovery
overhead. This skill solves that by:

1. Scanning a project for individual skills (looking for `skills/*/SKILL.md`)
2. Letting you select which ones to link
3. Creating symlinks only for the skills you choose, directly into `~/.agents/skills`
4. Storing your preferred directories in a config file so you don't have to type paths repeatedly

## One-time setup

The first time you run this skill, it will ask you for two directories:

- **Install directory** (default: `~/AI Tools`) — where you download new projects
- **Symlinks directory** (default: `~/.agents/skills`) — where symlinks should be created

These get saved to `~/.config/ai-tools.ai-tools.toml`. You only enter these once; later
runs reuse them. You can edit the config file by hand if your preferences change, or ask this
skill to re-configure them.

## How to use this skill

### Quick start: Direct skill names

If you know which skills you want, just name them directly:

```bash
skill-linker ktotten/local-ai-asset-organization ai-asset-auditor skill-override-safeguard
```

This creates symlinks for just those two skills. Done.

### Fuzzy matching

Typos are forgiven — the skill fuzzy-matches your input:

```bash
skill-linker project-x asset-audit   # Matches "ai-asset-auditor"
skill-linker project-x override-safe # Matches "skill-override-safeguard"
```

### Interactive mode (explore and choose)

If you run the skill without specifying skill names, it lists what's available and asks you to pick:

```bash
$ skill-linker ktotten/local-ai-asset-organization

📁 Project: ~/AI Tools/ktotten/local-ai-asset-organization
📚 Found 3 skill(s): ai-asset-auditor, skill-linker, skill-override-safeguard

Which skills do you want to link? (space-separated names, or 'all')
> ai-asset-auditor skill-override-safeguard

🔗 Linking 2 skill(s):
  ✓ ai-asset-auditor
  ✓ skill-override-safeguard

✅ Successfully linked 2/2 skill(s)
```

### Link all skills at once

```bash
skill-linker ktotten/local-ai-asset-organization all
```

Or in interactive mode, just type `all` when prompted.

### Replace existing symlinks

If you already have symlinks but want to update them to point to a different project:

```bash
skill-linker --force ktotten/local-ai-asset-organization skill-override-safeguard
```

The `--force` flag overwrites any existing symlinks without asking.

## What this skill does NOT do

- **Edit skills.** This skill only creates symlinks; it never modifies skill content.
- **Move or copy files.** Everything stays in your install directory; only symlinks are created.
- **Delete projects.** If you have leftover skills from an earlier run, this skill won't remove them.
- **Manage `~/.agents/skills` beyond symlinks.** Real (non-symlink) content already there is left alone.
- **Manage secrets or config values inside skills.** Each skill's own internal setup (MCP, etc.) is
  their responsibility, not this skill's.

## Warnings before you start

- **Symlink name collisions.** If two different projects have a skill with the same name
  (e.g. both have a `foo` skill), only one can be symlinked at a time under `~/.agents/skills/foo`.
  If this happens, the skill will ask which project's version you prefer, or suggest renaming
  one locally.
- **Project folder names vs. remote names.** The skill uses your project's local folder name
  (e.g. `project-a`) to create symlink targets, not the remote git name. If you've renamed
  a cloned project locally, those symlinks will use the local name you chose.
- **Uncommitted changes in projects.** The skill doesn't care whether a project has uncommitted
  git changes — it will symlink regardless. But if a skill's code changes later, the symlink
  will automatically reflect the new content (since it points to the live folder).

## Configuration file format

`~/.config/ai-tools.ai-tools.toml`:

```toml
[directories]
install_dir = "~/AI Tools"
symlinks_dir = "~/.agents/skills"
```

Both paths support `~/` expansion. You can edit this file by hand at any time.

## Common use cases

**Case 1: Link all skills from a new project**
```
User: "Link all skills from project-a"
Skill: Discovers 50 skills, asks for confirmation, creates 50 symlinks
```

**Case 2: Link just one skill**
```
User: "Link just the foo skill from project-a"
Skill: Scans project-a, finds 50 skills, asks which one you mean (or finds "foo"), 
       creates one symlink
```

**Case 3: Update symlink for a skill**
```
User: "I already symlinked foo from project-a, but now I want project-b's version instead"
Skill: Detects existing symlink at ~/.agents/skills/foo, asks to confirm the replacement,
       updates the symlink target to project-b's foo
```

## Edge cases this skill handles carefully

- **Nested skills in a project.** Some projects might have `skills/foo/skills/bar/SKILL.md`
  (a skill-within-a-skill). The skill will detect this and ask whether you want to symlink
  the parent (`foo`) or the nested child (`bar`), or both.
- **No `SKILL.md` in a folder named like a skill.** The skill verifies that a folder
  actually contains `SKILL.md` at the top level before treating it as a valid skill.
- **Symlink already exists but points elsewhere.** The skill detects this and asks whether
  to replace it, leave it alone, or report which project's version you're currently using.
- **Project folder doesn't exist.** If you type a project name that doesn't exist in your
  install directory, the skill tells you what it looked for and lists available projects
  instead of guessing.

---

## Summary: What you should know before starting

- This is a **safe, read-first, ask-often** skill. It discovers, presents a plan, waits for
  confirmation, and only then creates symlinks. It never overwrites without asking.
- **Symlinks are pointers.** They take up almost no disk space and automatically reflect
  changes in the real folder. If you update a skill in your project later, the symlink
  will see the new version immediately.
- **One symlink name = one active skill.** If two projects have a skill with the same name,
  you choose which one is reachable via `~/.agents/skills/<name>`.
- **Your install directory stays clean.** This skill creates symlinks only; it never moves
  or renames anything in your projects.
