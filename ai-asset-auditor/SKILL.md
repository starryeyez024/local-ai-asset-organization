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
root") that holds the real files for every AI-related asset, named
`@org--repo-name` from each repo's actual git remote, one flat entry per
repo — no org sub-folders, no per-skill splitting. Every tool-facing directory
then becomes a pure symlink view into that root. Moving or renaming an asset
afterward only ever means updating where a symlink points, never touching file
contents.

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
- `~/.agents/skills`
- Any project-local `.claude/skills` or `.agents/skills` under the user's
  usual working directories (ask where their projects generally live if not
  obvious — e.g. a `~/Sites`, `~/Code`, `~/dev`, or `~/Projects` equivalent)
- Any existing "AI assets" style root the user has already started (a folder
  whose entries are named `@org--repo-name`)

For each `SKILL.md` found, note its containing folder path. If a discovery
location does not exist on this machine, skip it silently — do not treat a
missing conventional path as an error, just fewer candidates.

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
2. Extract the **org/owner** from the remote URL's path component immediately
   before the final segment, and the **repo name** from the final path
   segment (strip `.git` if present).
3. Propose the flat entry name as `@<org>--<repo-name>`.
4. **Explicitly compare this derived name against the local folder name.** If
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

- **No `.git` at all.** Ask the user how they want it named and grouped —
  offer a personal-namespace fallback (e.g. `@<username>--<folder-name>`) as
  a suggestion, but let the user confirm or override it. Never invent an org
  prefix for an asset that has no remote to derive one from.
- **Repo with a remote but uncommitted changes.** Run `git -C <path> status
  --porcelain` for every real git repo before proposing it move. If it's
  non-empty, flag the repo and its specific dirty files, and ask the user how
  they want to handle it (commit first, stash, move it dirty and note the
  risk, copy just the edits into an override location, etc.) before it goes
  into any move plan. **Never silently discard, stash, or commit changes on
  the user's behalf** — surface the exact list of modified files and wait for
  a decision.
- **Name collision.** If two different discovered entries would resolve to
  the same proposed flat entry name (same org + repo name, or two different
  skills that would land on the same tool-facing symlink name), flag the
  collision with both source paths and ask the user how to disambiguate.
  Never auto-resolve a collision by silently overwriting one with the other
  or picking one arbitrarily.
- **Ambiguous MCP server type.** If it's unclear whether a configured server
  has a real local checkout or is purely remote/PATH-resolved, ask rather
  than guessing which of the two treatments (folder entry vs. lone doc file)
  applies.

---

## Phase 2 — Present the plan, ask, wait for confirmation

**Nothing in Phase 1 authorizes any action in Phase 3.** Phase 2 is the gate
between them.

### 2.1 Produce a written plan before asking anything else

Lay out, in plain language:

- The proposed physical root location (ask the user if they already have one
  in mind, e.g. `~/AI Assets`; do not assume a specific path without
  confirming it, especially on a machine you haven't audited before).
- For each real git repo found: current path → proposed flat entry name,
  with the remote-derived org/name shown explicitly next to the current
  folder name so any discrepancy from 1.4 is visible at a glance, not buried.
- For each plain non-git folder: the fallback name being proposed, clearly
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

### 2.2 Ask explicit clarifying questions

For every ambiguous or edge case surfaced in Phase 1, ask a direct question
rather than proceeding on an assumption — for example:

- "`<folder>` has no git remote — should I name it `@<fallback>` or would you
  prefer something else?"
- "`<repo>` has uncommitted changes to `<files>` — do you want to commit
  those first, or should I skip moving this one for now?"
- "`<repo-a>` and `<repo-b>` would both resolve to `@<org>--<name>` — how
  should I distinguish them?"
- "`<folder>`'s remote resolves to `@<derived-org>`, but its current
  container folder implies `<assumed-org>` — please confirm `@<derived-org>`
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
edit (not just a location change) and that skill lives outside
`~/AI Assets/overrides/` and is not one of the user's own personal
(`@<username>--*`) entries, stop and point the user (or the agent handling
that edit) at the `skill-override-safeguard` skill's copy → edit → re-point
procedure instead of improvising an edit here. This auditor moves and links
files; it does not decide, on its own initiative, to rewrite someone else's
skill content to make a migration tidier.

---

## Summary of the non-negotiables

- Phase 1 is read-only. No exceptions.
- Every proposed name for a git repo comes from `git remote -v`, not the
  folder name — and every mismatch between the two gets flagged, not silently
  resolved either way.
- No `.git` at all → ask, don't invent an org prefix.
- Uncommitted changes → flag and ask, never silently discard or move around.
- Name collisions → flag and ask, never auto-resolve.
- Phase 3 never runs on a plan that wasn't presented and explicitly
  confirmed first, and re-checks git state immediately before each move
  rather than trusting a stale audit.
- Content edits to vendor/team skills are out of scope for this skill —
  defer to `skill-override-safeguard`.
- When genuinely unsure, do less and ask, not more and apologize.
