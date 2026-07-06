---
name: learnings
description: Analyze the current session and extract non-obvious learnings to AGENTS.md
user-invocable: true
argument-hint: [focus area]
---

Analyze this session and extract non-obvious learnings to add to the project AGENTS.md file. If the user provides a focus area via $ARGUMENTS, concentrate on that topic.

## What counts as a learning (non-obvious discoveries only)

- Hidden relationships between files or modules
- Execution paths that differ from how code appears
- Non-obvious configuration, env vars, or flags
- Debugging breakthroughs when error messages were misleading
- API/tool quirks and workarounds
- Build/test commands not in README
- Architectural decisions and constraints
- Files that must change together
- Performance characteristics discovered through profiling or benchmarking
- Optimization attempts that failed and why (to prevent re-exploring dead ends)

## What NOT to include

- Obvious facts from documentation
- Standard language/framework behavior
- Things already in AGENTS.md
- Verbose explanations
- Session-specific details (ticket numbers, dates, temporary state)

## Process

1. Review the session for discoveries, errors that took multiple attempts, unexpected connections, and confirmed approaches
2. Read the existing AGENTS.md at the project root
3. Determine which section each learning belongs in — create new sections if needed, but prefer existing ones
4. Update AGENTS.md: add new entries, update stale ones, never duplicate
5. Keep entries to 1-3 lines per insight
6. After updating, summarize what was added/changed and how many learnings per section
