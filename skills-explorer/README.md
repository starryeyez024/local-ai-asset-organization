# AI Assets Explorer

A searchable catalog of valid `SKILL.md` entries found in a configured skills directory. **Browse Skills** shows names, descriptions, inferred tags, and source labels. **Audit Skills** is a local inventory of entries, broken links, name collisions, and file age. The Explorer does not install, invoke, or edit skills.

## Run locally

```bash
make run
# open http://localhost:8790
```

`make run` runs `make regen`, then starts a preview server bound to `127.0.0.1`. You can run the steps separately:

```bash
make regen
make serve
PORT=8080 make serve
SKILLS_ROOT=/another/skills/directory make regen
```

The generator defaults to `~/.agents/skills`. It accepts symlinks and real skill directories, resolves each valid `SKILL.md`, and assigns tags with fixed keyword rules. It writes two files:

- `skills.json` is the shareable catalog. Commit it when publishing an updated catalog.
- `skills-local.json` includes absolute paths and the local audit inventory. It is ignored by Git. Keep it local and do not publish it.

The page tries the local file first. If it is absent, the page shows the shareable Browse Skills catalog and hides Audit Skills. The source-file action works only through the local preview server. Catalog data is a snapshot; run `make regen` after changing the source skills or generator rules.

Requires Python 3.10+ and Make. No Python packages are required. The static site is copied to GitLab Pages by `.gitlab-ci.yml` on `main`; the ignored local inventory is not part of that deployment.
