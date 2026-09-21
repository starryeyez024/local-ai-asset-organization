---
name: skill-override-safeguard
description: >
   CRITICAL GUARDRAIL: Must be consulted before modifying, editing, patching, or updating
   ANY existing agent skill, vendor package, or team-shared asset on disk.
---

# Skill Override Safeguard

## Why this exists

`~/AI Assets/<org>/<repo-name>/` entries are git clones of team- or vendor-owned repos
(e.g. `org-a/project-name`, `org-b/repo-name`,
`org-c/skills`). For remotes with GitLab/GitHub subgroups, `<org>` may itself be
several folders deep (e.g. `dataverse/agentic-engineering/skills-hub`) — the
safeguard applies the same way regardless of nesting depth. Every org and repo
segment is lowercased in the local path (e.g. remote owner `RHEcosystemAppEng`
lives on disk as `rhecosystemappeng/`), so match against the lowercased path,
not the remote's original casing. Editing a skill file directly inside one of these entries
edits the team's shared clone in place — the exact mistake that causes uncommitted,
undocumented drift in a shared repo. It also risks a copy-based skill installer
treating the edited file as "installed content" and silently overwriting it back to
the upstream version on the next install.

## Trigger condition

**Before editing any file matching `~/AI Assets/**/SKILL.md` (i.e. any `SKILL.md`
found anywhere under the physical root — under an org folder, or, for multi-level
remotes with subgroups, under several nested org/subgroup folders before the repo
folder) — or any other file inside that skill's folder — that is NOT already under
your own username folder (`~/AI Assets/<your-git-username>/*`), stop and follow the
procedure below instead of editing in place.**

The one exception: `~/AI Assets/<your-git-username>/*` entries are the user's own personal repos
(not team/vendor-owned) — edits there are fine to make directly and commit normally.
The safeguard applies to every other org folder — anything that isn't your own
personal namespace.

## Procedure

1. **Copy the whole skill folder** (not just `SKILL.md` — every file inside the skill
   directory: scripts, references, assets) to a personal fork location under your
   own username namespace, treating it exactly like you forked the upstream repo
   yourself (even if no actual git fork/remote exists yet):
   ```
   ~/AI Assets/<your-git-username>/<repo-name>/
   ```
   There is no dedicated `overrides/` folder — the override lives as a personal
   fork, organized the same as any other personal repo under your username.
   Example: overriding
   `~/AI Assets/org-a/project-name/skills/example-skill/`
   means copying the `example-skill` folder to
   `~/AI Assets/<your-git-username>/example-skill/`.

2. **Make the requested edit in the copy**, never in the original. Leave the original
   team/vendor clone untouched and clean (`git status` should show nothing).

3. **Re-point the `~/.agents/skills/<name>` symlink** at the new override location
   instead of the original — the symlink name itself does NOT change, only its
   target:
   ```bash
   rm ~/.agents/skills/<name>
   ln -s "~/AI Assets/<your-git-username>/<repo-name>" ~/.agents/skills/<name>
   ```
   Only `~/.agents/skills/<name>` needs repointing — `~/.claude/skills` is a single
   symlink to `~/.agents/skills` and follows through automatically. Cursor and Codex
   CLI read `~/.agents/skills` natively, so no further action is needed for them.

4. **Never leave two active copies of the same skill name.** After repointing, the
   original team/vendor version is no longer reachable through
   `~/.agents/skills/<name>` — that's intentional. Do not create a second symlink
   elsewhere with the same skill name pointing at the original.

## What this does NOT guarantee

This is a **defense-in-depth** convention, not a hard technical enforcement
mechanism. There is no OS-level permission lock or file-system enforcement — it
relies entirely on an agent reading and following this file before editing a
team/vendor skill. It does not replace periodically running `git status` inside
each `~/AI Assets/<org>/<repo-name>` entry to catch drift that slipped through anyway.
