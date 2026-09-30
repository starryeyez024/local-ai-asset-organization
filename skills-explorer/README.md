# skills-explorer

Filterable single-page explorer for the AI-first skills across the 6 ixd-firefly persona modules (Product Management, Program Management, Data Science, UX Design, UX Research, Content Creation).

**Quick start:**

```bash
make run
# open http://localhost:8790
```

`make run` regenerates `skills.json` and starts the local preview server in
one shot. Individual steps:

```bash
make regen   # regenerate skills.json from ~/.agents/skills
make serve   # serve the site locally (PORT=8080 make serve to override)
```

See the in-app **How to Update** page (`how-to-update.html`) for the same
instructions with more context.

The skills source directory defaults to `~/.agents/skills` (the flat symlink
farm that Cursor/Codex CLI read natively). Override it with the `SKILLS_ROOT`
environment variable to scan a different directory instead:

```bash
SKILLS_ROOT=/some/other/path python3 generate-skills-json.py
```

Requires Python 3.10+. No dependencies beyond the standard library.

Deployed via GitLab Pages on push to `main` (see `.gitlab-ci.yml`).
