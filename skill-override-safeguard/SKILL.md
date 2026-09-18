---
name: skill-override-safeguard
description: >
  Standing safeguard for editing skills that live outside ~/AI Assets/overrides/.
  Use this BEFORE editing, modifying, or "fixing" any SKILL.md (or any file inside
  that skill's folder) that lives under ~/AI Assets/@*--*/ and is not already under
  ~/AI Assets/overrides/. Applies to any Cursor, Claude Code, or Codex agent working
  on this machine. Triggers on requests like "update this skill", "fix a bug in
  <skill>", "improve <skill>'s prompt", or any direct edit targeting a file inside a
  team/vendor-owned skill folder.
---

# Skill Override Safeguard

## Why this exists

`~/AI Assets/@org--repo-name/` entries are git clones of team- or vendor-owned repos
(e.g. `@org-a--project-name`, `@org-b--repo-name`,
`@org-c--skills`). Editing a skill file directly inside one of these entries
edits the team's shared clone in place — the exact mistake that causes uncommitted,
undocumented drift in a shared repo. It also risks a copy-based skill installer
treating the edited file as "installed content" and silently overwriting it back to
the upstream version on the next install.

## Trigger condition

**Before editing any file matching `~/AI Assets/@*--*/**/SKILL.md` (or any other file
inside that skill's folder) that is NOT already under `~/AI Assets/overrides/`, stop
and follow the procedure below instead of editing in place.**

The one exception: `~/AI Assets/@<your-username>--*` entries are the user's own personal repos
(not team/vendor-owned) — edits there are fine to make directly and commit normally.
The safeguard applies to every other org prefix — anything that isn't your own
personal namespace.

## Procedure

1. **Copy the whole skill folder** (not just `SKILL.md` — every file inside the skill
   directory: scripts, references, assets) to the equivalent path under:
   ```
   ~/AI Assets/overrides/@org--project-name/<internal-path-if-any>/<skill-name>/
   ```
   Example: overriding
   `~/AI Assets/@org-a--project-name/skills/example-skill/`
   means copying it to
   `~/AI Assets/overrides/@org-a--project-name/skills/example-skill/`.

2. **Make the requested edit in the copy**, never in the original. Leave the original
   team/vendor clone untouched and clean (`git status` should show nothing).

3. **Re-point the `~/.agents/skills/<name>` symlink** at the new override location
   instead of the original:
   ```bash
   rm ~/.agents/skills/<name>
   ln -s "~/AI Assets/overrides/@org--project-name/.../<skill-name>" ~/.agents/skills/<name>
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
each `~/AI Assets/@org--*` entry to catch drift that slipped through anyway.
