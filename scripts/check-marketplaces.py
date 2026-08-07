#!/usr/bin/env python3
"""Verify every skill in skills/ is registered in the marketplace manifests and README.

Exits non-zero on any drift so CI fails loudly. Uses only the standard library.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
MANIFESTS = {
    "Claude Code": ROOT / ".claude-plugin" / "marketplace.json",
    "Codex": ROOT / ".codex-plugin" / "plugin.json",
    "Agents": ROOT / ".agents" / "plugins" / "marketplace.json",
}

errors = []


def err(message: str) -> None:
    errors.append(message)


def skill_dirs():
    return sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


def frontmatter_name(skill: pathlib.Path):
    text = (skill / "SKILL.md").read_text()
    for line in text.splitlines():
        line = line.strip()
        if line == "---":
            continue
        if line.startswith("---"):
            continue
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def main() -> None:
    skills = {d.name for d in skill_dirs()}
    if not skills:
        err(f"no skills found under {SKILLS_DIR}")
        return

    # SKILL.md frontmatter name must match the folder name
    for d in skill_dirs():
        name = frontmatter_name(d)
        if name != d.name:
            err(f"{d.name}/SKILL.md: frontmatter name is {name!r}, expected {d.name!r}")

    # Claude Code marketplace: one plugin entry per skill
    claude_path = MANIFESTS["Claude Code"]
    if not claude_path.exists():
        err(f"Claude Code marketplace: {claude_path.relative_to(ROOT)} is missing")
    else:
        claude = json.loads(claude_path.read_text())
        registered = set()
        for plugin in claude["plugins"]:
            for rel in plugin.get("skills", []):
                name = rel.removeprefix("./skills/").strip("/")
                if not (SKILLS_DIR / name / "SKILL.md").exists():
                    err(f"Claude Code marketplace: plugin {plugin['name']!r} points at missing skill {rel!r}")
                registered.add(name)
        for name in sorted(skills - registered):
            err(f"Claude Code marketplace: missing plugin entry for skill {name!r}")
        for name in sorted(registered - skills):
            err(f"Claude Code marketplace: plugin entry {name!r} has no matching skill directory")

    # Codex and Agents marketplaces bundle the whole skills/ tree
    for label in ("Codex", "Agents"):
        path = MANIFESTS[label]
        if not path.exists():
            err(f"{label} marketplace: {path.relative_to(ROOT)} is missing")
            continue
        data = json.loads(path.read_text())
        if label == "Codex" and data.get("skills") != "./skills/":
            err(f"Codex marketplace: 'skills' should be './skills/', got {data.get('skills')!r}")

    # README skills table must link every skill
    readme = (ROOT / "README.md").read_text()
    for name in sorted(skills):
        if f"./skills/{name}" not in readme:
            err(f"README: skills table is missing a link to ./skills/{name}")

    if errors:
        print("Marketplace drift found:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: all {len(skills)} skills are registered in the marketplaces and README.")


if __name__ == "__main__":
    main()
