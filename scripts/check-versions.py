#!/usr/bin/env python3
"""Require marketplace version bumps whenever a skill changes.

Compares the current working tree against a base git revision (the merge base
with the default branch, or HEAD for pushes). If any file under skills/ differs,
each marketplace manifest that bundles those skills must have had its version
bumped — strictly greater than the base revision's version. Exits non-zero on
any drift so CI fails loudly. Uses only the standard library.
"""

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
MANIFESTS = {
    "Claude Code marketplace": (ROOT / ".claude-plugin" / "marketplace.json", "metadata", "version"),
    "Codex/Agents plugin": (ROOT / ".codex-plugin" / "plugin.json", None, "version"),
}
DEFAULT_BRANCH = "master"


def err(messages, label):
    messages.append(f"  - {label}")
    return messages


def run_git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def version_tuple(version):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def current_version(manifest, section, key):
    data = json.loads(manifest.read_text())
    obj = data[section] if section else data
    return obj[key]


def base_version(manifest, section, key, base_rev):
    """Version of the manifest at base_rev, or None if it didn't exist."""
    rel = manifest.relative_to(ROOT).as_posix()
    try:
        text = run_git("show", f"{base_rev}:{rel}")
    except subprocess.CalledProcessError:
        return None
    data = json.loads(text)
    obj = data[section] if section else data
    return obj.get(key)


def main() -> None:
    # Resolve the revision to diff against. Pull requests diff against the merge
    # base with the default branch; pushes diff against the previous commit.
    base_rev = run_git("merge-base", "HEAD", f"origin/{DEFAULT_BRANCH}")
    if not base_rev:
        base_rev = run_git("rev-parse", "HEAD~1")

    changed = run_git("diff", "--name-only", "--relative", base_rev, "--", "skills/")
    if not changed:
        print("OK: no skills changed, no version bump required.")
        return

    changed_skills = sorted({pathlib.Path(p).parts[1] for p in changed.splitlines() if p.startswith("skills/")})
    print(f"Changed skills: {', '.join(changed_skills)}")

    errors = []
    for label, (manifest, section, key) in MANIFESTS.items():
        if not manifest.exists():
            err(errors, f"{label}: {manifest.relative_to(ROOT)} is missing")
            continue
        cur = version_tuple(current_version(manifest, section, key))
        if cur is None:
            err(errors, f"{label}: version {current_version(manifest, section, key)!r} is not MAJOR.MINOR.PATCH")
            continue
        prev = base_version(manifest, section, key, base_rev)
        if prev is None:
            continue  # manifest is new — nothing to bump against
        if version_tuple(prev) is None:
            err(errors, f"{label}: version {prev!r} at {base_rev} is not MAJOR.MINOR.PATCH")
            continue
        if cur <= version_tuple(prev):
            err(errors, f"{label}: skills changed but version {'.'.join(map(str, cur))} was not bumped (was {prev})")

    if errors:
        print("Version drift found:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    print("OK: skill changes are covered by a marketplace version bump.")


if __name__ == "__main__":
    main()
