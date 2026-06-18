#!/usr/bin/env python3
"""
expand_activities.py

For every letter A-Z, ask the GitHub Copilot CLI to brainstorm 50+ additional
activities/hobbies starting with that letter, then merge the new ideas into
activities.txt (deduplicated case-insensitively, alphabetically sorted, with a
blank line between each letter's section).

Usage:
    ./expand_activities.py             # process all letters A-Z
    ./expand_activities.py a c f       # process only the given letters

Environment:
    COPILOT_BIN    Path to the copilot CLI (auto-detected if unset).
    COPILOT_MODEL  Model to use (default: "auto").
"""

from __future__ import annotations

import os
import re
import shutil
import string
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ACTIVITIES_FILE = SCRIPT_DIR / "activities.txt"
WORK_DIR = SCRIPT_DIR / ".expand_work"
MODEL = os.environ.get("COPILOT_MODEL", "auto")

LIST_ITEM_PREFIX = re.compile(r"^\s*[-*\u2022]?\s*\d*[.)]?\s*")


def find_copilot() -> str:
    """Locate the copilot CLI, falling back to the VS Code bundled copy."""
    binary = os.environ.get("COPILOT_BIN") or shutil.which("copilot")
    if binary:
        return binary

    candidate = (
        Path.home()
        / ".config/Code/User/globalStorage/github.copilot-chat/copilotCli/copilot"
    )
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)

    sys.exit(
        "ERROR: could not find the 'copilot' CLI. "
        "Set COPILOT_BIN=/path/to/copilot."
    )


def read_activities() -> list[str]:
    text = ACTIVITIES_FILE.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines()]


def existing_for_letter(activities: list[str], letter: str) -> list[str]:
    """All non-empty activities that start with the given letter."""
    lower = letter.lower()
    return [a for a in activities if a and a[0].lower() == lower]


def build_prompt(letter: str, existing: list[str]) -> str:
    existing_block = "\n".join(existing) if existing else "(none yet)"
    return (
        f'Brainstorm a long list of real activities, hobbies, sports, crafts, or\n'
        f'pastimes whose names start with the letter "{letter}".\n\n'
        "Aim for 50 or more if you can think of that many genuinely distinct, good\n"
        "ones. Fewer is fine if you truly cannot reach 50 quality ideas. Do NOT pad\n"
        "the list with low-quality, made-up, or duplicate entries.\n\n"
        "The following items already exist, so DO NOT repeat any of them:\n"
        f"{existing_block}\n\n"
        "Output rules (follow exactly):\n"
        "- Output ONLY the new activity names, one per line.\n"
        f'- Each name must genuinely start with the letter "{letter}".\n'
        '- Use title case (capitalize the first word), e.g. "Apple picking".\n'
        "- No numbering, no bullet points, no commentary, no blank lines, "
        "no code fences."
    )


def generate_for_letter(copilot: str, letter: str, existing: list[str]) -> str:
    prompt = build_prompt(letter, existing)
    result = subprocess.run(
        [copilot, "--model", MODEL, "--allow-all-tools", "--no-color", "-p", prompt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "copilot exited non-zero")
    return result.stdout


def clean_output(letter: str, raw: str) -> list[str]:
    """Turn raw model output into a tidy list of candidate activities."""
    cleaned: list[str] = []
    lower = letter.lower()
    for line in raw.splitlines():
        line = LIST_ITEM_PREFIX.sub("", line.strip())
        if not line or "```" in line:
            continue
        if line[0].lower() != lower:
            continue
        cleaned.append(line)
    return cleaned


def dedupe_sorted(items: list[str]) -> list[str]:
    """Sort case-insensitively and drop case-insensitive duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for item in sorted((i for i in items if i), key=str.lower):
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def main(argv: list[str]) -> int:
    copilot = find_copilot()
    WORK_DIR.mkdir(exist_ok=True)

    if argv:
        letters = [a[0].upper() for a in argv if a]
    else:
        letters = list(string.ascii_uppercase)

    activities = read_activities()
    merged_sections: dict[str, list[str]] = {}

    print(f"Using copilot: {copilot} (model: {MODEL})")
    print(f"Activities file: {ACTIVITIES_FILE}\n")

    for letter in letters:
        print(f"==> Letter {letter}")
        existing = existing_for_letter(activities, letter)
        print(f"    existing: {len(existing)}")

        try:
            raw = generate_for_letter(copilot, letter, existing)
        except RuntimeError as exc:
            print(f"    WARNING: copilot call failed for {letter}: {exc}", file=sys.stderr)
            continue

        (WORK_DIR / f"{letter}.raw.txt").write_text(raw, encoding="utf-8")

        new_items = clean_output(letter, raw)
        (WORK_DIR / f"{letter}.new.txt").write_text(
            "\n".join(new_items) + "\n", encoding="utf-8"
        )
        print(f"    generated: {len(new_items)}")

        merged = dedupe_sorted(existing + new_items)
        merged_sections[letter] = merged
        print(f"    merged total: {len(merged)}")

    print(f"\n==> Rebuilding {ACTIVITIES_FILE}")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = ACTIVITIES_FILE.with_suffix(f".txt.bak.{timestamp}")
    shutil.copy2(ACTIVITIES_FILE, backup)
    print(f"    backup saved to {backup}")

    sections: list[str] = []
    for letter in string.ascii_uppercase:
        if letter in merged_sections:
            section = merged_sections[letter]
        else:
            # Letter not processed this run: keep whatever already exists for it.
            section = dedupe_sorted(existing_for_letter(activities, letter))
        if section:
            sections.append("\n".join(section))

    ACTIVITIES_FILE.write_text("\n\n".join(sections) + "\n", encoding="utf-8")

    total = sum(1 for line in ACTIVITIES_FILE.read_text(encoding="utf-8").splitlines() if line.strip())
    print(f"    done. activities.txt now has {total} activities.\n")
    print(f"Work files (raw + per-letter) are in: {WORK_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
