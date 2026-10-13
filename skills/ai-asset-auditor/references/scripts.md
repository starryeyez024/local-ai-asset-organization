# Script discovery and name lookup

Use this reference for standalone scripts and bundled skill helpers. The
`scripts/script-catalog.py` helper beside this reference uses Python 3.11+
standard library only. It reads metadata; it never executes a discovered
script. Keep the whole auditor folder when installing this skill by itself.

## Decision record (2026-10-12)

This project defines a local convention, not a built-in script registry of
Claude Code, Cursor, Codex, or ChatGPT Work. A private TOML catalog records
selected scripts. The private setup configuration binds source IDs to actual
checkouts and may select interpreters. Script code stays in its owning repository
or skill bundle. The resolver returns invocation details; the desktop agent uses
its normal execution tool to run the chosen script.

This keeps registration explicit and stable across checkout moves. The skill
linker and Explorer require skill-specific directory settings; this standalone
helper does not. The optional `--config` wins, followed by
`~/.config/agent-tools/agent-config.toml`, then the older
`~/.config/ai-tools/ai-tools.toml`. The catalog path and source bindings expand
`~` and resolve relative to the configuration file's directory. Entrypoints and
working directories resolve relative to their source root. Neither depends on
the agent's current working directory.

## Private configuration and catalog

The following names and paths are fictional. Store these files in private
configuration, outside a public project checkout.

```toml
# agent-config.toml on macOS
[script_catalog]
path = "script-catalog.toml"

[script_catalog.sources]
example-tools = "~/Projects/example-tools"

# Optional when a script's required working directory is outside its source.
[script_catalog.working_dirs]
workspace = "~/Documents/example-workspace"

[script_catalog.interpreters]
# Optional: pin Python to a chosen virtual environment.
# python = "~/Projects/example-tools/.venv/bin/python"
```

```toml
# agent-config.toml on native Windows: use forward slashes or TOML literal strings
[script_catalog]
path = 'C:\Users\Alex\agent-tools\script-catalog.toml'

[script_catalog.sources]
example-tools = 'C:\Users\Alex\Projects\example-tools'

[script_catalog.interpreters]
python = 'C:\Users\Alex\Projects\example-tools\.venv\Scripts\python.exe'
```

```toml
# script-catalog.toml
schema_version = 1

[[scripts]]
id = "example-tools/hello"
name = "hello"
aliases = ["hello.py"]
description = "Print a local setup greeting."
source = "example-tools"
entrypoint = "scripts/hello.py"
runtime = "python"
args = []
working_dir = "."
platforms = ["macos", "windows"]
status = "active"
```

Each record requires the fields shown. `id` is a lowercase qualified name.
`source` names a binding in `[script_catalog.sources]`; it does not encode a
filesystem path. `args` is a list of distinct argument values. Optional
`working_dir_binding = "workspace"` selects a configured working-directory
root instead of the script source; `working_dir` remains relative to that
root. This preserves a script's required working directory after its code
moves. Optional
`runbook` or `dependencies` text can point to maintained documentation; put
secrets elsewhere. Use `status = "archived"` for historical entries.

`runtime` can be `python`, `sh`, `bash`, `zsh`, `node`, `powershell`, `ruby`, `perl`, or
`executable`. Python defaults to the interpreter running the helper; other
runtimes use a system executable if available. Override a runtime in the
configuration when a virtual environment or specific interpreter is required.
A named configured runtime such as `python-framework` may select a distinct
interpreter for one record while retaining its recorded invocation.
A Windows shell script needs an explicit `sh` binding and a Windows platform
declaration backed by testing. `executable` uses the entrypoint itself.
The resolver reports missing interpreters and unsupported platforms rather
than implying that every script is portable.

## Lookup contract

An exact qualified ID selects its record. A short name, alias, or filename
selects only when one active record matches, using case-insensitive matching.
Two records may intentionally share the same spelling; lookup then returns
`ambiguous` and their qualified IDs. Case-only spelling differences are
invalid across records, to avoid different outcomes on macOS and Windows.
An archived ID returns `inactive`; archived names are omitted from ordinary
short lookup. Unknown names return suggestions only. Missing files or working
directories return `stale_entry` with the source binding. The resolver never
falls back to a same-named command on `PATH`.

Every JSON response has `schema_version = 1` and `status`. A successful
resolution includes `id`, `file`, `interpreter`, `argv`, `args`, `working_dir`,
`runtime`, and provenance. `argv` is an array; pass its values separately to
the execution tool and set its working directory. Do not join it into a shell
command string. Error responses carry a short `code` and `message`, with
candidate IDs or suggestions where applicable. `resolve` never runs the target.

## Procedure

1. Select only the repository or folders relevant to the request. Run
   `inventory --root example-tools=/path/to/checkout --json` before a catalog
   exists, or use configured sources. Add `--caller /path/to/file` for known
   aliases, schedules, or instructions. Inventory classifies files, reports
   actual Git toplevels, and flags possible location assumptions. It skips
   dependency trees, caches, logs, and common credential filenames, never
   follows directory symlinks, and does not leave selected roots. Findings
   are candidates for source review, not a complete call graph.
2. Determine each script's owner. A private helper stays in its skill's
   `scripts/` folder; a project script stays in its project; a reusable
   personal utility goes in an appropriate maintained personal repository.
   Leave installer-managed executables in their install location. Mark old
   experiments inactive. Do not create a generic global scripts repository
   solely for discovery.
3. For a move, record source fingerprint, destination, imports/resources,
   private data and mutable state, callers, invocation, verification, and
   rollback location. Review the concrete map and recoverable originals
   before moving files. Preserve the behavior of compound shell commands;
   do not register a constituent script as an equivalent alias. Offer to review
   the user's shell shortcuts using the profile locations in the parent skill.
   Trace aliases, functions, wrappers, and `PATH` entries to the script they
   actually invoke; include any needed edits in the migration map.
4. Register only selected scripts in the private catalog. Run `validate`,
   then `resolve` by ID and intended aliases from an unrelated directory.
   The optional `--output-candidates` creates derived JSON only when asked;
   inventory never silently edits the catalog.
5. Have the desktop agent run a harmless resolved fixture through its normal
   execution tool. Check the result in each selected app. The Python test
   suite proves the helper contract, not that an app loaded the instruction.
   For approved shell-shortcut changes, check target existence, inspect the
   expanded command in a new shell, and test reloading the profile in a shell
   with the old aliases present. Do not run a data-changing shortcut merely
   to verify its path.

### Direct commands

From a source checkout on macOS:

```text
python3 skills/ai-asset-auditor/scripts/script-catalog.py inventory --root example-tools=/path/to/checkout
python3 skills/ai-asset-auditor/scripts/script-catalog.py validate
python3 skills/ai-asset-auditor/scripts/script-catalog.py --json resolve example-tools/hello
```

From native Windows PowerShell:

```text
py -3 skills/ai-asset-auditor/scripts/script-catalog.py inventory --root example-tools=C:\Projects\example-tools
py -3 skills/ai-asset-auditor/scripts/script-catalog.py validate
py -3 skills/ai-asset-auditor/scripts/script-catalog.py --json resolve example-tools/hello
```

Use `--config PATH` before the operation for a custom setup file. The tool's
`list` operation shows registered names and descriptions. `--json` is useful
when the agent needs structured output; text output stays short.
