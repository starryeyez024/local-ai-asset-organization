# Local AI Asset Organization

A collection of three complementary skills for managing, organizing, and safely maintaining AI agent skills and assets on your local machine.

## Documentation site

The public guidance is organized as a small documentation site:

- [`pages/index.html`](pages/index.html) — overview and physical-root/tool-facing-view diagram.
- [`pages/agentic-setup.html`](pages/agentic-setup.html) — instructions, configuration, context, and scope.
- [`pages/asset-organization.html`](pages/asset-organization.html) — physical roots, links, naming, collisions, and overrides.
- [`pages/tool-compatibility.html`](pages/tool-compatibility.html) — Codex-first asset compatibility matrix and precedence rules.
- [`PAGES-RESTRUCTURING-PLAN.md`](PAGES-RESTRUCTURING-PLAN.md) — the maintenance plan for the documentation structure.

The site deliberately distinguishes canonical content from tool-facing delivery
mechanisms. A symlink is one option; committed files, generated copies, native
configuration, and platform-managed packages are also valid when a tool or
runtime requires them.

## Shared setup model

This project follows a portable version of the local agentic setup pattern:
keep agent behavior, machine configuration, and personal context separate.
Use one canonical global instruction file, one canonical machine-configuration
file, and short tool-native bootstrap files that point to those sources. Put
project-specific additions in a project-level instruction file only when the
project genuinely needs them.

## The Three Skills

### 1. 🔗 **Skill Linker** — Selective Symlink Creation

**Create symlinks for 1, some, or all skills from a project — without clutter.**

When you download an AI project with 50+ skills but only want to use a handful, this skill lets you select exactly which ones to symlink into `~/.agents/skills`.

#### Key Features:

✅ **Selective linking** — Choose 1, some, or all skills from a project  
✅ **Fuzzy matching** — Typos are forgiven ("override-safe" matches "skill-override-safeguard")  
✅ **Name-based invocation** — Just type skill names, no numbered lists  
✅ **Config-driven** — a canonical `ai-tools.toml` supplies the directories
✅ **Safe by default** — Won't overwrite existing symlinks without `--force`  
✅ **Cross-platform** — Works on macOS, Linux, and Windows  

#### Quick Examples:

```bash
# Link specific skills
skill-linker ktotten/local-ai-asset-organization ai-asset-auditor skill-override-safeguard

# Fuzzy matching (typos OK)
skill-linker project-x asset-audit override-safe

# Link all skills from a project
skill-linker ktotten/local-ai-asset-organization all

# Replace existing symlinks
skill-linker --force project-x ai-asset-auditor

# Interactive mode
skill-linker project-x  # Lists available skills and asks which to link
```

**See:** `skills/skill-linker/SKILL.md` for full documentation.

---

### 2. 🛡️ **Skill Override Safeguard** — Protect Shared Skills

**Critical guardrail: Prevents accidental edits to team/vendor-owned skills.**

Before you edit any skill from a team or vendor repo, this skill explains the safe procedure: copy to your personal namespace, edit the copy, re-point the symlink.

#### Key Features:

✅ **Defense-in-depth** — Prevents drift in team-shared repositories  
✅ **Clear procedures** — Copy → Edit → Re-point workflow  
✅ **Namespace-aware** — Personal edits go under `~/AI Assets/<your-username>/`  
✅ **No enforcement** — Trust-based; relies on reading the safeguard before editing  

#### When to Use:

You want to edit a skill that lives in `~/AI Assets/org-name/` or `~/AI Assets/vendor/` (a team or vendor repo, not your personal namespace).

**Before:** Stop and read this skill's procedure.

**Procedure:**
1. Copy the skill folder to your personal namespace: `~/AI Assets/<your-username>/`
2. Edit your copy (not the original)
3. Re-point the symlink from `~/.agents/skills/<name>` to your copy
4. Original team repo stays clean — no uncommitted drift

**See:** `skills/skill-override-safeguard/SKILL.md` for detailed walkthrough.

---

### 3. 📊 **AI Asset Auditor** — Discover and Organize Everything

**Find scattered skills and MCP servers across your machine and consolidate them.**

When you have skills scattered across `~/.claude/skills`, `~/.cursor/skills-cursor`, and multiple projects, this skill maps everything out and proposes a clean, single physical root with symlink fan-out.

#### Key Features:

✅ **Discovery** — Scans all common skill locations + config files  
✅ **Read-first** — Phase 1 is read-only; never touches files without confirmation  
✅ **Ask-before-acting** — Presents a plan and asks clarifying questions  
✅ **Git-aware** — Detects repos, checks for uncommitted changes, derives names from remotes  
✅ **Conflict detection** — Flags dangling symlinks, duplicate skills, name mismatches  
✅ **Conservative** — When unsure, asks rather than guesses  

#### When to Use:

"I want to clean up my skills folders," "Find duplicates," "Set up a flat AI asset root," "Consolidate my MCP servers."

**Workflow:**
1. **Phase 1:** Discover — scan for all skills and MCP servers (read-only)
2. **Phase 2:** Present plan — show what was found, ask clarifying questions
3. **Phase 3:** Execute — move/symlink based on confirmed plan

**See:** `skills/ai-asset-auditor/SKILL.md` for comprehensive walkthrough (includes nested skills detection, dangling symlinks, and edge-case handling).

---

## How These Three Work Together

```
┌─────────────────────────────────────────────────────────────┐
│         Discover & Organize (Auditor)                       │
│  Find all skills across your machine, consolidate to        │
│  ~/AI Assets with symlink fan-out                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  New Project Downloaded (Skill Linker)                      │
│  Select which skills you want with:                         │
│  $ skill-linker project-name skill-1 skill-2 ...           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Edit a Team Skill? (Override Safeguard)                    │
│  Copy → Edit personal copy → Re-point symlink              │
│  Keep team repo clean                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration: `ai-tools.toml`

The **skill-linker** reads the canonical TOML config file to find the physical
asset root and the tool-facing skill hub. It does not create a second config
file or maintain a separate copy of those paths.

### File Location

```
`/path/to/.config/ai-tools/ai-tools.toml`
```

If the file doesn't exist, **skill-linker** will tell you where to create it and what to put inside.

### File Format

```toml
[directories]
install_dir = "/absolute/path/to/AI Assets"
symlinks_dir = "/absolute/path/to/.agents/skills"
```

Use absolute paths for cross-tool configuration. TOML does not expand `~` by
itself; a consuming application would have to implement that behavior.

### What Each Setting Does

| Setting | Purpose | Default | Example |
|---------|---------|---------|---------|
| `install_dir` | Where you download/store AI projects and their skills | user-defined | An absolute path for the configured machine |
| `symlinks_dir` | Where symlinks are created (must already exist or be creatable) | user-defined | An absolute path for the configured machine |

### Understanding the Two Directories

**`install_dir`** — Your physical storage:
- This is where actual project folders live (e.g. `~/AI Assets/ktotten/local-ai-asset-organization/`)
- **skill-linker** looks here for projects you name
- Should be organized as `<org>/<repo-name>/` nested folders
- Example structure:
  ```
  ~/AI Assets/
  ├── ktotten/
  │   ├── local-ai-asset-organization/
  │   │   └── skills/
  │   │       ├── skill-linker/
  │   │       ├── ai-asset-auditor/
  │   │       └── skill-override-safeguard/
  │   └── my-custom-skills/
  │       └── skills/
  │           └── my-utility/
  ├── anthropics/
  │   └── some-project/
  │       └── skills/
  │           ├── feature-a/
  │           └── feature-b/
  └── redhat/
      └── enterprise-skills/
          └── skills/
              └── deployment-tool/
  ```

**`symlinks_dir`** — Your tool-facing hub:
- This is where AI tools (Cursor, Codex CLI, Claude Code, etc.) look for skills
- **skill-linker** creates symlinks here that point back to `install_dir`
- Should be small (just symlinks, rarely modifying)
- Example structure (after running skill-linker):
  ```
  ~/.agents/skills/
  ├── skill-linker → ~/AI Assets/ktotten/local-ai-asset-organization/skills/skill-linker
  ├── ai-asset-auditor → ~/AI Assets/ktotten/local-ai-asset-organization/skills/ai-asset-auditor
  ├── skill-override-safeguard → ~/AI Assets/ktotten/local-ai-asset-organization/skills/skill-override-safeguard
  ├── my-utility → ~/AI Assets/ktotten/my-custom-skills/skills/my-utility
  ├── feature-a → ~/AI Assets/anthropics/some-project/skills/feature-a
  ├── deployment-tool → ~/AI Assets/redhat/enterprise-skills/skills/deployment-tool
  └── [other symlinks...]
  ```

### How skill-linker Uses the Config

When you run:

```bash
skill-linker ktotten/local-ai-asset-organization skill-linker
```

**skill-linker** does this:

1. **Reads config** — Opens `~/.config/ai-tools/ai-tools.toml`
2. **Expands paths** — Converts `~/AI Assets` to `/Users/ktotten/AI Assets`
3. **Finds project** — Looks for `/Users/ktotten/AI Assets/ktotten/local-ai-asset-organization/`
4. **Discovers skills** — Scans for `skills/*/SKILL.md` files
5. **Creates symlinks** — Adds them to `~/.agents/skills/<skill-name>`

### Editing the Config

You can edit the file by hand anytime:

```bash
# Open in your editor
nano ~/.config/ai-tools/ai-tools.toml

# Or from Cursor:
# File > Open > ~/.config/ai-tools/ai-tools.toml
```

Changes take effect immediately on the next **skill-linker** invocation.

### Common Config Examples

**Example 1: macOS with separate AI and Projects directories**
```toml
[directories]
install_dir = "~/AI Assets"
symlinks_dir = "~/.agents/skills"
```

**Example 2: Linux with projects under Code**
```toml
[directories]
install_dir = "~/Code/ai-projects"
symlinks_dir = "~/.agents/skills"
```

**Example 3: Windows with WSL (inside WSL)**
```toml
[directories]
install_dir = "~/AI Assets"
symlinks_dir = "~/.agents/skills"
```

**Example 4: Absolute paths (works too)**
```toml
[directories]
install_dir = "/Users/ktotten/AI Assets"
symlinks_dir = "/Users/ktotten/.agents/skills"
```

### Troubleshooting Config Issues

**"Config file not found"**
- Create it: `mkdir -p ~/.config/ai-tools/` then create the file with the format shown above

**"Project not found"**
- Check that `install_dir` in your config matches where you actually store projects
- Verify the path exists: `ls ~/AI Assets` (or whatever you set)

**"Can't create symlinks"**
- Ensure `symlinks_dir` exists and you have write permissions: `mkdir -p ~/.agents/skills`
- Try running again: `skill-linker project-name skill-name`

**Want to change directories later**
- Just edit the config file and save. Next run will use the new paths.

---

## Setup

### 1. Create the config file

```bash
# Create the directory
mkdir -p ~/.config/ai-tools/

# Create the file (replace paths if needed)
cat > ~/.config/ai-tools/ai-tools.toml << 'EOF'
[directories]
install_dir = "~/AI Assets"
symlinks_dir = "~/.agents/skills"
EOF
```

### 2. Ensure directories exist

```bash
mkdir -p ~/AI Assets
mkdir -p ~/.agents/skills
```

### 3. Link the skills you want to use

```bash
# Link all three skills from this project
skill-linker ktotten/local-ai-asset-organization all

# Or pick specific ones
skill-linker ktotten/local-ai-asset-organization skill-linker ai-asset-auditor
```

Now you can invoke them:
- `skill-linker project-x foo` — Create symlinks
- `ai-asset-auditor` — Discover and organize
- `skill-override-safeguard` — Before editing a shared skill

## Methodology: One Physical Root, No Duplicates

All three skills are built around a single philosophy:

- **Physical root** (`~/AI Assets`) — One place where all your tracked skills/projects live
- **Symlink fan-out** — Symlinks from `~/.agents/skills` point back to the physical root
- **Cross-tool** — Cursor, Codex CLI, OpenCode, GitHub Copilot, and Gemini CLI all read `~/.agents/skills` natively

**Benefits:**
- Single source of truth — no duplicates across tool directories
- Git-clean — projects stay in their original repos
- Portable — move symlinks, not files
- Discoverable — AI tools find skills automatically

## Troubleshooting

### "Project not found"

Check that your `install_dir` in `~/.config/ai-tools/ai-tools.toml` matches where you actually store projects.

### Symlink already exists

`skill-linker` detects existing symlinks and won't overwrite without `--force`:

```bash
skill-linker --force ktotten/local-ai-asset-organization skill-name
```

### Nested skills in a project

Some projects have `skills/foo/skills/bar/SKILL.md` (skills within skills). The auditor flags these and offers two fixes:
1. Symlink each nested skill individually
2. Ask the upstream maintainer to flatten the structure

### Tool doesn't see my skills

Verify symlinks resolve:

```bash
readlink -f ~/.agents/skills/skill-name
# Should point to a real path with SKILL.md inside
```

## About This Project

These three skills form a **coherent system** for managing scattered AI assets across multiple tools and machines. They prioritize:

- **Safety** — Conservative, ask-before-acting, read-first philosophy
- **Clarity** — Explicit naming, no abbreviations, verbose error messages
- **Portability** — Cross-platform (macOS, Linux, Windows)
- **Simplicity** — Do one job well; don't overcomplicate

See individual SKILL.md files for deep dives into design decisions and edge cases.
