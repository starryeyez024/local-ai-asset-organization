# Configuration keys and context paths

Use `~/.config/agent-tools/agent-config.toml` for shared workflow settings.
The shared `AGENTS.md` tells agents to read it; native applications do not load
this arbitrary TOML file automatically. Each script or skill must name the
configuration it reads and the keys it consumes.

## Use the full TOML key

A table header is part of every key beneath it, until another header begins:

```toml
[custom.jira.fields]
wsjf = "customfield_12345"
story_points = "customfield_12346"
```

These keys are `custom.jira.fields.wsjf` and
`custom.jira.fields.story_points`. In Python, the first is
`config["custom"]["jira"]["fields"]["wsjf"]`. It is not `wsjf` or
`jira.fields.wsjf`. Prefixing the leaf as `jira_wsjf` would change the schema
and require every consumer to change too.

Write the complete dotted key in skill instructions. Parse TOML with a TOML
parser; copying the text beneath a heading loses its namespace. When a key
changes, update scripts, skills, examples, and test fixtures together. Missing
required keys should produce an error naming the full key rather than silently
using an old field ID. Keep existing schema names unless a migration is intended.

Separate workflow inputs and outputs, such as `activity_type` or `timestamp`,
from configuration keys. A shell variable may have a distinct name if its
binding is explicit, for example `AI_VAULT_ROOT` from `directories.vault_root`.
TOML does not export shell variables or expand `${...}` references automatically.
Two skills can also read similarly named keys from different configuration files;
identify the file before treating those keys as conflicts.

## Resolve paths consistently

| Setting | Meaning |
| --- | --- |
| `directories.context_root` | Canonical root for personal context. |
| `directories.vault_root` | Root used to resolve vault-relative paths. |
| `obsidian_vault.reports_directory` | Vault-relative report directory. |
| `instructions.shared_file` | Shared agent instructions. |
| `jira_spaces` | Default Jira project scope, when configured by the workflow. |
| `custom.jira.fields.*` | Site-specific Jira field IDs, when used. |

Expand `~` in path settings. Resolve relative `obsidian_vault` paths against
`directories.vault_root`; preserve absolute paths, including context outside the
vault. Script catalog paths have their own base rules in the
[script procedure](../skills/ai-asset-auditor/references/scripts.md).

Use one setting for the personal-context folder: `directories.context_root`.
When duplicate root settings exist, locate their consumers, migrate those
consumers to this key, and remove the redundant settings and fallback instructions
in the same change. Do not retain unused aliases. Keep configured individual
context-file paths where needed, and load only the files the task needs.

## Keep native application settings in native files

| Information | Maintained location |
| --- | --- |
| Shared paths, Jira scope, field IDs, workflow preferences | `agent-config.toml` |
| Agent behavior and context routing | Shared `AGENTS.md` and native bootstrap instructions |
| Personal role, projects, relationships, and writing preferences | Files under the configured context root |
| Codex MCP definitions, shell policy, authentication options, and trust | Supported Codex configuration layers |
| Credentials | A secret store or a supported runtime credential mechanism, outside Git |

Codex reads user defaults from `~/.codex/config.toml` and trusted project
overrides from `.codex/config.toml`. Moving those settings into the shared
workflow TOML does not configure Codex. Keep machine-level trust and login
settings in the supported user-level location. Avoid maintaining two editable
copies of the same runtime setting. If generating native configurations from
shared metadata, document and verify that generation step first.

Check nesting as well as spelling. For example,
`cli_auth_credentials_store` placed beneath `[shell_environment_policy]` becomes
`shell_environment_policy.cli_auth_credentials_store`; that is not the root
Codex setting. Check the installed version and the
[Codex configuration reference](https://developers.openai.com/codex/config-reference/)
before changing authentication or runtime behavior.

## Verify a change

Parse the canonical file and examples. Confirm every required dotted key exists;
check resolved paths and confirm redundant aliases have no remaining consumers. Inspect the actual targets of
installed skill links: editing an unlinked source copy does not update the active
skill. Search maintained consumers for the old key and run relevant offline
configuration tests with alternate values. Keep personal values and credentials
out of this public repository. Native application discovery remains a separate
runtime check.
