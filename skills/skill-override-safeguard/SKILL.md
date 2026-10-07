---
name: skill-override-safeguard
description: >
  Protect team and vendor skills from local drift. Use before modifying a
  shared skill or repointing its local symlink to a personal override.
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

1. **Identify ownership.** Check the Git remote and local checkout before changing a team or vendor skill. A path alone is a useful clue, but it does not prove who owns the repository. If the checkout is your own personal repository, edit it normally.

2. **Copy the whole skill folder** into a personal repository under `~/AI Assets/<your-git-username>/<repo-name>/skills/<skill-name>/`. Include scripts, references, and assets. Keep the original team or vendor checkout untouched. Use a distinct personal repository folder if the name would collide with an existing checkout.

3. **Edit and verify the personal copy.** Confirm its `SKILL.md` and supporting files work together. Record where the copy came from and how you will review upstream changes.

4. **Re-point only the intended local delivery path.** Show the existing link and proposed target first. If the user wants this override active in the configured skills hub, use the bundled skill linker with `--force` and the personal repository path. `--force` replaces an existing symlink without a prompt; it never replaces real files or directories. Check other tool roots separately, because a change to `~/.agents/skills` does not guarantee a change in every tool or runtime.

5. **Verify discovery.** Resolve the new link, confirm it contains the edited `SKILL.md`, and test the intended tool. Keep same-name copies deliberate and documented; project, user, and platform scopes may have different precedence.

## What this does NOT guarantee

This is a **defense-in-depth** convention, not a hard technical enforcement
mechanism. There is no OS-level permission lock or file-system enforcement — it
relies entirely on an agent reading and following this file before editing a
team/vendor skill. It does not replace periodically running `git status` inside
each `~/AI Assets/<org>/<repo-name>` entry to catch drift that slipped through anyway.
