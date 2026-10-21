# Script lookup verification — 2026-10-12

The public contract is implemented by
`skills/ai-asset-auditor/scripts/script-catalog.py`. The fictional fixture
and tests contain no personal machine paths. The helper has no dependency on
the linker, Explorer, Bash, Make, or a skills hub.

| Check | Result | Environment and evidence |
| --- | --- | --- |
| Helper, Explorer, and existing project tests | Verified | macOS 26.7.1, Python 3.13.7; `python3 -B -m unittest discover -s tests -q` passed 40 tests. |
| Direct named fixture from unrelated directory | Verified | From an unrelated working directory, `resolve greet` returned `example-tools/hello`, separate `argv` values, and a source working directory. Running that known harmless fixture printed `hello fixture`. |
| Independent auditor package | Verified | Test copies only `skills/ai-asset-auditor/` and resolves the fixture with its bundled helper. |
| Scheduled-job scanner | Verified | Fixture tests cover direct launchd and cron references, shell `cd`, multiple launchd directories, system cron, and rejection of a shell function name or an `echo` mention. On this Mac the scanner found 10 directly referenced script files; nine match registered scripts. Job load and success were not checked. |
| Script categories | Verified | The regenerated catalog assigns all 23 registered scripts at least one Work Stage and Task Type; 13 match Gather, 23 Produce, and three Reflect. Categories use fixed keyword rules and script action hints. |
| Local Explorer snapshot | Verified | Managed local output has 293 skills and 23 registered scripts; nine have direct launchd matches and none have cron matches. The sidebar separates Asset Type and Automation. Browser interaction showed 23 scripts by default, nine with Automated selected, 14 with Manual selected, and all 23 with both selected. HTML/JavaScript syntax checked. |
| Native Windows helper | Not verified | No native Windows host was available. TOML syntax and path examples are provided; a macOS simulation is not a Windows execution check. |

## Desktop instruction checks

These require a fresh app session after connecting each app's instructions.
Python tests and a manual invocation from Codex do not prove that a desktop
agent loaded the shared lookup rule.

| App | OS | Version | Instruction entry point | Result and pending evidence |
| --- | --- | --- | --- | --- |
| Claude Code | macOS 26.7.1 | 2.1.294 installed | User `CLAUDE.md` bootstrap to shared instructions | Not verified; run short name, qualified ID, and skill-requested fixture in a fresh session. |
| Cursor | macOS 26.7.1 | Not captured | User Rules or supported local rule | Not verified; inspect active rule and run the three fixture forms. |
| Codex desktop | macOS 26.7.1 | Not captured | User `AGENTS.md` bootstrap to shared instructions | Not verified in a fresh session; manual resolver execution in the current session is separate evidence. |
| ChatGPT Work desktop | macOS 26.7.1 | Not captured | Work desktop instruction connection | Not verified; confirm this interface separately from Codex and run the three fixture forms. |

## Representative returned-text comparison

For the fictional `greet` fixture, manual file discovery plus reading the
configuration and complete catalog returned 2,283 bytes. The helper's text
`resolve greet` response returned 359 bytes. This compares exploratory text
for one fixture only; it excludes safety review and makes no universal token
savings claim.

## Source references

The desktop connection guidance was checked against the official
[Cursor Rules documentation](https://cursor.com/docs/rules),
[Claude Code skills documentation](https://code.claude.com/docs/en/skills),
and [OpenAI's ChatGPT Work and Codex help](https://help.openai.com/en/articles/20001275)
on 2026-10-12. Installed interface behavior still needs the checks above.
