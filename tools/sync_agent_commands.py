#!/usr/bin/env python3
"""Render native agent command adapters from the SpecNative command manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "Template-Project-Agents-AI"
MANIFEST = TEMPLATE / ".specnative" / "commands.json"
CLAUDE_DIR = TEMPLATE / ".claude" / "commands"
CODEX_CONFIG = TEMPLATE / "codex.toml"


def load_commands() -> list[dict[str, str]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("commands.json must contain a non-empty commands list")
    for command in commands:
        if not all(isinstance(command.get(key), str) and command[key] for key in ("name", "description", "prompt")):
            raise ValueError("each command must define non-empty name, description and prompt")
    names = [command["name"] for command in commands]
    if len(names) != len(set(names)):
        raise ValueError("command names must be unique")
    return commands


def render_claude(command: dict[str, str]) -> str:
    return f"{command['prompt'].strip()}\n"


def render_codex(commands: list[dict[str, str]]) -> str:
    lines = [
        "# codex.toml — generated from the SpecNative command manifest.",
        "# Framework maintainers regenerate it from .specnative/commands.json.",
        "",
        "[mcp_servers.specnative]",
        'command = "./.specnative/.venv/bin/python3"',
        'args = ["./.specnative/specnative_mcp.py"]',
        'type = "stdio"',
    ]
    for command in commands:
        prompt = command["prompt"].replace("$ARGUMENTS", "la solicitud del desarrollador")
        prompt = prompt.replace('"""', '\\\"\\\"\\\"')
        lines.extend([
            "",
            f"[prompts.{command['name']}]",
            f"description = {json.dumps(command['description'], ensure_ascii=False)}",
            'prompt = """',
            prompt,
            '"""',
        ])
    return "\n".join(lines) + "\n"


def expected_files(commands: list[dict[str, str]]) -> dict[Path, str]:
    files = {CLAUDE_DIR / f"{command['name']}.md": render_claude(command) for command in commands}
    files[CODEX_CONFIG] = render_codex(commands)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write generated adapters")
    parser.add_argument("--check", action="store_true", help="Fail when adapters are stale")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")

    try:
        files = expected_files(load_commands())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Command manifest error: {exc}", file=sys.stderr)
        return 1

    stale = [path for path, content in files.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
    if args.check:
        if stale:
            print("Generated agent adapters are stale:", file=sys.stderr)
            for path in stale:
                print(f"- {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("Agent command adapters are current.")
        return 0

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Generated {len(files)} agent command adapters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
