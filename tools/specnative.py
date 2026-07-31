#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility when tomli is installed.
    try:
        import tomli as tomllib
    except ModuleNotFoundError as exc:
        raise RuntimeError("TOML parsing requires Python 3.11+ or the 'tomli' package") from exc
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent / "Template-Project-Agents-AI"
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "spec-native/README.md",
    "spec-native/PRODUCT.md",
    "spec-native/ARCHITECTURE.md",
    "spec-native/architecture/README.md",
    "spec-native/STACK.md",
    "spec-native/CONVENTIONS.md",
    "spec-native/conventions/README.md",
    "spec-native/COMMANDS.md",
    "spec-native/DECISIONS.md",
    "spec-native/decisions/README.md",
    "spec-native/ROADMAP.md",
    "spec-native/TRACEABILITY.md",
    "spec-native/SESSION.md",
    ".specnative/SCHEMA.md",
    "spec-native/tasks/README.md",
    "spec-native/workflows/README.md",
    "spec-native/pipelines/README.md",
]
SPEC_STATES = {"draft", "active", "blocked", "done", "superseded"}
TASK_STATES = {"todo", "in_progress", "blocked", "done"}
TASK_PRIORITIES = {"p0", "p1", "p2", "p3"}
BOARD_COLUMNS = ("ready", "in_progress", "blocked", "waiting", "done")
DEFAULT_GITHUB_PROJECT_CONFIG = ".specnative/integrations/github-project.toml"
INSTALL_BRANCH_PREFIX = "specnative/install"

INSTALL_PATHS_MINIMAL = [
    "AGENTS.md",
    "spec-native/README.md",
    "spec-native/PRODUCT.md",
    "spec-native/ARCHITECTURE.md",
    "spec-native/architecture/README.md",
    "spec-native/STACK.md",
    "spec-native/CONVENTIONS.md",
    "spec-native/conventions/README.md",
    "spec-native/COMMANDS.md",
    "spec-native/DECISIONS.md",
    "spec-native/decisions/README.md",
    "spec-native/ROADMAP.md",
    "spec-native/TRACEABILITY.md",
    "spec-native/SESSION.md",
    "spec-native/specs/README.md",
    "spec-native/tasks/README.md",
    "spec-native/backlog/README.md",
    "spec-native/tasks/TASKS.template.md",
    "spec-native/workflows/README.md",
    "spec-native/workflows/IMPLEMENTATION.md",
    "spec-native/workflows/PLANNING.md",
    "spec-native/workflows/REVIEW.md",
    "spec-native/pipelines/README.md",
    "spec-native/pipelines/CI.md",
    "spec-native/pipelines/CD.md",
    ".specnative/README.md",
    ".specnative/CLI.md",
    ".specnative/SCHEMA.md",
    ".specnative/archetypes/README.md",
    ".specnative/templates/README.md",
    ".specnative/templates/specs/README.md",
    ".specnative/templates/decisions/README.md",
    ".claude/commands/spec-backlog-add.md",
    ".claude/skills/specnative-workflow/SKILL.md",
    ".codex/skills/specnative-workflow/SKILL.md",
]

INSTALL_PATHS_EXAMPLES = [
    "spec-native/specs/authentication/README.md",
    "spec-native/specs/authentication/SPEC.md",
    "spec-native/tasks/authentication/README.md",
    "spec-native/tasks/authentication/TASKS.md",
]


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_toml_block(text: str) -> dict[str, Any]:
    match = re.search(r"```toml\n(.*?)\n```", text, flags=re.DOTALL)
    if not match:
        match = re.search(r"^\+\+\+\n(.*?)\n\+\+\+", text, flags=re.DOTALL | re.MULTILINE)
    if not match:
        return {}
    return parse_simple_toml(match.group(1))


def parse_simple_toml(raw: str) -> dict[str, Any]:
    try:
        parsed = tomllib.loads(raw)
    except Exception as exc:
        raise ValueError(f"invalid TOML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("TOML metadata must be an object")
    return parsed


def parse_toml_value(raw: str) -> Any:
    return parse_simple_toml(f"value = {raw}")["value"]


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
        metadata = toml_blocks[0] if toml_blocks else {}
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
    return sorted(ROOT.glob("spec-native/specs/**/SPEC.md")) + (
        [ROOT / "spec-native/SPEC.md"] if (ROOT / "spec-native/SPEC.md").exists() else []
    )


def find_task_files() -> list[Path]:
    return sorted(ROOT.glob("spec-native/tasks/**/TASKS.md"))


def find_decision_files() -> list[Path]:
    return sorted(ROOT.glob("spec-native/decisions/DEC-*.md"))


def find_context_artifacts(directory: str, prefix: str) -> list[Path]:
    return sorted(ROOT.glob(f"spec-native/{directory}/{prefix}-*.md"))


def collect_tasks() -> list[dict[str, Any]]:
    """Return normalized task records used by every derived work-management view."""
    tasks: list[dict[str, Any]] = []
    for task_path in find_task_files():
        task_file = parse_tasks(task_path)
        initiative = task_file.get("initiative") or task_path.parent.name
        for task in task_file.get("tasks", []):
            if not task.get("id"):
                continue
            record = dict(task)
            record.update(
                {
                    "initiative": initiative,
                    "spec_id": task_file.get("spec_id"),
                    "task_file": task_file.get("path"),
                    "priority": task.get("priority", "p2"),
                    "labels": task.get("labels", []),
                }
            )
            tasks.append(record)
    return tasks


def build_board() -> dict[str, Any]:
    """Build a deterministic delivery-board projection from canonical task files."""
    tasks = collect_tasks()
    tasks_by_id = {task["id"]: task for task in tasks}
    columns: dict[str, list[dict[str, Any]]] = {column: [] for column in BOARD_COLUMNS}

    for task in tasks:
        state = task.get("state", "todo")
        dependencies = task.get("dependencies", [])
        dependencies_done = all(
            tasks_by_id.get(dependency, {}).get("state") == "done"
            for dependency in dependencies
        )

        if state == "todo":
            column = "ready" if dependencies_done else "waiting"
        elif state in {"in_progress", "blocked", "done"}:
            column = state
        else:
            column = "waiting"

        completion_evidence = task.get("completion_evidence", [])
        columns[column].append(
            {
                "id": task["id"],
                "title": task.get("title", ""),
                "initiative": task["initiative"],
                "spec_id": task.get("spec_id"),
                "state": state,
                "board_column": column,
                "priority": task["priority"],
                "owner": task.get("owner", ""),
                "labels": task["labels"],
                "dependencies": dependencies,
                "expected_files": task.get("expected_files", []),
                "close_criteria": task.get("close_criteria", ""),
                "validation": task.get("validation", []),
                "completion_evidence": completion_evidence,
                "completion_evidence_missing": state == "done" and not completion_evidence,
                "task_file": task["task_file"],
            }
        )

    priority_order = {priority: index for index, priority in enumerate(sorted(TASK_PRIORITIES))}
    for tasks_in_column in columns.values():
        tasks_in_column.sort(key=lambda task: (priority_order.get(task["priority"], 99), task["id"]))

    return {
        "schema_version": "1.0",
        "source_of_truth": "spec-native/tasks/**/TASKS.md",
        "columns": columns,
    }


def render_board_markdown(board: dict[str, Any]) -> str:
    labels = {
        "ready": "Ready",
        "in_progress": "In progress",
        "blocked": "Blocked",
        "waiting": "Waiting for dependencies",
        "done": "Done",
    }
    lines = [
        "# SpecNative Delivery Board",
        "",
        "> Generated projection. Update task TOML metadata, never this view.",
    ]
    for column in BOARD_COLUMNS:
        tasks = board["columns"][column]
        lines.extend(["", f"## {labels[column]} ({len(tasks)})", ""])
        if not tasks:
            lines.append("No tasks.")
            continue
        lines.extend([
            "| Priority | Task | Initiative | Owner | Dependencies |",
            "|---|---|---|---|---|",
        ])
        for task in tasks:
            dependencies = ", ".join(task["dependencies"]) or "-"
            lines.append(
                f"| {task['priority']} | {task['id']} - {task['title']} | "
                f"{task['initiative']} | {task['owner'] or '-'} | {dependencies} |"
            )
    return "\n".join(lines) + "\n"


def render_board_mermaid(board: dict[str, Any]) -> str:
    """Render a stable overview; Mermaid is intentionally not an editable board."""
    labels = {
        "ready": "Ready",
        "in_progress": "In progress",
        "blocked": "Blocked",
        "waiting": "Waiting",
        "done": "Done",
    }
    lines = ["flowchart LR"]
    for index, column in enumerate(BOARD_COLUMNS):
        node = f"C{index}"
        lines.append(f'    {node}["{labels[column]} ({len(board["columns"][column])})"]')
        if index:
            lines.append(f"    C{index - 1} --> {node}")
    return "\n".join(lines) + "\n"


def load_github_project_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise ValueError(
            f"GitHub Project configuration not found: {config_path}. "
            "Copy .specnative/integrations/github-project.toml.example first."
        )
    config = parse_simple_toml(load_text(config_path))
    project = config.get("github_project", {})
    status_map = config.get("status_map", {})
    if not isinstance(project, dict) or not project.get("project_id"):
        raise ValueError("github_project.project_id is required")
    if not isinstance(status_map, dict):
        raise ValueError("status_map must be a TOML table")
    missing = [column for column in BOARD_COLUMNS if not status_map.get(column)]
    if missing:
        raise ValueError(f"status_map is missing board columns: {', '.join(missing)}")
    return config


def github_project_plan(config_path: Path) -> dict[str, Any]:
    """Create a no-side-effect plan for a future GitHub Projects export."""
    config = load_github_project_config(config_path)
    project = config["github_project"]
    status_map = config["status_map"]
    board = build_board()
    items: list[dict[str, Any]] = []
    for column in BOARD_COLUMNS:
        for task in board["columns"][column]:
            items.append(
                {
                    "operation": "upsert_draft_item",
                    "external_key": task["id"],
                    "title": f"{task['id']} - {task['title']}",
                    "status": status_map[column],
                    "fields": {
                        "SpecNative ID": task["id"],
                        "Initiative": task["initiative"],
                        "Priority": task["priority"],
                        "Owner": task["owner"],
                    },
                    "source": task["task_file"],
                }
            )
    return {
        "schema_version": "1.0",
        "mode": "dry_run",
        "project": {
            "project_id": project["project_id"],
            "owner": project.get("owner"),
            "status_field": project.get("status_field", "Status"),
        },
        "items": items,
        "notes": [
            "This command does not call GitHub.",
            "SpecNative task files remain the source of truth.",
            "An apply command requires an explicit future integration release.",
        ],
    }


def validate() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    specs = find_specs()
    if not specs:
        errors.append("missing required spec: spec-native/SPEC.md or spec-native/specs/**/SPEC.md")

    parsed_specs: list[dict[str, Any]] = []
    for spec_path in specs:
        try:
            spec = parse_spec(spec_path)
        except Exception as exc:
            errors.append(f"{spec_path.relative_to(ROOT)}: {exc}")
            continue

        # validate TOML fields only when a TOML block is present
        if spec.get("artifact_type") == "spec":
            for field in ("id", "state", "owner", "created_at", "updated_at"):
                if field not in spec:
                    errors.append(f"{spec_path.relative_to(ROOT)}: missing metadata field '{field}'")
            if spec.get("state") not in SPEC_STATES:
                errors.append(f"{spec_path.relative_to(ROOT)}: invalid state '{spec.get('state')}'")
        parsed_specs.append(spec)

    spec_ids = {spec.get("id") for spec in parsed_specs if spec.get("id")}
    all_task_ids: set[str] = set()
    all_tasks: list[tuple[Path, dict[str, Any]]] = []
    decision_ids: set[str] = set()
    for decision_path in find_decision_files():
        try:
            decision_meta = extract_toml_block(load_text(decision_path))
        except Exception as exc:
            errors.append(f"{decision_path.relative_to(ROOT)}: {exc}")
            continue
        for field in ("doctype", "id", "title", "status", "created_at", "tags"):
            if field not in decision_meta:
                errors.append(f"{decision_path.relative_to(ROOT)}: missing metadata field '{field}'")
        if decision_meta.get("doctype") != "decision":
            errors.append(f"{decision_path.relative_to(ROOT)}: doctype must be 'decision'")
        if decision_meta.get("id") in decision_ids:
            errors.append(f"{decision_path.relative_to(ROOT)}: duplicate decision id '{decision_meta.get('id')}'")
        decision_ids.add(decision_meta.get("id"))
        if not isinstance(decision_meta.get("tags", []), list):
            errors.append(f"{decision_path.relative_to(ROOT)}: tags must be a list")

    for directory, prefix, doctype in (("architecture", "ARCH", "architecture"), ("conventions", "CONV", "convention")):
        artifact_ids: set[str] = set()
        for artifact_path in find_context_artifacts(directory, prefix):
            try:
                meta = extract_toml_block(load_text(artifact_path))
            except Exception as exc:
                errors.append(f"{artifact_path.relative_to(ROOT)}: {exc}")
                continue
            for field in ("doctype", "id", "title", "status", "tags"):
                if field not in meta:
                    errors.append(f"{artifact_path.relative_to(ROOT)}: missing metadata field '{field}'")
            if meta.get("doctype") != doctype:
                errors.append(f"{artifact_path.relative_to(ROOT)}: doctype must be '{doctype}'")
            if meta.get("id") in artifact_ids:
                errors.append(f"{artifact_path.relative_to(ROOT)}: duplicate id '{meta.get('id')}'")
            artifact_ids.add(meta.get("id"))

    for task_path in find_task_files():
        try:
            task_file = parse_tasks(task_path)
        except Exception as exc:
            errors.append(f"{task_path.relative_to(ROOT)}: {exc}")
            continue

        if task_file.get("artifact_type") == "task_file":
            for field in ("initiative", "spec_id", "owner", "state"):
                if field not in task_file:
                    errors.append(f"{task_path.relative_to(ROOT)}: missing metadata field '{field}'")
            if task_file.get("state") not in TASK_STATES:
                errors.append(f"{task_path.relative_to(ROOT)}: invalid state '{task_file.get('state')}'")
            if task_file.get("spec_id") not in spec_ids:
                errors.append(
                    f"{task_path.relative_to(ROOT)}: spec_id '{task_file.get('spec_id')}' does not reference an existing spec"
                )

        task_ids: set[str] = set()
        for task in task_file["tasks"]:
            task_id = task.get("id")
            if task_id in task_ids:
                errors.append(f"{task_path.relative_to(ROOT)}: duplicate task id '{task_id}'")
            if task_id:
                task_ids.add(task_id)
                if task_id in all_task_ids:
                    errors.append(f"{task_path.relative_to(ROOT)}: task id '{task_id}' is not globally unique")
                all_task_ids.add(task_id)
                all_tasks.append((task_path, task))
            if task_file.get("artifact_type") == "task_file":
                for field in ("id", "title", "state", "owner", "close_criteria", "validation"):
                    if field not in task:
                        errors.append(
                            f"{task_path.relative_to(ROOT)}: task {task_id or '<unknown>'} missing field '{field}'"
                        )
            if task.get("state") and task["state"] not in TASK_STATES:
                errors.append(f"{task_path.relative_to(ROOT)}: task {task.get('id')} has invalid state '{task['state']}'")
            priority = task.get("priority", "p2")
            if priority not in TASK_PRIORITIES:
                errors.append(f"{task_path.relative_to(ROOT)}: task {task_id} has invalid priority '{priority}'")
            labels = task.get("labels", [])
            if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
                errors.append(f"{task_path.relative_to(ROOT)}: task {task_id} labels must be a list of strings")
            if task.get("state") == "done" and not task.get("completion_evidence"):
                errors.append(
                    f"{task_path.relative_to(ROOT)}: task {task_id} is done but has no completion_evidence"
                )

        if task_file.get("state") == "done" and any(
            task.get("state") != "done" for task in task_file["tasks"]
        ):
            errors.append(f"{task_path.relative_to(ROOT)}: task file is done but not all tasks are done")

    for task_path, task in all_tasks:
        for dependency in task.get("dependencies", []):
            if dependency not in all_task_ids:
                errors.append(
                    f"{task_path.relative_to(ROOT)}: task {task.get('id')} depends on missing task '{dependency}'"
                )
            if dependency == task.get("id"):
                errors.append(f"{task_path.relative_to(ROOT)}: task {task.get('id')} cannot depend on itself")

    for spec in parsed_specs:
        if spec.get("state") == "done":
            linked = [task_file for task_file in find_task_files() if parse_tasks(task_file).get("spec_id") == spec.get("id")]
            if linked and any(
                task.get("state") != "done"
                for task_file in linked
                for task in task_file.get("tasks", [])
            ):
                errors.append(f"spec {spec.get('id')}: state is done but linked tasks are not all done")

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


def status() -> int:
    specs = find_specs()
    task_files = find_task_files()
    tasks_by_spec = {tf.get("spec_id"): tf for tf in [parse_tasks(p) for p in task_files]}

    lines: list[str] = ["SpecNative status\n"]

    if not specs:
        lines.append("  no specs found\n")
    else:
        for spec_path in specs:
            spec = parse_spec(spec_path)
            spec_id = spec.get("id") or str(spec_path.relative_to(ROOT))
            spec_state = spec.get("state", "unknown")
            lines.append(f"  spec  {spec_id:<20} [{spec_state}]")

            task_file = tasks_by_spec.get(spec.get("id"))
            if not task_file:
                lines.append("        no task file linked")
            else:
                tasks = task_file.get("tasks", [])
                counts: dict[str, int] = {}
                for t in tasks:
                    s = t.get("state", "unknown")
                    counts[s] = counts.get(s, 0) + 1
                summary = "  ".join(f"{s}:{n}" for s, n in sorted(counts.items()))
                lines.append(f"        tasks: {summary}" if summary else "        no tasks")

    print("\n".join(lines))
    return 0


def write_output(payload: dict[str, Any], output: str | None) -> int:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_git_repo(target: Path) -> None:
    if not target.exists():
        raise ValueError(f"target does not exist: {target}")
    try:
        result = run_git(["rev-parse", "--is-inside-work-tree"], cwd=target)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"target is not a git repository: {target}\n{exc.stderr.strip()}") from exc
    if result.stdout.strip() != "true":
        raise ValueError(f"target is not a git repository: {target}")


def ensure_clean_worktree(target: Path) -> None:
    result = run_git(["status", "--porcelain"], cwd=target)
    if result.stdout.strip():
        raise ValueError("target repository has uncommitted changes")


def create_branch(target: Path, branch: str) -> None:
    existing = run_git(["branch", "--list", branch], cwd=target)
    if existing.stdout.strip():
        raise ValueError(f"branch already exists in target repository: {branch}")
    run_git(["checkout", "-b", branch], cwd=target)


def copy_file(source_root: Path, target_root: Path, relative: str, force: bool, created: list[str], skipped: list[str]) -> None:
    source = source_root / relative
    target = target_root / relative

    if not source.exists():
        raise ValueError(f"installer source path does not exist: {relative}")

    if target.exists() and not force:
        skipped.append(relative)
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    created.append(relative)


def install_template(target: Path, profile: str, include_examples: bool, branch: str, force: bool) -> int:
    ensure_git_repo(target)
    ensure_clean_worktree(target)
    create_branch(target, branch)

    selected_paths = list(INSTALL_PATHS_MINIMAL)
    if profile == "full":
        selected_paths.append("README.md")
    if include_examples:
        selected_paths.extend(INSTALL_PATHS_EXAMPLES)

    created: list[str] = []
    skipped: list[str] = []

    for relative in selected_paths:
        if relative == "README.md" and (target / "README.md").exists() and not force:
            skipped.append(relative)
            continue
        copy_file(ROOT, target, relative, force=force, created=created, skipped=skipped)

    summary = {
        "target": str(target),
        "branch": branch,
        "profile": profile,
        "include_examples": include_examples,
        "created_or_overwritten": created,
        "skipped_existing": skipped,
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
# Init — interactive wizard
# ---------------------------------------------------------------------------

_INIT_QUESTIONS: list[tuple[str, str, str]] = [
    # (document, section_title, question)
    ("product",      "Problema",    "¿Qué problema principal resuelve este proyecto?"),
    ("product",      "Usuarios",    "¿Para quién lo construyes? ¿Cuál es su dolor principal?"),
    ("product",      "Objetivos",   "¿Cuál es el objetivo concreto y medible de éxito?"),
    ("product",      "No objetivos","¿Qué queda explícitamente fuera del alcance?"),
    ("stack",        "Stack",       "¿Qué lenguajes, frameworks y base de datos usan?"),
    ("stack",        "Restricciones","¿Restricciones de versión o dependencias clave?"),
    ("architecture", "Modulos",     "¿Cuáles son los módulos o componentes principales?"),
    ("architecture", "Limites",     "¿Hay límites o fronteras importantes entre módulos?"),
    ("conventions",  "Codigo",      "¿Convenciones de naming y estructura de carpetas?"),
    ("conventions",  "Testing",     "¿Política de testing? ¿Cobertura esperada?"),
    ("conventions",  "Commits",     "¿Convención para commits y PRs?"),
    ("commands",     "Setup",       "¿Cómo se instalan las dependencias?"),
    ("commands",     "Desarrollo",  "¿Cómo se corre el proyecto en local?"),
    ("commands",     "Tests",       "¿Cómo se corren los tests?"),
    ("commands",     "Build",       "¿Cómo se hace el build o deploy?"),
]

_DOC_HEADERS: dict[str, str] = {
    "product":      "# PRODUCT.md\n\nFuente de verdad del producto.\n",
    "stack":        "# STACK.md\n\nTecnologías, versiones y restricciones técnicas.\n",
    "architecture": "# ARCHITECTURE.md\n\nEstructura del sistema, módulos y límites.\n",
    "conventions":  "# CONVENTIONS.md\n\nReglas de código, naming, testing y commits.\n",
    "commands":     "# COMMANDS.md\n\nComandos de desarrollo, test, lint y build.\n",
}


def _ask(prompt: str, default: str = "") -> str:
    """Print prompt and return stripped input. Returns default on empty input."""
    hint = f" [{default}]" if default else ""
    try:
        answer = input(f"\n{prompt}{hint}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)
    return answer or default


def _confirm(question: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"\n{question} {hint} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)
    if not answer:
        return default
    return answer.startswith("y")


def init_interactive(target: Path, force: bool) -> int:
    """
    Interactive wizard: ask the developer about their project and fill
    spec-native/ documents with real content.
    """
    sn = target / "spec-native"
    if not sn.exists():
        print(
            f"Error: spec-native/ not found in {target}.\n"
            "Run install.py first to set up the SpecNative structure.",
            file=sys.stderr,
        )
        return 1

    print("\n🟢 SpecNative Init — definamos el contexto base de tu proyecto\n")
    print("Responde cada pregunta. Puedes dejar en blanco para completar más tarde.")

    # Collect answers grouped by document
    answers: dict[str, dict[str, str]] = {
        "product": {}, "stack": {}, "architecture": {}, "conventions": {}, "commands": {}
    }

    for doc, section, question in _INIT_QUESTIONS:
        answers[doc][section] = _ask(question)

    # Write files
    created: list[str] = []
    skipped: list[str] = []

    for doc, sections in answers.items():
        dest = sn / f"{doc.upper()}.md"
        if dest.exists() and not force:
            if not _confirm(f"spec-native/{doc.upper()}.md ya existe. ¿Sobreescribir?", default=False):
                skipped.append(f"spec-native/{doc.upper()}.md")
                continue

        content = _DOC_HEADERS[doc]
        for section, answer in sections.items():
            if answer:
                content += f"\n## {section}\n\n{answer}\n"

        dest.write_text(content, encoding="utf-8")
        created.append(f"spec-native/{doc.upper()}.md")

    print("\n✓ SpecNative Init completado")
    if created:
        print("  Archivos creados/actualizados:")
        for f in created:
            print(f"    {f}")
    if skipped:
        print("  Omitidos (ya existían):")
        for f in skipped:
            print(f"    {f}")

    print(
        "\nPróximos pasos:"
        "\n  1. Conecta el MCP: ver .specnative/MCP.md"
        "\n  2. Refina con:  python3 /path/to/SpecNative-Development/tools/specnative.py update --target ."
        "\n  3. Crea tu primera spec con el prompt start_initiative() del MCP"
    )
    return 0


# ---------------------------------------------------------------------------
# Update — health check + guided refinement
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE_CLI = re.compile(
    r"<!--|\bTemplate\b|^\s*$|\bDescribe\b.*\baqui\b|Tu nombre\b",
    re.IGNORECASE | re.MULTILINE,
)

_REFINE_PROMPTS: dict[str, list[tuple[str, str]]] = {
    "product": [
        ("Problema",    "¿Cómo describirías ahora el problema que resuelve el proyecto?"),
        ("Usuarios",    "¿Ha cambiado tu comprensión de los usuarios o su dolor principal?"),
        ("Objetivos",   "¿Cuál es el objetivo medible de éxito hoy?"),
        ("No objetivos","¿Qué queda fuera del alcance?"),
    ],
    "stack": [
        ("Stack",          "¿Qué tecnologías, versiones y base de datos usan actualmente?"),
        ("Restricciones",  "¿Restricciones de versión o dependencias clave nuevas?"),
    ],
    "architecture": [
        ("Modulos",  "¿Cuáles son los módulos principales hoy?"),
        ("Limites",  "¿Hay límites o reglas entre módulos que deban documentarse?"),
    ],
    "conventions": [
        ("Codigo",   "¿Convenciones de naming y estructura de carpetas vigentes?"),
        ("Testing",  "¿Política de testing actual?"),
        ("Commits",  "¿Convención de commits y PRs?"),
    ],
    "commands": [
        ("Setup",       "Comando para instalar dependencias:"),
        ("Desarrollo",  "Comando para correr el proyecto en local:"),
        ("Tests",       "Comando para correr tests:"),
        ("Build",       "Comando de build o deploy:"),
    ],
    "roadmap": [
        ("Ahora",         "¿Qué iniciativas están activas ahora mismo?"),
        ("Después",       "¿Cuáles son las siguientes prioridades?"),
        ("Más adelante",  "¿Qué apuestas de largo plazo hay?"),
        ("No por ahora",  "¿Qué se ha descartado temporalmente?"),
    ],
}


def _doc_is_empty_cli(path: Path) -> bool:
    if not path.exists():
        return True
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 80:
        return True
    real = [ln for ln in text.splitlines() if ln.strip() and not _PLACEHOLDER_RE_CLI.search(ln)]
    return len(real) < 5


def update_interactive(target: Path, doc: str | None) -> int:
    """
    Detect documentation gaps and guide the developer to refine them.
    Without --doc: shows health check and asks what to update.
    With --doc: refines that specific document.
    """
    sn = target / "spec-native"
    if not sn.exists():
        print(
            f"Error: spec-native/ not found in {target}.\n"
            "Run install.py first.",
            file=sys.stderr,
        )
        return 1

    print("\n🟡 SpecNative Update\n")

    docs_to_check = [
        ("product",      "PRODUCT.md"),
        ("stack",        "STACK.md"),
        ("architecture", "ARCHITECTURE.md"),
        ("conventions",  "CONVENTIONS.md"),
        ("commands",     "COMMANDS.md"),
        ("roadmap",      "ROADMAP.md"),
    ]

    if doc:
        # Refine a single document
        target_docs = [(d, f) for d, f in docs_to_check if d == doc.lower()]
        if not target_docs:
            print(
                f"Unknown document '{doc}'. "
                f"Valid: {', '.join(d for d, _ in docs_to_check)}",
                file=sys.stderr,
            )
            return 1
    else:
        # Health check first
        empty = [(d, f) for d, f in docs_to_check if _doc_is_empty_cli(sn / f)]
        filled = [(d, f) for d, f in docs_to_check if not _doc_is_empty_cli(sn / f)]

        print("Estado de la documentación:")
        for d, f in filled:
            print(f"  ✓  spec-native/{f}")
        for d, f in empty:
            print(f"  ⚠  spec-native/{f}  (vacío o incompleto)")

        if not empty:
            print("\n✓ Todos los documentos core tienen contenido.")
            choice = _ask(
                "¿Qué quieres actualizar?\n"
                "  1) Un documento específico\n"
                "  2) El ROADMAP\n"
                "  3) Nada por ahora (salir)\n"
                "Elige (1/2/3)",
                default="3",
            )
            if choice == "3":
                return 0
            elif choice == "2":
                doc = "roadmap"
                target_docs = [("roadmap", "ROADMAP.md")]
            else:
                doc_name = _ask(
                    "¿Qué documento quieres actualizar? "
                    "(product, stack, architecture, conventions, commands, roadmap)"
                )
                target_docs = [(d, f) for d, f in docs_to_check if d == doc_name.lower()]
                if not target_docs:
                    print(f"Documento '{doc_name}' no reconocido.", file=sys.stderr)
                    return 1
        else:
            print(f"\n{len(empty)} documento(s) con vacíos.")
            choice = _ask(
                "¿Qué quieres hacer?\n"
                "  1) Llenar los vacíos detectados\n"
                "  2) Actualizar un documento específico\n"
                "  3) Salir\n"
                "Elige (1/2/3)",
                default="1",
            )
            if choice == "3":
                return 0
            elif choice == "2":
                doc_name = _ask(
                    "¿Qué documento? "
                    "(product, stack, architecture, conventions, commands, roadmap)"
                )
                target_docs = [(d, f) for d, f in docs_to_check if d == doc_name.lower()]
                if not target_docs:
                    print(f"Documento '{doc_name}' no reconocido.", file=sys.stderr)
                    return 1
            else:
                target_docs = empty

    updated: list[str] = []
    for doc_key, filename in target_docs:
        path = sn / filename
        questions = _REFINE_PROMPTS.get(doc_key, [])
        if not questions:
            continue

        print(f"\n── {filename} ──")
        if path.exists():
            print(path.read_text(encoding="utf-8")[:400].rstrip())
            print("  …")

        sections: dict[str, str] = {}
        for section, question in questions:
            answer = _ask(question)
            if answer:
                sections[section] = answer

        if not sections:
            print(f"  Omitido (sin respuestas).")
            continue

        header = _DOC_HEADERS.get(doc_key, f"# {filename}\n\n")
        if doc_key == "roadmap":
            header = "# ROADMAP.md\n\nDirección y prioridades del proyecto.\n"

        content = header
        for section, answer in sections.items():
            content += f"\n## {section}\n\n{answer}\n"

        path.write_text(content, encoding="utf-8")
        updated.append(f"spec-native/{filename}")

    if updated:
        print("\n✓ Documentos actualizados:")
        for f in updated:
            print(f"  {f}")
    else:
        print("\nNada actualizado.")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpecNative tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate the repository structure")
    validate_parser.add_argument("--target", help="Repository to validate")

    status_parser = subparsers.add_parser("status", help="Show current state of specs and tasks")
    status_parser.add_argument("--target", help="Repository to inspect")

    export_index_parser = subparsers.add_parser("export-index", help="Export a machine-readable project index")
    export_index_parser.add_argument("--output", help="Write JSON to a file")
    export_index_parser.add_argument("--target", help="Repository to export")

    export_trace_parser = subparsers.add_parser("export-traceability", help="Export traceability data")
    export_trace_parser.add_argument("--output", help="Write JSON to a file")
    export_trace_parser.add_argument("--target", help="Repository to export")

    board_parser = subparsers.add_parser("board", help="Generate a derived delivery-board view")
    board_parser.add_argument("--target", help="Repository to inspect")
    board_parser.add_argument("--output", help="Write output to a file")
    board_parser.add_argument(
        "--format", choices=("json", "markdown", "mermaid"), default="markdown", help="Output format"
    )

    github_parser = subparsers.add_parser(
        "github-project", help="Create safe GitHub Projects export plans"
    )
    github_subparsers = github_parser.add_subparsers(dest="github_command", required=True)
    github_plan_parser = github_subparsers.add_parser("plan", help="Create a no-side-effect export plan")
    github_plan_parser.add_argument("--target", default=".", help="Repository to inspect")
    github_plan_parser.add_argument("--config", help="GitHub Project TOML configuration path")
    github_plan_parser.add_argument("--output", help="Write JSON to a file")

    install_parser = subparsers.add_parser("install", help="Install SpecNative into an existing repository")
    install_parser.add_argument("--target", required=True, help="Target repository path")
    install_parser.add_argument(
        "--profile",
        choices=("minimal", "full"),
        default="minimal",
        help="Installation profile.",
    )
    install_parser.add_argument("--include-examples", action="store_true")
    install_parser.add_argument("--branch", default=f"{INSTALL_BRANCH_PREFIX}-v0.6")
    install_parser.add_argument("--force", action="store_true")

    init_parser = subparsers.add_parser(
        "init",
        help="Interactive wizard to fill spec-native/ documents with real project content",
    )
    init_parser.add_argument(
        "--target", default=".", help="Path to the repository (default: current directory)"
    )
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing documents"
    )

    update_parser = subparsers.add_parser(
        "update",
        help="Detect documentation gaps and guide iterative refinement",
    )
    update_parser.add_argument(
        "--target", default=".", help="Path to the repository (default: current directory)"
    )
    update_parser.add_argument(
        "--doc",
        default=None,
        help="Refine a specific document: product, stack, architecture, conventions, commands, roadmap",
    )

    return parser


def main() -> int:
    global ROOT

    parser = build_parser()
    args = parser.parse_args()

    if args.command in {"validate", "status", "export-index", "export-traceability", "board"} and args.target:
        ROOT = Path(args.target).resolve()

    if args.command == "validate":
        return validate()
    if args.command == "status":
        return status()
    if args.command == "export-index":
        return write_output(export_index(), args.output)
    if args.command == "export-traceability":
        return write_output(export_traceability(), args.output)
    if args.command == "board":
        board = build_board()
        if args.format == "markdown":
            payload = render_board_markdown(board)
        elif args.format == "mermaid":
            payload = render_board_mermaid(board)
        else:
            payload = json.dumps(board, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 0
    if args.command == "github-project":
        ROOT = Path(args.target).resolve()
        config_path = Path(args.config).resolve() if args.config else ROOT / DEFAULT_GITHUB_PROJECT_CONFIG
        try:
            return write_output(github_project_plan(config_path), args.output)
        except ValueError as exc:
            print(f"GitHub Project plan failed: {exc}", file=sys.stderr)
            return 1
    if args.command == "install":
        try:
            return install_template(
                target=Path(args.target).resolve(),
                profile=args.profile,
                include_examples=args.include_examples,
                branch=args.branch,
                force=args.force,
            )
        except ValueError as exc:
            print(f"Install failed: {exc}", file=sys.stderr)
            return 1
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            print(f"Install failed: {stderr}", file=sys.stderr)
            return 1
    if args.command == "init":
        return init_interactive(Path(args.target).resolve(), args.force)
    if args.command == "update":
        return update_interactive(Path(args.target).resolve(), args.doc)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
