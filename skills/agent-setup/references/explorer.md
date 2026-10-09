# Prepare and open the person's Explorer

Run these steps for the user. They should receive a working browser view and a
short explanation of how to use it, not a command-line assignment.

Use Python 3.11 or newer. Locate the repository containing this skill and the
active configuration from the preceding setup. For a standalone Explorer request,
inspect the existing config first; do not migrate it. Inspect `SKILLS_ROOT` if set
and resolve its conflict with the chosen config rather than scanning an unintended
folder. Pass the chosen configuration explicitly during guided setup; the helper also supports the recommended or legacy default configuration for direct use. It rejects the environment override to avoid scanning the wrong folder.

Run the helper from the repository root, substituting the actual configuration:

```bash
python3 skills/agent-setup/scripts/prepare-explorer.py --config ~/.config/agent-tools/agent-config.toml
```

It generates the user's catalogs and copies the viewer and local server into
`~/.local/share/ai-assets-explorer/`. `--output-dir` selects another local location.
Use a location outside the public repository and the private context repo; local
catalogs are generated output. The helper does not install skills or alter sources.
It can be rerun to refresh the same managed directory after source changes or
repository updates. It refuses to replace an unrecognized existing installation.

Start the copied server in a managed terminal or process session:

```bash
python3 ~/.local/share/ai-assets-explorer/serve.py 8790
```

If the port is occupied, check whether it is this user's existing Explorer and
reuse it when appropriate; otherwise choose another available port. Do not stop
an unrelated process. The server binds only to loopback and serves the generated
Explorer directory, not the home folder or personal context. Record the process
session, URL, and directory in setup progress. Closing its terminal stops it;
do not install a persistent background service unless requested.

Open the local URL with the available browser tool. Verify that the page loads,
Browse Skills and Audit Skills read the generated data, and a known skill appears
in a search. If the configured folder is empty, verify the empty state and explain
that skills will appear after the user adds or links some. Don't add unwanted skills
to create a success demonstration. Demonstrate filtering or opening a card; opening
a card doesn't invoke the skill. Offer to run a chosen skill through their agent.

If browser automation is unavailable, verify the server and JSON responses and
give the user the URL, recording the visual check as pending. Do not claim a browser
check succeeded when only generation succeeded. Keep the process alive for their
session, or clearly report if the environment cannot retain it.

At handoff, tell the user they can ask “open my Skills Explorer” or “refresh my
skill catalog.” On either request, read their saved configuration, rerun the helper
when a refresh is needed, and open or restart their local server. Both catalog files stay local and are ignored by Git. This repository publishes
guidance, skills, and a separate fictional demo catalog. Never copy `sample-skills.json` into a personal installation. Skill descriptions themselves may
contain private work; do not copy the generated data into the published site.
