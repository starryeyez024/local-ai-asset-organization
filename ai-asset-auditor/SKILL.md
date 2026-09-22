---
name: ai-asset-auditor
description: >
  Interactive auditing tool for organizing scattered AI assets (skills, MCP
  servers) onto a single flat physical root with symlink fan-out into every
  tool's own directory — the "one root, no duplicates" methodology. Use this
  BEFORE moving, renaming, deduplicating, or restructuring any skill folder or
  MCP server checkout, on ANY machine. Triggers on requests like "clean up my
  skills folders," "consolidate my AI assets," "find duplicate skills," "set up
  a flat AI asset root," or "audit my MCP servers." Runs discover-then-confirm:
  always presents a plan and asks clarifying questions before touching any
  file, and never executes a move, rename, delete, or symlink change without
  explicit per-plan user confirmation.
---

# AI Asset Auditor

## Why this exists

AI coding tools (Cursor, Claude Code, Codex CLI, and others) each ship their
own convention for "where skills live" and their own installer for MCP
servers. Once you use more than one of these tools, the same skill or server
ends up duplicated across tool-specific directories with no single
authoritative copy, symlinks that silently go dark when a target folder gets
renamed, macOS Finder alias files masquerading as symlinks that no CLI or
agent actually follows, and git repos whose local folder name has quietly
drifted from what their remote says they should be called.

The fix is architectural: pick exactly one folder on disk (the "physical
root") that holds the real files for every asset you personally curate and
version-control, organized as nested `<org>/<repo-name>/` folders derived from
each repo's actual git remote — one entry per repo, nested under its owning
org, no per-skill splitting. See "Physical Root & Identity" in the companion
`index.html` writeup for the reasoning. Your own tracked skills and
vendor-fork overrides get symlinked from that physical root into
`~/.agents/skills` — a canonical, cross-tool-recognized location that OpenAI
Codex CLI, Cursor, OpenCode, Google Gemini CLI, and GitHub Copilot all read
natively. That hub is not required to be pure symlinks, though: every one of
those tools discovers skills by resolving whatever sits at each entry, real
directory or symlink, with no restriction on mixing the two. Content a tool
writes directly into the hub (Cursor's own built-ins, Codex's own built-ins, a
third-party skills-CLI installer's output) legitimately coexists there as
real files — that's expected, not drift, and forcing it into a symlink risks
it being silently overwritten on the next tool sync anyway. Moving or
renaming one of your own tracked assets afterward only ever means updating
where its symlink points, never touching file contents.

This skill operationalizes that methodology as a **read-first, ask-often
audit**, not a script that reorganizes a filesystem on your behalf. It is
deliberately conservative: it would rather stop and ask a question than guess
wrong about a real user's files.

## Warning — read this before doing anything else

**This skill, once its plan is confirmed, changes real files on a real
filesystem.** Phase 3 moves directories, deletes symlinks and alias files, and
creates new symlinks. Before running Phase 3 for any given plan:

- Confirm with the user that anything not already committed to git has a
  backup, or get their explicit go-ahead to proceed anyway with full
  awareness of the risk.
- Prefer recommending the user commit or stash in-progress git changes over
  proceeding around them.
- When any part of a plan is ambiguous, default to the **least destructive**
  interpretation and ask rather than assume. It is always acceptable to do
  less than requested and ask a follow-up question; it is never acceptable to
  guess and delete, overwrite, or discard something silently.
- Never treat "the user asked for a full audit/cleanup" as blanket
  authorization for every destructive action a plan implies. Get sign-off on
  the specific plan actually presented, not on the general idea of cleaning up.

If you are an AI agent reading this file: follow the three phases below in
order. Do not skip ahead to Phase 3 actions while still inside Phase 1 or 2,
even if the user seems impatient or the fix looks obvious.

---

## Phase 1 — Discover (read-only, no writes)

Everything in this phase is inspection only: `ls`, `find`, `git remote -v`,
`git status`, reading config files. Nothing gets moved, renamed, created, or
deleted in this phase.

### 1.1 Find candidate skill locations

Skills are directories containing a `SKILL.md` file. Check the common
locations first, and ask the user for anything this list misses:

- `~/.claude/skills`
- `~/.cursor/skills-cursor`
- `~/.agents/skills` (the global hub)
- Any project-local `.claude/skills` or `.agents/skills` under the user's
  usual working directories (ask where their projects generally live if not
  obvious — e.g. a `~/Sites`, `~/Code`, `~/dev`, or `~/Projects` equivalent)
- Any existing "AI assets" style root the user has already started (a folder
  whose entries are nested `<org>/<repo-name>/` folders)

For each `SKILL.md` found, note its containing folder path. If a discovery
location does not exist on this machine, skip it silently — do not treat a
missing conventional path as an error, just fewer candidates.

**`~/.agents/skills` is not the only place skills legitimately live.** Most
tools that read the global hub (Codex, Cursor, OpenCode) also walk from a
project's working directory up to its repo root looking for a
project-local `.agents/skills`. This auditor's Phase 1 discovery above
already includes that project-local scan, but don't let anything downstream
in this skill implicitly treat the global hub as the single source of truth
when reasoning about a workspace. A `./.agents/skills/<name>/` folder found
inside a project falls under a separate two-rule convention (personal
projects symlink from `~/AI Assets` into the project root, the same as the
global hub; team-shared repos commit a real `SKILL.md` directly into the
project so it travels with the clone) — see "Workspace scope" in the
companion `index.html` writeup. Auditing or reconciling every project's own
`.agents/skills` folder against that convention is out of scope for this
skill; just don't audit a machine as if the global hub were the whole
picture.

### 1.2 Find candidate MCP server entries

MCP servers are configured, not discovered by directory scan — each tool's
config file has an explicit named block. Check the common config files, and
ask the user which files their tools actually use if none of these exist or
if the user mentions a different tool:

- `~/.claude/mcp.json`
- `~/.cursor/mcp.json`
- `~/.codex/config.toml`
- Any project-local MCP config the user points out

For each configured server, determine:

- Does its `command`/`args` point at a real local checkout (a path on disk
  with source code), or is it a remote `url`, or a globally-installed binary
  resolved from `PATH`? These need different treatment in Phase 2 (see the
  methodology's local-checkout vs. doc-only-server distinction).
- Is the same server configured redundantly across multiple config files? A
  server appearing in more than one file isn't itself a problem, but flag it
  so Phase 2 can ask whether the user wants those kept in sync.

### 1.3 Classify every discovered filesystem entry

For every skill folder and every local MCP checkout found in 1.1–1.2,
classify it into exactly one of these categories before proposing anything:

| Category | How to detect | What it means for Phase 2 |
|---|---|---|
| **Real git repo** | `git -C <path> remote -v` succeeds and returns at least one remote | Name the proposed entry from the remote (see 1.4), not the folder name |
| **Plain folder, no git** | `git -C <path> remote -v` fails with "not a git repository" | No remote to derive identity from — ask the user how they want it named/grouped, do not invent an org prefix |
| **Finder alias file (macOS)** | Looks like a file/folder in a listing but is actually a Finder alias, not a real symlink or directory — check with `file <path>` (aliases report as data/alias, not as a symlink) or note that `readlink` returns nothing for it | Flag as dead weight — no CLI/agent runtime follows a Finder alias. Propose deletion, but only after user confirmation; never delete without asking, even though these are near-certainly junk |
| **Dangling symlink** | `readlink` succeeds but the target path does not exist (check with `test -e` on the resolved target, or `find -L <parent> -xtype l`) | Flag explicitly. Ask the user whether the target moved (and should be repointed) or the asset is genuinely gone (and the dangling link should be removed) |
| **Real symlink, valid target** | `readlink` succeeds and the target exists | Note what it currently points at — this may already reflect a prior migration; don't propose redundant moves for something already correctly symlinked into a physical root |

Do not guess a category from the name or extension alone — actually run the
check for every entry. A folder that looks like a git repo because it has a
`.gitignore` may still fail `git remote -v` if it has no `.git` directory or
no remote configured; treat that as "plain folder, no remote," not as an
error to paper over.

### 1.4 Derive proposed naming from git remotes, never from folder names

**This is the single most error-prone step — treat local folder names as
hints, never as ground truth.** For every entry classified as a real git
repo:

1. Run `git -C <path> remote -v` and parse the remote URL (the `origin`
   remote if present, otherwise ask the user which remote to treat as
   canonical if there are several).
2. Extract the **full org/owner path** from the remote URL — everything
   between the host and the final segment — and the **repo name** from the
   final path segment (strip `.git` if present). GitLab and GitHub subgroups
   mean this path can be more than one level deep; preserve every level as
   its own nested folder, never collapse down to just the top-level group.
   For example, `git@gitlab.example.com:dataverse/agentic-engineering/skills-hub.git`
   resolves to the three-level entry `dataverse/agentic-engineering/skills-hub/`,
   not the collapsed `dataverse/skills-hub/`.
3. Lowercase every segment of that org/owner path, and the repo name, before
   proposing the folder — regardless of how the remote actually capitalizes
   it. Use hyphens to separate words if needed, never underscores or
   camelCase. For example, remote owner `RHEcosystemAppEng` becomes the local
   folder `rhecosystemappeng/`, not `RHEcosystemAppEng/`.
4. Propose the nested entry path as `<org>/<repo-name>/` (an org folder
   containing a repo folder — or, for multi-level remotes, `<org>/<subgroup>/<repo-name>/`).
   This is the convention for every entry, new or existing.
5. **Explicitly compare this derived name against the local folder name.** If
   they differ in any way — different org, different repo name, different
   casing, a container folder implying a different owner than the remote
   actually resolves to — flag it as a named discrepancy in the Phase 2 plan
   and call out specifically what differs. Do not silently prefer either one.

This check exists because it is a real, recurring source of naming errors:
local container folders get named for whoever happened to clone something
into them, or for a team someone assumed owned a repo, and that assumption
regularly turns out to be wrong once the actual remote is inspected. A repo
sitting inside a folder that implies one owner can resolve to a completely
different org on `git remote -v` — always check, never infer from the path
the repo happens to currently live at.

### 1.5 Flag edge cases explicitly — never guess past these

Do not resolve any of the following silently. Collect them for Phase 2 and
present each one as an explicit question:

- **No `.git` at all (or a git repo with no remote configured).** Nest it under
  the user's own OS username as the namespace folder (e.g.
  `<username>/<folder-name>/`), the same as any other personal repo — never a
  generic `personal/<folder-name>/` folder, since that name doesn't correspond
  to anything on the remote side. Confirm the exact username and folder name
  with the user rather than assuming, but the username-as-namespace convention
  itself is settled; don't offer `personal/` as an alternative.
- **Repo with a remote but uncommitted changes.** Run `git -C <path> status
  --porcelain` for every real git repo before proposing it move. If it's
  non-empty, flag the repo and its specific dirty files, and ask the user how
  they want to handle it (commit first, stash, move it dirty and note the
  risk, copy just the edits into an override location, etc.) before it goes
  into any move plan. **Never silently discard, stash, or commit changes on
  the user's behalf** — surface the exact list of modified files and wait for
  a decision.
- **Name collision.** If two different discovered entries would resolve to
  the same proposed nested entry path (same org + repo name, or two different
  skills that would land on the same tool-facing symlink name), flag the
  collision with both source paths and ask the user how to disambiguate.
  Never auto-resolve a collision by silently overwriting one with the other
  or picking one arbitrarily.
- **Ambiguous MCP server type.** If it's unclear whether a configured server
  has a real local checkout or is purely remote/PATH-resolved, ask rather
  than guessing which of the two treatments (folder entry vs. lone doc file)
  applies.

### 1.6 Check for nested `SKILL.md` files before proposing any symlink target

For every folder being considered as a symlink target into
`~/.agents/skills` — whether it's a brand-new skill source being onboarded or
an existing entry being re-audited — count how many files named `SKILL.md`
exist anywhere inside it, at any depth. Something conceptually equivalent to:

```
find <target> -name SKILL.md | wc -l
```

The expected count is **exactly 1**, and that one `SKILL.md` must sit at the
top level of the folder itself. Any count other than 1, or a match found at
a deeper nesting level than the top, is a problem to flag — not something to
silently accept or silently fix by picking one.

**Why this check exists:** OpenAI's Codex CLI recursively walks skill
directories and registers *any* file named `SKILL.md` it finds at any depth —
it does not enforce a boundary of "one skill = one top-level folder" (this is
a confirmed open bug:
[openai/codex#22275](https://github.com/openai/codex/issues/22275)). If a
folder being symlinked into `~/.agents/skills` contains other, nested skill
folders inside it, and those nested skills are *also* separately symlinked as
their own top-level entries in `~/.agents/skills`, Codex will double-register
those nested skills — once via the parent's symlink, once via their own.
This was discovered concretely in a real vendor repo (`dataverse/skills-hub`),
where several top-level skill folders turned out to contain nested sub-skill
folders of their own.

If a nested `SKILL.md` is found:

- Flag it clearly to the user as part of Phase 2's plan, **before** proposing
  or creating the symlink for that folder — do not let it pass through as if
  the folder were a clean single-skill entry.
- Recommend one of two fixes, and let the user pick:
  1. Don't symlink the parent folder at all. Instead, symlink each nested
     skill folder individually into `~/.agents/skills`, treating each nested
     `SKILL.md`'s containing folder as its own top-level skill entry.
  2. Ask the upstream repo maintainer to flatten their structure — file an
     issue against the source repo, the same way this was already handled
     for `dataverse/skills-hub`.
- Consistent with this skill's human-in-the-loop pattern, **do not block or
  refuse to proceed automatically** on finding a nested `SKILL.md`. Surface
  the finding clearly as part of the Phase 2 plan and let the user decide how
  to handle it — this is a flag-and-ask case, not a stop-the-audit case.

### 1.7 Real (non-symlink) entries directly inside `~/.agents/skills` are not automatically a problem

Not every entry inside `~/.agents/skills` needs to be a symlink. Every tool that reads this
hub (Codex CLI, Cursor, OpenCode, Gemini CLI, GitHub Copilot) resolves whatever sits at each
entry — a real directory or a symlink — with no restriction on mixing the two. Before flagging
a real (non-symlink) folder or file found directly in `~/.agents/skills`, check which of two
cases actually applies — do not assume it's a violation just because it isn't a symlink:

- **Tracked elsewhere with identical content.** Search `~/AI Assets` (e.g. `find ~/AI\ Assets
  -iname SKILL.md`, or compare directory contents/hashes against the candidate) to see if this
  same skill already exists as a git-tracked repo or personal skill folder under the physical
  root. If it does, and the content matches, this one IS still worth flagging in the Phase 2
  plan — recommend converting it to a symlink, same as any other tracked asset, for consistency
  and version control.
- **Not tracked anywhere, plausibly tool-written.** If no matching content exists anywhere
  under `~/AI Assets`, this is very likely something a tool's own sync/install mechanism wrote
  directly into the hub (a built-in skill, an installer's copy-based output). **Leave it
  alone.** This is not a violation, not drift, and not something to propose deleting, moving,
  or converting to a symlink. Record it in the Phase 1 findings as "tool-managed, no action
  needed" rather than omitting it or silently treating it as a defect.

---

## Phase 2 — Present the plan, ask, wait for confirmation

**Nothing in Phase 1 authorizes any action in Phase 3.** Phase 2 is the gate
between them.

### 2.1 Produce a written plan before asking anything else

Lay out, in plain language:

- The proposed physical root location (ask the user if they already have one
  in mind, e.g. `~/AI Assets`; do not assume a specific path without
  confirming it, especially on a machine you haven't audited before).
- For each real git repo found: current path → proposed nested `<org>/<repo-name>/`
  entry path, with the remote-derived org/name shown explicitly next to the current
  folder name so any discrepancy from 1.4 is visible at a glance, not buried.
- For each plain non-git folder: the fallback path being proposed, clearly
  marked as "no remote — needs your input" rather than presented as settled.
- For each MCP server: whether it's proposed as a folder entry (real local
  checkout) or a lone symlinked doc file (remote/PATH-resolved), and what
  stable-indirection symlink (if any) config files would be updated to
  reference.
- Every symlink that would be created or repointed, and its target.
- Every Finder alias file and dangling symlink proposed for removal, listed
  individually — not just "N stray files will be cleaned up."
- Anything flagged in 1.5 (edge cases), listed as open questions, not as
  already-decided plan items.
- Any nested `SKILL.md` found under 1.6, listed by path with both remediation
  options spelled out, for any folder proposed as a symlink target.
- Any real (non-symlink) entry found directly in `~/.agents/skills` under 1.7 — labeled either
  "tracked elsewhere, recommend symlinking" (with the matching physical-root path shown) or
  "tool-managed, no action needed."

### 2.2 Ask explicit clarifying questions

For every ambiguous or edge case surfaced in Phase 1, ask a direct question
rather than proceeding on an assumption — for example:

- "`<folder>` has no git remote — should I place it under `<fallback>/` or would you
  prefer something else?"
- "`<repo>` has uncommitted changes to `<files>` — do you want to commit
  those first, or should I skip moving this one for now?"
- "`<repo-a>` and `<repo-b>` would both resolve to `<org>/<name>` — how
  should I distinguish them?"
- "`<folder>`'s remote resolves to `<derived-org>/<repo-name>`, but its current
  container folder implies `<assumed-org>` — please confirm `<derived-org>/<repo-name>`
  is correct before I use it."

Batch these into one clear round of questions where possible rather than
trickling them out one at a time, but don't force a single mega-question if
the answers are genuinely independent.

### 2.3 Get explicit go-ahead on the specific plan presented

Do not proceed to Phase 3 until the user has confirmed the plan as written
(after any revisions from their answers to 2.2). A general "yes, clean things
up" given before the plan existed does not count as confirmation of this
plan. If the user changes their mind about part of the plan, re-confirm the
updated plan before executing any part of it — don't execute the
unchanged parts on the strength of an earlier, now-superseded confirmation.

Before executing, ask the user: "Want a quick backup first? I can tar/zip the current state of `~/.agents/skills` and the affected `~/AI Assets` folders before making changes." Proceed only after their answer.

---

## Phase 3 — Execute only what was confirmed

Only actions that were explicitly part of the confirmed plan happen here. If
executing the plan reveals something new (a repo that turns out to have
uncommitted changes that weren't visible during the audit, for instance),
stop and go back to Phase 2 for that item rather than pushing through.

### 3.1 Re-check state immediately before each move

Time has passed since Phase 1's audit — the user may have committed,
edited, or moved something in the meantime. For every git repo about to be
moved, re-run `git -C <path> remote -v` and `git -C <path> status
--porcelain` immediately before moving it. If either result has changed since
the audit (different remote, newly dirty, no longer dirty), stop and
surface the change to the user before proceeding with that specific item —
don't silently trust the Phase 1 snapshot.

### 3.2 Move whole repos with `mv`, never with a copy-and-delete

For a confirmed repo move, use a plain `mv <source> <destination>` (or the
`git mv`-equivalent directory move) for the whole repo directory. This is
safe for git: `mv` doesn't touch `.git/config`'s remote URL, doesn't affect
`git pull`/`git push`, and doesn't affect anyone else's separate clone of the
same remote — only the local checkout's path changes. Do not copy the repo
and then delete the original as a substitute for `mv`; that's slower, isn't
atomic, and needlessly risks leaving two partial copies if interrupted.

### 3.3 Never `rm -rf` real user data without explicit confirmation

Deleting a Finder alias or a confirmed-dangling symlink is low-risk (they
contain no real data), but still name the specific file being removed when
doing so. For anything that could contain real user data — an entire folder,
a git repo with any uncommitted content, anything the audit didn't already
classify as strictly disposable — require an explicit, specific confirmation
naming that exact path before removing it. A general earlier "yes, clean up
the stray files" does not extend to a different, larger deletion encountered
mid-execution; go back and ask again for anything outside what was
specifically itemized in the confirmed plan.

### 3.4 Rebuild symlinks so tool-facing directories become pure views

After a repo or asset lands in its new physical-root location:

- Create or repoint the tool-facing symlink(s) for it (e.g.
  `~/.agents/skills/<name>` → the asset's new physical-root path, or a
  single collapsed symlink like `~/.claude/skills` → `~/.agents/skills`)
  exactly as specified in the confirmed plan.
- Remove the old symlink or real directory it's replacing so there is never
  more than one active copy under the same tool-facing name.
- Verify the new symlink actually resolves (`test -e` on the symlink path,
  or `readlink -f`) before considering that item done — a symlink pointing
  at a path with a typo is worse than no symlink, because it fails silently
  until a tool tries to use it.
- For MCP servers with a real local checkout, prefer one extra layer of
  indirection — a stable symlink that config files reference — over pointing
  `command`/`args` directly at the physical-root path. Config files are
  read once and hardcoded, not re-scanned, so a future reorganization would
  otherwise require editing every config file by hand instead of updating
  one symlink target.
- After all symlinks in a batch are rebuilt, do a final sweep for dangling
  links introduced by the move itself (something that pointed at the old
  path and wasn't part of the plan to update) — report any found rather than
  leaving them.

### 3.5 Respect the override-safety boundary

This auditor skill's job is discovery, planning, and moving/symlinking
whole assets — it is **not** a substitute for the sibling
`skill-override-safeguard` skill, and it must not edit the contents of a
vendor- or team-owned skill in place as part of its own operation.

If, during any phase, you discover that a skill actually needs a content
edit (not just a location change) and that skill is not one of the user's own
personal (`<username>/*`) entries, stop and point the user (or the agent
handling that edit) at the `skill-override-safeguard` skill's copy → edit →
re-point procedure instead of improvising an edit here. This auditor moves
and links files; it does not decide, on its own initiative, to rewrite
someone else's skill content to make a migration tidier.

---

## Summary of the non-negotiables

- Phase 1 is read-only. No exceptions.
- Every proposed name for a git repo comes from `git remote -v`, not the
  folder name — and every mismatch between the two gets flagged, not silently
  resolved either way.
- No `.git` at all → ask, don't invent an org folder.
- Uncommitted changes → flag and ask, never silently discard or move around.
- Name collisions → flag and ask, never auto-resolve.
- Every folder proposed as a `~/.agents/skills` symlink target gets checked
  for nested `SKILL.md` files (exactly 1 expected, at the top level) — flag
  and ask, never symlink a folder with nested skills silently.
- A real (non-symlink) entry sitting directly in `~/.agents/skills` is only flagged for
  conversion if it's also tracked with identical content somewhere under `~/AI Assets`.
  Otherwise it's presumed tool-managed and left alone — not a violation.
- Phase 3 never runs on a plan that wasn't presented and explicitly
  confirmed first, and re-checks git state immediately before each move
  rather than trusting a stale audit.
- Content edits to vendor/team skills are out of scope for this skill —
  defer to `skill-override-safeguard`.
- When genuinely unsure, do less and ask, not more and apologize.
