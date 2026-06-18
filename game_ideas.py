#!/usr/bin/env python3
"""
game_ideas.py

Pick a random activity from activities.txt, then ask the GitHub Copilot CLI to
brainstorm game ideas based on that activity plus a unique "twist".

Usage:
    ./game_ideas.py

Environment:
    COPILOT_BIN    Path to the copilot CLI (auto-detected if unset).
    COPILOT_MODEL  Model to use (default: "auto").
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ACTIVITIES_FILE = SCRIPT_DIR / "activities.txt"
MODEL = os.environ.get("COPILOT_MODEL", "auto")


def find_copilot() -> str:
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


def pick_activity() -> str:
    activities = [
        line.strip()
        for line in ACTIVITIES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not activities:
        sys.exit("ERROR: activities.txt is empty.")
    return random.choice(activities)


def build_prompt(activity: str) -> str:
    return (
        f'Come up with 5 creative & unique nonviolent video game ideas inspired by the activity "{activity}".\n\n'
        "Format each idea as exactly:\n"
        "Title — one-sentence pitch.\n\n"
        "Be terse. No intro, no extra commentary, no elaboration."
    )


def main() -> None:
    copilot = find_copilot()
    activity = pick_activity()
    print(f"Random activity: {activity}\n")

    result = subprocess.run(
        [
            copilot,
            "--model",
            MODEL,
            "--allow-all-tools",
            "--no-color",
            "-p",
            build_prompt(activity),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(result.stderr.strip() or "copilot exited non-zero")

    print(result.stdout.strip())


if __name__ == "__main__":
    main()
