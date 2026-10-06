# Public Guidance Site Restructuring Plan

Status: Planning only. No page restructuring has been implemented.
Research reviewed: 2026-10-05.
Updated: 2026-10-05 after Cursor symlink research and multi-tool structure review.

## Goal

Make the project’s public guidance easier to navigate without losing the
technical depth that makes it useful. The site should teach a reusable local
agentic-workspace pattern for multiple tools while being explicit about where
tool behavior differs.

## Homepage decision

Keep the “Physical root vs. tool-facing symlink views” diagram on the
homepage. It is one of the clearest explanations of the core model and should
remain part of the first-pass explanation, not be hidden on a subpage.

The homepage should become a concise overview rather than the complete manual.
It should contain:

1. The problem: duplicated, drifting, or broken AI assets.
2. The core model: one physical root plus tool-facing views.
3. The physical-root/tool-facing-hub diagram currently in `pages/index.html`.
4. The five principles in abbreviated form.
5. A short explanation of instructions, configuration, and context as three
   separate concerns.
6. Clear links to the deeper guides.
7. A short, safety-oriented getting-started path.

## Proposed information architecture

### `pages/index.html` — Overview

Audience: someone encountering the methodology for the first time.

Keep the core diagram, the problem statement, the main principles, and a
short “choose a guide” section. Target roughly 300–450 lines of content and
keep implementation details out of the landing page.

### `pages/agentic-setup.html` — Instructions, configuration, and context

Explain:

- One canonical global instruction source.
- Short tool-native bootstrap files.
- One canonical machine configuration source.
- Separate personal/project context from behavior and configuration.
- Optional project-level instruction files.
- Global versus project-local scope.
- Absolute paths for cross-tool configuration and relative paths inside a
  configured root.
- What a shareable repository should and should not contain.

### `pages/asset-organization.html` — Skills and assets

Explain:

- Physical asset-root layout.
- Tool-facing skill hubs and symlink views.
- Naming from git remotes and nested organizations.
- Duplicate skill names and collision handling.
- Personal overrides using copy → edit → re-point.
- Read-first auditing and confirmation before filesystem changes.

Keep the existing architecture diagrams and naming examples here as detailed
reference material. The homepage should link to this page after showing the
main physical-root/tool-facing-hub diagram.

### `pages/tooling.html` — Tool-specific behavior and adapters

Explain:

- Why discovery behavior differs by tool.
- Which tools support or do not support symlinked skill directories, with
  version and runtime scope called out explicitly.
- MCP configuration as explicit-path configuration rather than directory
  discovery.
- Copy-based installers such as Lola.
- The Lola bridge script and its limitations.
- When a shared portable skill needs a tool-specific adapter or duplicate
  representation.

This page must clearly label confirmed tool behavior, version-sensitive
behavior, project recommendations, and fallback projections.

## Compatibility matrix requirements

The tooling guide should include a prominent compatibility matrix organized by
asset type and agent. The agent columns should appear in this order:

1. Codex
2. Cursor
3. Claude Code
4. ChatGPT

The asset rows should cover at least:

- Skills.
- Global behavior instructions.
- Project behavior instructions.
- Project context and durable knowledge.
- Memory.
- MCP server code.
- MCP configuration.
- Commands, agents, and wrappers.

Each cell should identify the appropriate delivery mechanism:

- Symlink.
- Committed project file.
- Generated or copied projection.
- Native tool configuration.
- Platform-managed distribution.
- Verify/version-dependent behavior.

The matrix must distinguish runtime scope where relevant:

- Local machine.
- Committed project/repository.
- Cloud or hosted agent.
- Remote workspace.

Do not imply that a global local symlink is available to a hosted runtime.
For example, local Claude and Cursor skill directories do not automatically
make those skills available to their cloud environments. Codex and Cursor also
have different distribution mechanisms for local skills versus plugins or
hosted sessions.

## Precedence and collision requirements

The guide should state precedence rules once, in a dedicated section, rather
than repeating a vague “project overrides global” claim in every asset row.
The current documented guidance to capture is:

- **Codex instructions:** broader `AGENTS.md` instructions load before more
  specific repository and directory instructions; more-specific instructions
  can refine or override earlier ones.
- **Codex skills:** same-name repository and user skills are not merged; both
  may appear. Do not assume a project skill silently replaces a user skill.
- **Claude Code skills:** enterprise takes precedence over personal, and
  personal takes precedence over project for same-name local skills.
- **Cursor:** document project/user collisions as version- and
  runtime-dependent unless the behavior is verified for the specific asset
  type.
- **ChatGPT:** skills, plugins, Project knowledge, and workspace settings are
  platform-managed; filesystem precedence does not apply.

When precedence is undocumented or ambiguous, recommend unique names,
explicit source labeling, or a direct test against the target tool surface.

## Research findings that affect the guidance

### Cursor symlinks

The linked Cursor issue was a real discovery bug in older Cursor releases,
especially for symlinked global skills. Cursor staff reported an IDE fix in
Cursor 2.5, but follow-up reports still showed inconsistent behavior across
versions and runtimes. Current Cursor documentation lists several skill roots
and describes recursive discovery, but it does not guarantee identical
symlink behavior across every Cursor product surface.

The guidance should therefore say:

- The physical asset root can remain the source of truth.
- Cursor IDE skill directories may use symlinked projections, but the result
  should be verified against the installed Cursor version.
- Cursor SDK/local runtime, Cloud Agents, remote-SSH workflows, and other
  non-IDE surfaces may canonicalize paths, filter targets outside a workspace,
  or require a real copied projection.
- The project must not claim that one symlink hub works identically across
  Cursor, Claude Code, Codex, Gemini, SDKs, and hosted agents.
- Troubleshooting should include updating/reloading the tool, verifying the
  link target and `SKILL.md`, and switching to a tool-specific projection when
  symlink discovery is unreliable.

Useful sources:

- [Cursor Agent Skills documentation](https://cursor.com/docs/skills)
- [Original Cursor symlink issue](https://forum.cursor.com/t/cursor-doesnt-follow-symlinks-to-discover-skills/149693)
- [Cursor symlink installation issue and staff response](https://forum.cursor.com/t/skills-installed-by-skill-sh-will-not-be-found-if-use-symlink-method/151014)
- [Cursor SDK local-runtime limitation](https://forum.cursor.com/t/cursor-sdk-local-runtime-does-not-appear-to-load-filesystem-skills/160664)
- [Cursor remote-SSH symlink issue](https://forum.cursor.com/t/cannot-open-symlinked-global-skill-rule-in-editor/168425)

### Coworker multi-tool structure

The proposed `~/work/context` model identifies a real problem: one logical
asset may need several discovery surfaces. It is a strong pattern when its
boundaries remain explicit:

1. Canonical/shareable content: portable instructions, procedures, and
   project context.
2. Personal or project context: knowledge that should not be mixed with
   machine behavior or executable configuration.
3. Machine/tool configuration: MCP files, settings, absolute paths, and
   native bootstrap files.
4. Tool adapters or generated projections: wrappers, copied skills, command
   stubs, or other representations required by a specific tool.

The public guidance should recommend one canonical source where a tool can
reliably consume it, but should not treat duplication as inherently wrong.
Intentional copies are appropriate when a tool cannot follow symlinks, rewrites
installed content, requires a different package shape, or operates in a
different workspace/runtime boundary. Every such copy should identify its
source and update/synchronization rule so it does not become an unexplained
competing canonical version.

The coworker's structure should therefore be presented as one valid
implementation pattern, not a universal directory layout. A single `context`
repository should not mix credentials, personal knowledge, instructions,
executable configuration, and tool-specific artifacts without labeling their
different lifecycles.

## Content principles

- Keep the homepage conceptual and visual.
- Put operational procedures on reference pages and in downloadable skills.
- Use placeholders such as `$ASSET_ROOT` in shareable examples; do not embed a
  maintainer’s private absolute paths.
- Distinguish portable content from tool-specific files, adapters, and
  configuration.
- Prefer one canonical source where the consuming tool reliably supports it;
  use intentional adapters or generated copies when it does not.
- Avoid unmanaged duplication, but do not prohibit deliberate copies required
  by a tool, runtime, or hosted environment.
- Treat same-name collisions as a separate compatibility concern from
  filesystem organization.
- Do not promise one symlink layout works identically across every tool.
- Treat duplication as an intentional compatibility choice when a tool cannot
  consume the canonical representation safely.
- Preserve the read-first, ask-before-acting safety model.

## Implementation sequence

1. Treat the research conclusions above as input to the tooling guide and keep
   confirmed behavior, version-sensitive behavior, and recommendations visibly
   separate.
2. Add shared navigation and a small site-level stylesheet or shared style
   strategy if needed.
3. Extract the setup guidance into `agentic-setup.html`.
4. Extract the asset and naming guidance into `asset-organization.html`.
5. Extract MCP, Lola, and tool-compatibility guidance into `tooling.html`.
6. Add the asset-by-agent compatibility matrix, runtime legend, and
   precedence/collision guidance to the tooling page.
7. Reduce `index.html` to the overview while preserving the physical-root /
   tool-facing-hub diagram.
8. Check every internal link, code example, source reference, and generated
   asset.
9. Validate the pages locally and review the homepage at desktop and narrow
   viewport widths.

## Open decisions

- Whether sources should remain at the bottom of each page or move to one
  references page.
- Whether the existing `skills-explorer` should be linked as a separate tool
  or treated as part of the documentation navigation.
- Whether the public guidance should recommend symlinks by default, or frame
  them as one option selected only after checking each tool’s discovery and
  installer behavior. Current recommendation: present symlinks as an adapter
  strategy and require verification per tool/runtime, not as a universal
  guarantee.
