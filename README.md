# randomblock1-skills

A Claude Code plugin marketplace with personal skills.

## Plugins

- **learnings** — extract non-obvious learnings from a session into `AGENTS.md`.
- **just-use-postgres** — architecture guidance for choosing data infrastructure, defaulting to Postgres-based alternatives where they fit.
- **mechanical-sympathy** — find, verify, and rank CPU-friendly improvements in hot paths.

## Using this marketplace

From Claude Code:

```
/plugin marketplace add ~/git/skills
/plugin install learnings@randomblock1-skills
/plugin install just-use-postgres@randomblock1-skills
/plugin install mechanical-sympathy@randomblock1-skills
```

Or point at the GitHub repo:

```
/plugin marketplace add Randomblock1/skills
```

## Adding a new skill

1. Create `plugins/<name>/.claude-plugin/plugin.json` with `name`, `description`, `version`.
2. Put the skill itself in `plugins/<name>/skills/<name>/SKILL.md` (plus any `references/` files it needs).
3. Add an entry for it to `.claude-plugin/marketplace.json`.
