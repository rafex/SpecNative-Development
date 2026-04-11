#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "agents/README.md",
    "agents/PRODUCT.md",
    "agents/ARCHITECTURE.md",
    "agents/STACK.md",
    "agents/CONVENTIONS.md",
    "agents/COMMANDS.md",
    "agents/DECISIONS.md",
    "agents/ROADMAP.md",
    "agents/SCHEMA.md",
    "agents/TRACEABILITY.md",
    "tasks/README.md",
    "workflows/README.md",
]
SPEC_STATES = {"draft", "active", "blocked", "done", "superseded"}
TASK_STATES = {"todo", "in_progress", "blocked", "done"}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_toml_block(text: str) -> dict[str, Any]:
    match = re.search(r"```toml\n(.*?)\n```", text, flags=re.DOTALL)
    if not match:
        raise ValueError("missing TOML metadata block")
    return parse_simple_toml(match.group(1))


def parse_simple_toml(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid TOML line: {line}")
        key, value = [part.strip() for part in line.split("=", 1)]
        data[key] = parse_toml_value(value)
    return data


def parse_toml_value(raw: str) -> Any:
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        parts = [part.strip() for part in inner.split(",")]
        return [parse_toml_value(part) for part in parts]
    if raw in {"true", "false"}:
        return raw == "true"
    return raw


def extract_all_toml_blocks(text: str) -> list[dict[str, Any]]:
    return [parse_simple_toml(block) for block in re.findall(r"```toml\n(.*?)\n```", text, flags=re.DOTALL)]


def parse_task_entries(text: str) -> list[dict[str, Any]]:
    sections = re.split(r"(?=^###\s+)", text, flags=re.MULTILINE)
    entries: list[dict[str, Any]] = []

    for section in sections:
        heading = re.search(r"^###\s+([A-Z0-9-]+)\s+-\s+(.+)$", section, flags=re.MULTILINE)
        if not heading:
            continue

        toml_blocks = extract_all_toml_blocks(section)
        if not toml_blocks:
            raise ValueError(f"task section {heading.group(1)} is missing a TOML metadata block")

        metadata = toml_blocks[0]
        metadata.setdefault("id", heading.group(1))
        metadata.setdefault("title", heading.group(2))
        entries.append(metadata)

    return entries


def parse_spec(path: Path) -> dict[str, Any]:
    text = load_text(path)
    metadata = extract_toml_block(text)
    metadata["path"] = str(path.relative_to(ROOT))
    return metadata


def parse_tasks(path: Path) -> dict[str, Any]:
    text = load_text(path)
    metadata = extract_toml_block(text)
    metadata["path"] = str(path.relative_to(ROOT))
    metadata["tasks"] = parse_task_entries(text)
    return metadata


def find_specs() -> list[Path]:
    return sorted(ROOT.glob("agents/specs/**/SPEC.md")) + ([ROOT / "agents/SPEC.md"] if (ROOT / "agents/SPEC.md").exists() else [])


def find_task_files() -> list[Path]:
    return sorted(path for path in ROOT.glob("tasks/**/TASKS.md"))


def validate() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    specs = find_specs()
    if not specs:
        errors.append("missing required spec: agents/SPEC.md or agents/specs/**/SPEC.md")

    for spec_path in specs:
        try:
            spec = parse_spec(spec_path)
        except Exception as exc:
            errors.append(f"{spec_path.relative_to(ROOT)}: {exc}")
            continue

        for field in ("id", "state", "owner", "created_at", "updated_at"):
            if field not in spec:
                errors.append(f"{spec_path.relative_to(ROOT)}: missing metadata field '{field}'")
        if spec.get("state") not in SPEC_STATES:
            errors.append(f"{spec_path.relative_to(ROOT)}: invalid state '{spec.get('state')}'")

    for task_path in find_task_files():
        try:
            task_file = parse_tasks(task_path)
        except Exception as exc:
            errors.append(f"{task_path.relative_to(ROOT)}: {exc}")
            continue

        for field in ("initiative", "spec_id", "owner", "state"):
            if field not in task_file:
                errors.append(f"{task_path.relative_to(ROOT)}: missing metadata field '{field}'")
        if task_file.get("state") not in TASK_STATES:
            errors.append(f"{task_path.relative_to(ROOT)}: invalid state '{task_file.get('state')}'")

        for task in task_file["tasks"]:
            for field in ("id", "title", "state", "owner", "close_criteria"):
                if field not in task:
                    errors.append(f"{task_path.relative_to(ROOT)}: task {task.get('id', '<unknown>')} missing field '{field}'")
            if task.get("state") not in TASK_STATES:
                errors.append(f"{task_path.relative_to(ROOT)}: task {task.get('id')} has invalid state '{task.get('state')}'")

    if errors:
        print("SpecNative validation failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SpecNative validation passed")
    return 0


def export_index() -> dict[str, Any]:
    return {
        "specs": [parse_spec(path) for path in find_specs()],
        "task_files": [parse_tasks(path) for path in find_task_files()],
    }


def export_traceability() -> dict[str, Any]:
    specs = [parse_spec(path) for path in find_specs()]
    task_files = [parse_tasks(path) for path in find_task_files()]
    tasks_by_spec = {task_file.get("spec_id"): task_file for task_file in task_files}

    rows = []
    for spec in specs:
        task_file = tasks_by_spec.get(spec.get("id"))
        rows.append(
            {
                "spec_id": spec.get("id"),
                "spec_state": spec.get("state"),
                "spec_path": spec.get("path"),
                "related_tasks": spec.get("related_tasks", []),
                "related_decisions": spec.get("related_decisions", []),
                "artifacts": spec.get("artifacts", []),
                "validation": spec.get("validation", []),
                "task_file": None if not task_file else task_file.get("path"),
            }
        )
    return {"traceability": rows}


def write_output(payload: dict[str, Any], output: str | None) -> int:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpecNative tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate the repository structure")

    export_index_parser = subparsers.add_parser("export-index", help="Export a machine-readable project index")
    export_index_parser.add_argument("--output", help="Write JSON to a file")

    export_trace_parser = subparsers.add_parser("export-traceability", help="Export traceability data")
    export_trace_parser.add_argument("--output", help="Write JSON to a file")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "validate":
        return validate()
    if args.command == "export-index":
        return write_output(export_index(), args.output)
    if args.command == "export-traceability":
        return write_output(export_traceability(), args.output)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
