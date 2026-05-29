#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent / "Template-Project-Agents-AI"
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "spec-native/README.md",
    "spec-native/PRODUCT.md",
    "spec-native/ARCHITECTURE.md",
    "spec-native/STACK.md",
    "spec-native/CONVENTIONS.md",
    "spec-native/COMMANDS.md",
    "spec-native/DECISIONS.md",
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
INSTALL_BRANCH_PREFIX = "specnative/install"

INSTALL_PATHS_MINIMAL = [
    "AGENTS.md",
    "spec-native/README.md",
    "spec-native/PRODUCT.md",
    "spec-native/ARCHITECTURE.md",
    "spec-native/STACK.md",
    "spec-native/CONVENTIONS.md",
    "spec-native/COMMANDS.md",
    "spec-native/DECISIONS.md",
    "spec-native/ROADMAP.md",
    "spec-native/TRACEABILITY.md",
    "spec-native/SESSION.md",
    "spec-native/specs/README.md",
    "spec-native/tasks/README.md",
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
        return {}
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


def validate() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    specs = find_specs()
    if not specs:
        errors.append("missing required spec: spec-native/SPEC.md or spec-native/specs/**/SPEC.md")

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

        for task in task_file["tasks"]:
            if task.get("state") and task["state"] not in TASK_STATES:
                errors.append(f"{task_path.relative_to(ROOT)}: task {task.get('id')} has invalid state '{task['state']}'")

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
        "\n  2. Refina con:  python3 specnative.py update --target ."
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

    subparsers.add_parser("validate", help="Validate the repository structure")
    subparsers.add_parser("status", help="Show current state of specs and tasks")

    export_index_parser = subparsers.add_parser("export-index", help="Export a machine-readable project index")
    export_index_parser.add_argument("--output", help="Write JSON to a file")

    export_trace_parser = subparsers.add_parser("export-traceability", help="Export traceability data")
    export_trace_parser.add_argument("--output", help="Write JSON to a file")

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
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "validate":
        return validate()
    if args.command == "status":
        return status()
    if args.command == "export-index":
        return write_output(export_index(), args.output)
    if args.command == "export-traceability":
        return write_output(export_traceability(), args.output)
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
