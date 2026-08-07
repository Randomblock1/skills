# randomblock1-skills

Personal [Agent Skills](https://agentskills.io/) for coding agents — Claude Code, Codex, Cursor, and anything else that reads `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [full-review](./skills/full-review) | Thorough, verification-first review of a working diff |
| [just-use-postgres](./skills/just-use-postgres) | Prefer Postgres-based data infrastructure where it fits |
| [learnings](./skills/learnings) | Extract non-obvious session learnings into `AGENTS.md` |
| [mechanical-sympathy](./skills/mechanical-sympathy) | Find, verify, and rank CPU-friendly hot-path improvements |
| [trim-comments](./skills/trim-comments) | Trim comments and docs so every comment earns its place |

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
/plugin install full-review@randomblock1-skills
/plugin install just-use-postgres@randomblock1-skills
/plugin install learnings@randomblock1-skills
/plugin install mechanical-sympathy@randomblock1-skills
/plugin install trim-comments@randomblock1-skills
```

Local path:

```
/plugin marketplace add ~/git/skills
```

## Layout

Skills follow the open Agent Skills format:

```
skills/<name>/SKILL.md
skills/<name>/…          # optional references, scripts, assets
```

Claude Code marketplace metadata lives in `.claude-plugin/marketplace.json` and points at those same skill folders (same pattern as [anthropics/skills](https://github.com/anthropics/skills)).

Codex/ChatGPT marketplace metadata lives in `.codex-plugin/plugin.json` (which points `skills` at `./skills/`) plus `.agents/plugins/marketplace.json`, the same layout as [openai/plugins](https://github.com/openai/plugins) and [JITx-Inc/jitx-skills](https://github.com/JITx-Inc/jitx-skills).

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter (name must match the folder).
2. Add any supporting files under that skill directory (`references/`, `scripts/`, etc.).
3. Register it in `.claude-plugin/marketplace.json` if you want it installable via Claude Code's marketplace. The Codex plugin already bundles the whole `skills/` tree, so no extra step is needed there.
