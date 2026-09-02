# randomblock1-skills

Personal [Agent Skills](https://agentskills.io/) for coding agents — Claude Code, Codex, Cursor, and anything else that reads `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [auto-optimize](./skills/auto-optimize) | Turn a codebase into an autonomous keep-or-revert optimization loop judged by a frozen measurement harness |
| [full-review](./skills/full-review) | Thorough, patterns-tuned code review of a working diff — diff hygiene plus ten verification-backed dimensions |
| [gpu-sympathy](./skills/gpu-sympathy) | Find, verify, and rank GPU-friendly improvements in kernels and GPU pipelines (coalescing, tiling, occupancy, divergence, transfers) |
| [just-use-postgres](./skills/just-use-postgres) | Architecture guidance for choosing data infrastructure, defaulting to Postgres-based alternatives where they fit |
| [learnings](./skills/learnings) | Extract non-obvious learnings from a session into AGENTS.md |
| [mechanical-sympathy](./skills/mechanical-sympathy) | Find, verify, and rank CPU-friendly improvements in hot paths (cache layout, branches, allocations) |
| [trim-comments](./skills/trim-comments) | Audit and trim comments and docs so every comment earns its place |

## Install (Codex, Cursor, Claude Code, …)

Via the [skills](https://skills.sh/) CLI — installs into the agents you have locally:

```bash
npx skills add Randomblock1/skills
```

Or from a local clone:

```bash
npx skills add ~/git/skills
```

Pick specific skills or agents:

```bash
npx skills add Randomblock1/skills --skill learnings just-use-postgres
npx skills add Randomblock1/skills --agent codex cursor claude-code
```

## Claude Code marketplace (optional)

Still works as a Claude Code plugin marketplace:

```
/plugin marketplace add Randomblock1/skills
/plugin install auto-optimize@randomblock1-skills
/plugin install full-review@randomblock1-skills
/plugin install gpu-sympathy@randomblock1-skills
/plugin install just-use-postgres@randomblock1-skills
/plugin install learnings@randomblock1-skills
/plugin install mechanical-sympathy@randomblock1-skills
/plugin install trim-comments@randomblock1-skills
```

Local path:

```
/plugin marketplace add ~/git/skills
```

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter (name must match the folder).
2. Add any supporting files under that skill directory.
3. Add a row to the skills table above and a plugin entry in `.claude-plugin/marketplace.json`. The Codex and Agents marketplaces bundle the whole `skills/` tree, so no extra step is needed there.

CI (`scripts/check-marketplaces.py`) fails if a skill is missing from any manifest or the README table.

## Changing a skill

Any change under `skills/` must bump the marketplace versions that ship those skills: `metadata.version` in `.claude-plugin/marketplace.json` and `version` in `.codex-plugin/plugin.json`. CI (`scripts/check-versions.py`) diffs `skills/` against the base revision and fails if either version wasn't increased.
