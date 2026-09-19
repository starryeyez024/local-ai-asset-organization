#!/usr/bin/env bash
#
# lola-post-install-hub-bridge.sh
#
# =============================================================================
# WHAT THIS SCRIPT IS
# =============================================================================
# A best-effort bridge between the `lola` CLI ("AI Skills Package Manager")
# and the "flat physical root + symlink hub" AI-asset organization pattern
# documented in this repo's `AI Asset Management Methodology.html`.
#
# `lola install` is a COPY-based installer: it writes a fresh, real copy of
# each skill's files straight into a tool's skill directory (e.g.
# `~/.claude/skills/<skill-name>/`). It has no config file/flag for
# redirecting that write to a different physical location and symlinking
# it back in. This script fills that gap by running immediately AFTER
# `lola install` has already copied the files, then:
#   1. moving each newly-copied, real (non-symlink) skill folder out of the
#      tool's skill directory and into the canonical physical root at
#      `~/AI Assets/@lola--<module-name>/<skill-name>/`, and
#   2. replacing the original location with a symlink back to that new
#      physical-root location.
#
# The net effect: `lola` can still be used normally to fetch/update skills,
# but the real files end up living in the same flat physical root as every
# other AI asset on this machine, instead of as an orphaned duplicate copy
# sitting inside `~/.claude/skills/`, `~/.cursor/skills/`, etc.
#
# =============================================================================
# WARNING — THIS IS A BEST-EFFORT BRIDGE, NOT AN OFFICIAL LOLA FEATURE
# =============================================================================
# Lola has no supported "move real files + symlink back" mode. Everything
# below is inferred by reading `lola install --help` and, where that fell
# short, the actual installed `lola` Python source on this machine
# (lola_ai 0.7.2.dev37, installed via `uv tool install`, source under
# ~/.local/share/uv/tools/lola-ai/lib/python3.13/site-packages/lola/). Lola
# is not maintained by the author of this repo. Its hook contract could
# change or disappear in a future release without notice. Re-verify against
# `lola install --help` and, ideally, the installed source before relying on
# this in a new environment.
#
# =============================================================================
# LOLA'S DOCUMENTED HOOK CONTRACT (from `lola install --help`, verbatim)
# =============================================================================
#   --pre-install PATH   Run script before installing (use instead of
#                         module's hook)
#   --post-install PATH  Run script after installing (use instead of
#                         module's hook)
#
# That is the ENTIRE documented contract. The `--help` output does NOT
# document what arguments or environment variables get passed to the hook
# script, what its working directory is, or how PATH is resolved. Everything
# in the next two sections is therefore an ASSUMPTION/GAP filled in by
# reading lola's source rather than its docs, and is called out explicitly
# per the instructions for this script rather than silently guessed.
#
# =============================================================================
# ASSUMPTION #1 (from source, not --help): environment variables passed in
# =============================================================================
# Reading `lola/targets/install.py` (`_run_install_hook`), as of
# lola_ai 0.7.2.dev37, a hook script is invoked as:
#     subprocess.run(["bash", <resolved_script_path>], cwd=<project_path>, env=<env>)
# where <env> is the parent process's environment PLUS these lola-specific
# variables:
#     LOLA_MODULE_PATH   - absolute path to the module's local copy
#                           (e.g. .lola/modules/<module-name>/...)
#     LOLA_PROJECT_PATH  - the --project-path lola was invoked with (or the
#                           resolved cwd for user-scope installs)
#     LOLA_ASSISTANT     - the assistant slug, e.g. "claude-code", "cursor"
#     LOLA_SCOPE         - "user" or "project"
#     LOLA_HOOK          - "pre-install" or "post-install"
# None of this is documented in `--help`. This script reads these variables
# when present (see "Mode 1" below) but does NOT hard-fail if they are
# absent, since a future lola release could rename or drop them silently.
#
# =============================================================================
# ASSUMPTION #2 / KNOWN GAP (from source): --post-install PATH resolution
# =============================================================================
# The same source shows `_run_install_hook` resolves the PATH you pass to
# --post-install RELATIVE TO THE MODULE'S OWN LOCAL COPY DIRECTORY
# (`.lola/modules/<module-name>/...`), then verifies the resolved path is
# still INSIDE that directory before running it. If the resolved path falls
# outside the module's local copy (e.g. you point --post-install at an
# absolute path to a script living in this repo, outside any lola module),
# lola raises "post-install script outside module directory" — and because
# post-install failures are only ever logged as a yellow warning (install
# still "succeeds"), the practical effect is that YOUR HOOK SCRIPT SILENTLY
# NEVER RUNS, with no non-zero exit code to notice.
#
# Two ways to work around that, given this script lives in a separate repo:
#   (a) Copy or symlink this script into the module's own
#       `.lola/modules/<module-name>/` tree before running `lola install`,
#       and pass a path relative to that module (e.g.
#       `--post-install scripts/lola-post-install-hub-bridge.sh` if you drop
#       a copy at `<module>/scripts/...`), OR
#   (b) Skip the --post-install flag entirely and just run this script
#       manually, right after `lola install` finishes, using Mode 2 below.
# Verify which of these actually works against your installed lola version
# before trusting the --post-install flag for anything unattended.
#
# =============================================================================
# TWO INVOCATION MODES SUPPORTED BY THIS SCRIPT
# =============================================================================
# Mode 1 - as a lola hook (LOLA_* env vars present):
#     lola install <module> -a <assistant> -s user \
#         --post-install /absolute/path/to/lola-post-install-hub-bridge.sh
#   (subject to the path-resolution gap above — confirm it actually fires)
#
# Mode 2 - manual / standalone, run by hand right after `lola install`:
#     ./lola-post-install-hub-bridge.sh --assistant claude-code --scope user \
#         --module-name my-module [--project-path /path/to/project]
#   or, most robust of all, skip assistant/scope guessing entirely and just
#   point directly at the skill directory lola wrote into:
#     ./lola-post-install-hub-bridge.sh --skills-dir ~/.claude/skills \
#         --module-name my-module
#
# =============================================================================
# PREREQUISITES
# =============================================================================
#   - bash (this script uses only POSIX-ish + bash builtins, no bashisms
#     beyond arrays/[[ ]], so it should run under the bash that ships on
#     both macOS and Linux without needing bash 4+ features)
#   - Standard coreutils: mv, ln, mkdir, basename, dirname (present on any
#     macOS or Linux box by default)
#   - `~/AI Assets/` should already exist as the physical root used by this
#     repo's methodology; this script will create the per-module container
#     folder under it (`@lola--<module-name>/`) but will NOT create
#     `~/AI Assets/` itself if it's missing, to avoid guessing at a root
#     the user hasn't actually set up
#
# =============================================================================
# SAFETY MODEL
# =============================================================================
#   - Only touches entries that are REAL directories (not symlinks) sitting
#     directly inside the resolved skills directory. Anything already a
#     symlink is logged and skipped, so re-running this script after it has
#     already run is a safe no-op (idempotent).
#   - Never overwrites an existing destination. If
#     `~/AI Assets/@lola--<module>/<skill-name>/` already exists (as a file,
#     directory, or symlink), that skill is logged as AMBIGUOUS and skipped
#     rather than guessing whether it's safe to replace.
#   - Supports `--dry-run` to preview every move/symlink this script would
#     perform without touching the filesystem. Use this first in any new
#     environment.
#   - This script was written and syntax-checked (`bash -n`) but was
#     deliberately NOT run against any real skill directory as part of
#     writing it — test it yourself with --dry-run before trusting it.
#
# =============================================================================

set -uo pipefail
# Note: deliberately NOT using `set -e` here. This script processes a list
# of skill folders in a loop, and one folder being ambiguous/unexpected
# should not abort processing of the rest. Every command whose failure
# matters is checked explicitly below instead.

# -----------------------------------------------------------------------
# Defaults / physical root location
# -----------------------------------------------------------------------
# The canonical flat physical root this whole methodology is built around.
PHYSICAL_ROOT="${PHYSICAL_ROOT:-$HOME/AI Assets}"

# These get filled in either from the LOLA_* env vars (Mode 1) or from
# explicit CLI flags (Mode 2). Left blank until resolved below.
ASSISTANT="${LOLA_ASSISTANT:-}"
SCOPE="${LOLA_SCOPE:-}"
PROJECT_PATH="${LOLA_PROJECT_PATH:-}"
MODULE_PATH="${LOLA_MODULE_PATH:-}"
MODULE_NAME=""
SKILLS_DIR_OVERRIDE=""
DRY_RUN=0

# -----------------------------------------------------------------------
# Logging helpers - every message is prefixed so it's obvious in lola's
# (or a terminal's) output which lines came from this bridge script.
# -----------------------------------------------------------------------
log_info()  { printf '[lola-hub-bridge] %s\n' "$1"; }
log_skip()  { printf '[lola-hub-bridge] SKIP: %s\n' "$1"; }
log_warn()  { printf '[lola-hub-bridge] WARNING: %s\n' "$1" >&2; }
log_error() { printf '[lola-hub-bridge] ERROR: %s\n' "$1" >&2; }

usage() {
  cat <<'EOF'
Usage:
  lola-post-install-hub-bridge.sh [options]

Options:
  --assistant NAME      Assistant slug (claude-code, cursor, copilot-cli,
                         opencode). Falls back to $LOLA_ASSISTANT.
  --scope user|project  Install scope. Falls back to $LOLA_SCOPE.
  --project-path PATH   Project root, only needed for scope=project.
                         Falls back to $LOLA_PROJECT_PATH.
  --module-name NAME    Name of the lola module that was just installed.
                         Falls back to the basename of $LOLA_MODULE_PATH.
  --skills-dir PATH     Skip assistant/scope auto-detection entirely and
                         operate directly on this directory. Recommended
                         when you already know exactly where lola wrote
                         the skill folders.
  --dry-run             Log every action this script WOULD take, but do
                         not move or symlink anything.
  -h, --help            Show this help text.

See the header comment block in this script for the full explanation of
what lola actually passes to hook scripts (and what is unverified).
EOF
}

# -----------------------------------------------------------------------
# Parse CLI flags (Mode 2). Any flag given here overrides an LOLA_* env
# var picked up from Mode 1, so this also works as a manual override even
# when lola *did* invoke this script as a hook.
# -----------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --assistant)
      ASSISTANT="$2"; shift 2 ;;
    --scope)
      SCOPE="$2"; shift 2 ;;
    --project-path)
      PROJECT_PATH="$2"; shift 2 ;;
    --module-name)
      MODULE_NAME="$2"; shift 2 ;;
    --skills-dir)
      SKILLS_DIR_OVERRIDE="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      log_error "Unrecognized argument: $1"
      usage
      exit 1 ;;
  esac
done

# -----------------------------------------------------------------------
# Resolve MODULE_NAME: prefer an explicit --module-name, otherwise derive
# it from LOLA_MODULE_PATH (basename of .lola/modules/<module-name>).
# This name becomes the "@lola--<module-name>" container folder under the
# physical root, so we refuse to guess if we truly have nothing to go on.
# -----------------------------------------------------------------------
if [[ -z "$MODULE_NAME" && -n "$MODULE_PATH" ]]; then
  MODULE_NAME="$(basename -- "$MODULE_PATH")"
fi

if [[ -z "$MODULE_NAME" ]]; then
  log_error "Could not determine the module name."
  log_error "Pass --module-name explicitly, or invoke this script as a lola"
  log_error "hook so \$LOLA_MODULE_PATH is set (see header comments)."
  exit 1
fi

# -----------------------------------------------------------------------
# Defensive check: if lola tells us (via LOLA_HOOK) that this is actually
# running as a PRE-install hook, bail out early rather than doing anything.
# Skill files don't exist yet during pre-install, so there would be
# nothing valid to move -- this guards against someone accidentally wiring
# this same script up to --pre-install by copy/paste.
# -----------------------------------------------------------------------
if [[ "${LOLA_HOOK:-}" == "pre-install" ]]; then
  log_warn "\$LOLA_HOOK=pre-install -- this bridge script only makes sense"
  log_warn "as a POST-install hook (files must exist before we can move"
  log_warn "them). Doing nothing and exiting cleanly."
  exit 0
fi

# -----------------------------------------------------------------------
# Resolve the skills directory to operate on.
#
# Priority order:
#   1. --skills-dir, if given: use it verbatim, no guessing at all.
#   2. Otherwise, reconstruct lola's own per-assistant/per-scope path
#      convention. This mirrors what's actually in lola's installed
#      source (lola/targets/{claude_code,cursor,copilot}.py) as of
#      lola_ai 0.7.2.dev37 -- NOT re-derived from --help, which says
#      nothing about directory layout. If lola changes these paths in a
#      future release, this mapping will silently go stale; --skills-dir
#      is the safer option for that reason.
# -----------------------------------------------------------------------
if [[ -n "$SKILLS_DIR_OVERRIDE" ]]; then
  SKILLS_DIR="$SKILLS_DIR_OVERRIDE"
else
  if [[ -z "$ASSISTANT" || -z "$SCOPE" ]]; then
    log_error "No --skills-dir given, and assistant/scope are unknown"
    log_error "(got ASSISTANT='$ASSISTANT' SCOPE='$SCOPE')."
    log_error "Pass --skills-dir directly, or provide --assistant/--scope"
    log_error "(or run this as a lola hook so LOLA_ASSISTANT/LOLA_SCOPE"
    log_error "are set)."
    exit 1
  fi

  # Base directory differs for user vs. project scope, same as lola itself.
  if [[ "$SCOPE" == "user" ]]; then
    SCOPE_BASE="$HOME"
  elif [[ "$SCOPE" == "project" ]]; then
    if [[ -z "$PROJECT_PATH" ]]; then
      log_error "scope=project requires --project-path (or \$LOLA_PROJECT_PATH)."
      exit 1
    fi
    SCOPE_BASE="$PROJECT_PATH"
  else
    log_error "Unrecognized scope '$SCOPE' (expected 'user' or 'project')."
    exit 1
  fi

  case "$ASSISTANT" in
    claude-code)
      SKILLS_DIR="$SCOPE_BASE/.claude/skills" ;;
    cursor)
      SKILLS_DIR="$SCOPE_BASE/.cursor/skills" ;;
    copilot-cli)
      # Copilot CLI's own source uses a different project-scope path than
      # the other assistants (.github/skills, not .copilot/skills) --
      # only the user-scope path matches the ~/.<tool>/skills pattern.
      if [[ "$SCOPE" == "user" ]]; then
        SKILLS_DIR="$HOME/.copilot/skills"
      else
        SKILLS_DIR="$SCOPE_BASE/.github/skills"
      fi ;;
    opencode)
      SKILLS_DIR="$SCOPE_BASE/.opencode/skills" ;;
    *)
      log_error "No known skills-directory mapping for assistant '$ASSISTANT'."
      log_error "Pass --skills-dir explicitly instead of relying on"
      log_error "auto-detection for this assistant."
      exit 1 ;;
  esac
fi

log_info "Module:       $MODULE_NAME"
log_info "Skills dir:   $SKILLS_DIR"
log_info "Physical root: $PHYSICAL_ROOT"
[[ "$DRY_RUN" -eq 1 ]] && log_info "DRY RUN -- no files will be moved or linked."

if [[ ! -d "$SKILLS_DIR" ]]; then
  log_warn "Skills directory does not exist: $SKILLS_DIR"
  log_warn "Nothing to do. (Did lola actually install anything here?)"
  exit 0
fi

if [[ ! -d "$PHYSICAL_ROOT" ]]; then
  log_error "Physical root does not exist: $PHYSICAL_ROOT"
  log_error "Refusing to create it automatically -- set it up first (see"
  log_error "this repo's AI Asset Management Methodology.html), or point"
  log_error "PHYSICAL_ROOT at the right place via env var."
  exit 1
fi

# The per-module container folder under the physical root, e.g.
# ~/AI Assets/@lola--my-module/
DEST_CONTAINER="$PHYSICAL_ROOT/@lola--$MODULE_NAME"

# -----------------------------------------------------------------------
# Main loop: walk every top-level entry in the skills directory.
# -----------------------------------------------------------------------
moved_count=0
skipped_count=0

# Use a glob rather than `find` so we only ever look at direct children,
# matching how lola writes one folder per skill directly under the
# skills directory (never nested deeper than that).
shopt -s nullglob
for entry in "$SKILLS_DIR"/*; do
  skill_name="$(basename -- "$entry")"

  # --- Case 1: not a directory at all (e.g. a stray file) -> skip, log ---
  if [[ ! -d "$entry" ]]; then
    log_skip "'$skill_name' is not a directory ($entry) -- leaving as-is."
    ((skipped_count++)) || true
    continue
  fi

  # --- Case 2: already a symlink -> this is the idempotent no-op case. ---
  # A previous run of this script (or a manual `ln -s`) already bridged
  # this skill into the physical root. Do nothing, just note it.
  if [[ -L "$entry" ]]; then
    log_skip "'$skill_name' is already a symlink -- already bridged, leaving as-is."
    ((skipped_count++)) || true
    continue
  fi

  # --- Case 3: a real directory. This is what we came here to bridge. ---
  dest_path="$DEST_CONTAINER/$skill_name"

  # Never overwrite something already at the destination. If it exists in
  # any form (real dir, file, or symlink), we cannot be sure whether it's
  # safe to replace it, so we log clearly and skip rather than guessing.
  if [[ -e "$dest_path" || -L "$dest_path" ]]; then
    log_warn "AMBIGUOUS: destination already exists, skipping '$skill_name'."
    log_warn "  Source:      $entry"
    log_warn "  Destination: $dest_path"
    log_warn "  Resolve this manually (compare the two, then remove the"
    log_warn "  stale one) before re-running this script for this skill."
    ((skipped_count++)) || true
    continue
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log_info "[dry-run] would move: $entry"
    log_info "[dry-run]        to: $dest_path"
    log_info "[dry-run] would symlink: $entry -> $dest_path"
    ((moved_count++)) || true
    continue
  fi

  # Create the per-module container folder the first time we need it.
  if ! mkdir -p -- "$DEST_CONTAINER"; then
    log_error "Failed to create destination container: $DEST_CONTAINER"
    log_error "Skipping '$skill_name'."
    ((skipped_count++)) || true
    continue
  fi

  # Step (a): move the real folder to the physical root.
  if ! mv -- "$entry" "$dest_path"; then
    log_error "Failed to move '$skill_name' to $dest_path -- leaving the"
    log_error "original in place untouched. Skipping the symlink step for"
    log_error "this skill."
    ((skipped_count++)) || true
    continue
  fi

  # Step (b): create a symlink at the original location pointing back at
  # the new physical-root location, so the tool (Claude Code, Cursor,
  # etc.) still finds the skill exactly where it expects it.
  if ! ln -s -- "$dest_path" "$entry"; then
    log_error "Moved '$skill_name' to $dest_path but FAILED to create the"
    log_error "symlink back at $entry."
    log_error "The tool will no longer see this skill until you manually"
    log_error "run: ln -s \"$dest_path\" \"$entry\""
    ((skipped_count++)) || true
    continue
  fi

  log_info "Bridged '$skill_name':"
  log_info "  real files now at: $dest_path"
  log_info "  symlink at:        $entry"
  ((moved_count++)) || true
done
shopt -u nullglob

log_info "Done. Bridged: $moved_count, skipped: $skipped_count."
exit 0
