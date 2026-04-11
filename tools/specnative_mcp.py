#!/usr/bin/env python3
"""
SpecNative MCP Server — v0.4

Exposes a SpecNative repository as MCP resources, tools, and prompts so any
MCP-compatible agent (Claude Desktop, Claude Code, OpenCode, etc.) can work
spec-first without manually navigating the file tree.

Resources  — read repository context documents by URI
Tools      — validate, status, list specs/tasks, read, export
Prompts    — structured workflow starters (start initiative, plan tasks, etc.)

Usage:
    # stdio transport (default — for Claude Desktop, Claude Code, OpenCode)
    python3 specnative_mcp.py --repo /path/to/project

    # SSE transport (for remote/web agents)
    python3 specnative_mcp.py --repo /path/to/project --transport sse --port 8765

    # Use SPECNATIVE_REPO env var instead of --repo
    SPECNATIVE_REPO=/path/to/project python3 specnative_mcp.py

Requirements:
    pip install mcp
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

try:
    from mcp.server.fastmcp import FastMCP

VERSION = "dev"  # replaced by CI on release
except ImportError:
    sys.exit(
        "mcp package not found.\n"
        "Install with:  pip install mcp\n"
        "Then retry:    python3 specnative_mcp.py --repo /path/to/project\n"
    )

# ---------------------------------------------------------------------------
# Configuration — resolved before FastMCP initialises
# ---------------------------------------------------------------------------

_parser = argparse.ArgumentParser(
    description="SpecNative MCP server",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
_parser.add_argument(
    "--repo",
    default=os.environ.get("SPECNATIVE_REPO", "."),
    help="Path to the SpecNative repository root (default: $SPECNATIVE_REPO or cwd)",
)
_parser.add_argument(
    "--transport",
    default="stdio",
    choices=["stdio", "sse"],
    help="MCP transport: stdio (default) or sse",
)
_parser.add_argument(
    "--port",
    type=int,
    default=8765,
    help="Port for SSE transport (default: 8765)",
)
_ARGS, _ = _parser.parse_known_args()
REPO = Path(_ARGS.repo).resolve()

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "specnative",
    instructions=(
        f"SpecNative repository at {REPO}. "
        "Read AGENTS.md first, then navigate via README.md files. "
        "Load only the minimum context needed for the current task."
    ),
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    """Return file contents or a clear placeholder when the file is absent."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"(file not found: {path.relative_to(REPO) if REPO in path.parents else path})"


def _find_specs() -> list[Path]:
    return sorted(
        p for p in REPO.rglob("SPEC.md") if ".specnative" not in p.parts
    )


def _find_task_files() -> list[Path]:
    tasks_dir = REPO / "tasks"
    return sorted(tasks_dir.rglob("TASKS.md")) if tasks_dir.exists() else []


def _toml_loads(text: str) -> dict[str, Any]:
    """Parse the first ```toml block in *text*, return {} on any failure."""
    match = re.search(r"```toml\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return {}
    raw = match.group(1)
    try:
        import tomllib          # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # backport
        except ImportError:
            # Minimal hand-rolled parser for the simple key = "value" / list cases
            result: dict[str, Any] = {}
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    v = v.strip()
                    if v.startswith('"') and v.endswith('"'):
                        result[k.strip()] = v[1:-1]
                    elif v.startswith("["):
                        result[k.strip()] = re.findall(r'"([^"]+)"', v)
                    else:
                        result[k.strip()] = v
            return result
    try:
        return tomllib.loads(raw)
    except Exception:
        return {}


def _task_state_summary(task_file: Path) -> str:
    text = task_file.read_text(encoding="utf-8")
    states = re.findall(r'\bstate\s*=\s*"([^"]+)"', text)
    if not states:
        return "(no TOML task states found)"
    counts: dict[str, int] = {}
    for s in states:
        counts[s] = counts.get(s, 0) + 1
    return "  ".join(f"{s}:{n}" for s, n in sorted(counts.items()))


# ---------------------------------------------------------------------------
# Resources — repository context documents
# ---------------------------------------------------------------------------

@mcp.resource("spec://agents")
def resource_agents_contract() -> str:
    """AGENTS.md — agent operating contract. Read this first."""
    return _read(REPO / "AGENTS.md")


@mcp.resource("spec://context/product")
def resource_product() -> str:
    """PRODUCT.md — problem, users, goals (permanent)."""
    return _read(REPO / "agents" / "PRODUCT.md")


@mcp.resource("spec://context/architecture")
def resource_architecture() -> str:
    """ARCHITECTURE.md — system structure, boundaries, constraints."""
    return _read(REPO / "agents" / "ARCHITECTURE.md")


@mcp.resource("spec://context/stack")
def resource_stack() -> str:
    """STACK.md — tech stack and version constraints."""
    return _read(REPO / "agents" / "STACK.md")


@mcp.resource("spec://context/conventions")
def resource_conventions() -> str:
    """CONVENTIONS.md — code rules, naming, testing approach."""
    return _read(REPO / "agents" / "CONVENTIONS.md")


@mcp.resource("spec://context/commands")
def resource_commands() -> str:
    """COMMANDS.md — project-specific dev/test/build commands."""
    return _read(REPO / "agents" / "COMMANDS.md")


@mcp.resource("spec://context/decisions")
def resource_decisions() -> str:
    """DECISIONS.md — persistent decisions and trade-offs."""
    return _read(REPO / "agents" / "DECISIONS.md")


@mcp.resource("spec://context/roadmap")
def resource_roadmap() -> str:
    """ROADMAP.md — temporal direction and priorities."""
    return _read(REPO / "agents" / "ROADMAP.md")


@mcp.resource("spec://context/traceability")
def resource_traceability() -> str:
    """TRACEABILITY.md — cross-artifact links (update when initiative closes)."""
    return _read(REPO / "agents" / "TRACEABILITY.md")


@mcp.resource("spec://context/spec")
def resource_spec_main() -> str:
    """agents/SPEC.md — active or general spec entry point."""
    return _read(REPO / "agents" / "SPEC.md")


@mcp.resource("spec://pipelines/ci")
def resource_ci() -> str:
    """pipelines/CI.md — automated validation gates."""
    return _read(REPO / "pipelines" / "CI.md")


@mcp.resource("spec://pipelines/cd")
def resource_cd() -> str:
    """pipelines/CD.md — delivery process and environments."""
    return _read(REPO / "pipelines" / "CD.md")


@mcp.resource("spec://schema")
def resource_schema() -> str:
    """.specnative/SCHEMA.md — framework contract (required files, states, ownership)."""
    return _read(REPO / ".specnative" / "SCHEMA.md")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def status() -> str:
    """
    Show all specs with their states and a summary of task counts per state.
    Use this as a quick project health check before starting work.
    """
    specs = _find_specs()
    if not specs:
        return f"No SPEC.md files found under {REPO}."

    lines = [f"SpecNative status — {REPO.name}\n"]
    task_files_by_spec_id: dict[str, Path] = {}
    for tf in _find_task_files():
        meta = _toml_loads(tf.read_text(encoding="utf-8"))
        sid = meta.get("spec_id")
        if sid:
            task_files_by_spec_id[sid] = tf

    for sp in specs:
        meta = _toml_loads(sp.read_text(encoding="utf-8"))
        sid = meta.get("id") or str(sp.relative_to(REPO))
        state = meta.get("state", "unknown")
        lines.append(f"  spec  {sid:<26} [{state}]")

        tf = task_files_by_spec_id.get(meta.get("id", ""))
        if not tf:
            # Fallback: look for tasks/<parent>/TASKS.md
            initiative = sp.parent.name
            candidate = REPO / "tasks" / initiative / "TASKS.md"
            tf = candidate if candidate.exists() else None

        if tf:
            lines.append(f"        tasks: {_task_state_summary(tf)}")
        else:
            lines.append("        tasks: no task file linked")

    return "\n".join(lines)


@mcp.tool()
def validate() -> str:
    """
    Validate that all required SpecNative files exist in the repository.
    Returns a list of missing files, or a success message.
    """
    required = [
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
        "agents/TRACEABILITY.md",
        "agents/SPEC.md",
        "tasks/README.md",
        "workflows/README.md",
        "pipelines/README.md",
        ".specnative/SCHEMA.md",
    ]
    missing = [r for r in required if not (REPO / r).exists()]
    if missing:
        return "Validation failed. Missing files:\n" + "\n".join(f"  - {m}" for m in missing)
    return f"Validation passed. All {len(required)} required files present."


@mcp.tool()
def list_specs() -> str:
    """
    List all spec files found in the repository with their IDs, states, and owners.
    Useful before starting a new initiative or reviewing project scope.
    """
    specs = _find_specs()
    if not specs:
        return "No spec files found."

    rows = []
    for sp in specs:
        meta = _toml_loads(sp.read_text(encoding="utf-8"))
        sid = meta.get("id") or str(sp.relative_to(REPO))
        state = meta.get("state", "—")
        owner = meta.get("owner", "—")
        rows.append(f"  {sid:<26} {state:<14} {owner}")

    header = f"  {'ID':<26} {'state':<14} owner\n  " + "─" * 56
    return header + "\n" + "\n".join(rows)


@mcp.tool()
def list_tasks(initiative: str) -> str:
    """
    List tasks for a given initiative with their states.

    Args:
        initiative: Folder name under tasks/ (e.g. 'authentication')
    """
    tf = REPO / "tasks" / initiative / "TASKS.md"
    if not tf.exists():
        return f"Task file not found: tasks/{initiative}/TASKS.md"

    text = tf.read_text(encoding="utf-8")
    blocks = re.findall(r"```toml\s*\n(.*?)\n```", text, re.DOTALL)

    if not blocks:
        return f"No TOML blocks in tasks/{initiative}/TASKS.md\n\n{text[:800]}"

    rows = []
    for block in blocks:
        meta = _toml_loads(f"```toml\n{block}\n```")
        if not meta.get("id"):
            continue  # skip file-level header block
        tid = meta.get("id", "—")
        title = meta.get("title", "—")
        state = meta.get("state", "—")
        owner = meta.get("owner", "—")
        rows.append(f"  {tid:<12} {state:<14} {owner:<16} {title}")

    if not rows:
        return "No individual task blocks found (only file-level TOML header)."

    header = f"  {'ID':<12} {'state':<14} {'owner':<16} title\n  " + "─" * 60
    return header + "\n" + "\n".join(rows)


@mcp.tool()
def read_spec(initiative: str = "") -> str:
    """
    Read a spec file.

    Args:
        initiative: Initiative name (empty → agents/SPEC.md,
                    otherwise agents/specs/{initiative}/SPEC.md)
    """
    path = (
        REPO / "agents" / "SPEC.md"
        if not initiative
        else REPO / "agents" / "specs" / initiative / "SPEC.md"
    )
    return _read(path)


@mcp.tool()
def read_context(document: str) -> str:
    """
    Read a context document by short name.

    Args:
        document: One of: product, architecture, stack, conventions, commands,
                  decisions, roadmap, traceability, agents, schema, ci, cd
    """
    mapping: dict[str, Path] = {
        "product":       REPO / "agents" / "PRODUCT.md",
        "architecture":  REPO / "agents" / "ARCHITECTURE.md",
        "stack":         REPO / "agents" / "STACK.md",
        "conventions":   REPO / "agents" / "CONVENTIONS.md",
        "commands":      REPO / "agents" / "COMMANDS.md",
        "decisions":     REPO / "agents" / "DECISIONS.md",
        "roadmap":       REPO / "agents" / "ROADMAP.md",
        "traceability":  REPO / "agents" / "TRACEABILITY.md",
        "agents":        REPO / "AGENTS.md",
        "schema":        REPO / ".specnative" / "SCHEMA.md",
        "ci":            REPO / "pipelines" / "CI.md",
        "cd":            REPO / "pipelines" / "CD.md",
    }
    path = mapping.get(document.lower())
    if not path:
        valid = ", ".join(sorted(mapping))
        return f"Unknown document '{document}'. Valid names: {valid}"
    return _read(path)


@mcp.tool()
def export_index() -> str:
    """
    Export all specs and task files with TOML metadata as a JSON string.
    Useful for programmatic processing or external tooling.
    """
    result: dict[str, Any] = {"specs": [], "task_files": []}
    for sp in _find_specs():
        meta = _toml_loads(sp.read_text(encoding="utf-8"))
        meta["_path"] = str(sp.relative_to(REPO))
        result["specs"].append(meta)
    for tf in _find_task_files():
        meta = _toml_loads(tf.read_text(encoding="utf-8"))
        meta["_path"] = str(tf.relative_to(REPO))
        result["task_files"].append(meta)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Prompts — structured workflow starters
# ---------------------------------------------------------------------------

@mcp.prompt()
def start_initiative(initiative_name: str, problem_description: str) -> str:
    """
    Begin a new spec-driven initiative.

    Args:
        initiative_name:      Short slug used as folder name (e.g. 'user-auth')
        problem_description:  One or two sentences describing the problem
    """
    return f"""You are starting a new SpecNative initiative called '{initiative_name}'.

Problem: {problem_description}

## Steps

1. Read the repository operating contract:
   Resource → spec://agents

2. Load minimum project context:
   Resource → spec://context/roadmap    (confirm initiative aligns with direction)
   Resource → spec://context/product    (understand users and goals)
   Resource → spec://context/decisions  (respect persistent trade-offs)

3. Use tool `status()` to see current active specs and avoid conflicts.

4. Create agents/specs/{initiative_name}/SPEC.md with:
   ```toml
   artifact_type = "spec"
   id            = "SPEC-XXXX"
   state         = "draft"
   owner         = "your-name"
   created_at    = "YYYY-MM-DD"
   updated_at    = "YYYY-MM-DD"
   replaces      = "none"
   related_tasks = []
   related_decisions = []
   ```
   Then write the Markdown body:
   - **Resumen**: what this initiative builds
   - **Problema**: friction today and for whom
   - **Objetivo**: observable end state
   - **Alcance**: includes / excludes
   - **Requisitos funcionales**: RF-1, RF-2 …
   - **Requisitos no funcionales**: RNF-1 …
   - **Criterios de aceptación**: Given / When / Then
   - **Dependencias y riesgos**
   - **Plan de ejecución**: task outline
   - **Plan de validación**: test approach

5. Present the draft to the user for review before saving.

Document ownership rule:
- Spec scope disappears when the initiative closes → SPEC.md only
- Persistent trade-offs → DECISIONS.md
- Product goals → PRODUCT.md
"""


@mcp.prompt()
def plan_tasks(initiative_name: str) -> str:
    """
    Derive an executable task list from an existing spec.

    Args:
        initiative_name: The initiative whose spec will be decomposed
    """
    return f"""You are creating the task plan for initiative '{initiative_name}'.

## Steps

1. Read the spec:
   Tool → read_spec(initiative='{initiative_name}')

2. Read the planning workflow:
   Read file: workflows/PLANNING.md

3. Read constraints before planning:
   Resource → spec://context/decisions
   Resource → spec://context/architecture

4. Decompose the spec into tasks (one task = one verifiable unit):
   - Every task produces observable evidence
   - Every task has a clear close criterion
   - Dependencies between tasks are explicit

5. Create tasks/{initiative_name}/TASKS.md:

   File header (TOML):
   ```toml
   artifact_type = "task_file"
   initiative    = "{initiative_name}"
   spec_id       = "SPEC-XXXX"
   owner         = "your-name"
   state         = "todo"
   ```

   Per task:
   ```toml
   id             = "TASK-0001"
   title          = "Short action title"
   state          = "todo"
   owner          = "your-name"
   dependencies   = []
   expected_files = ["src/example.py"]
   close_criteria = "Observable closure condition"
   validation     = ["pytest tests/example_test.py"]
   ```
   Followed by a brief Markdown description of the task's scope and risks.

6. Present the task list to the user for review before saving.
"""


@mcp.prompt()
def implement_task(initiative_name: str, task_id: str) -> str:
    """
    Implement a specific task from an initiative.

    Args:
        initiative_name: The initiative name
        task_id:         The task ID to implement (e.g. TASK-0001)
    """
    return f"""You are implementing {task_id} from initiative '{initiative_name}'.

## Steps

1. Read the spec for acceptance context:
   Tool → read_spec(initiative='{initiative_name}')

2. Read the task details:
   Tool → list_tasks(initiative='{initiative_name}')

3. Load constraints:
   Resource → spec://context/architecture
   Resource → spec://context/stack
   Resource → spec://context/conventions
   Resource → spec://context/commands   (to run project commands)

4. Read the implementation workflow:
   File: workflows/IMPLEMENTATION.md

5. Implement {task_id}:
   - Respect architecture boundaries
   - Follow stack constraints and conventions
   - Produce the expected_files listed in the task TOML
   - Run the validation command from the task TOML

6. After validation:
   - If validation passes → update task state to 'done'
   - If blocked → update task state to 'blocked', add a blocker note

7. If a persistent trade-off emerged during implementation:
   Use prompt → record_decision to document it before closing the task.

8. Check pipelines/CI.md to confirm the change would pass automated gates.
"""


@mcp.prompt()
def review_against_spec(initiative_name: str) -> str:
    """
    Review an implementation against the spec's acceptance criteria.

    Args:
        initiative_name: The initiative to review
    """
    return f"""You are reviewing initiative '{initiative_name}' against its spec.

## Steps

1. Read the spec (acceptance criteria are the benchmark):
   Tool → read_spec(initiative='{initiative_name}')

2. Read the task summary to see what was completed:
   Tool → list_tasks(initiative='{initiative_name}')

3. Read the review workflow:
   File: workflows/REVIEW.md

4. For each acceptance criterion:
   - Confirm there is implementation evidence
   - Confirm the relevant task close criterion is satisfied
   - Flag any criterion that is not fully covered

5. Produce a review report:
   ### Criteria met
   - Criterion X → evidence (file, test, PR)

   ### Criteria not met
   - Criterion Y → gap description

   ### Recommendation
   approve | request changes | block

6. If all criteria are met, the spec state can move to 'done'.
   Proceed to prompt → close_initiative when ready.
"""


@mcp.prompt()
def record_decision(
    decision_title: str,
    context: str,
    decision: str,
    consequences: str,
) -> str:
    """
    Record a persistent decision in DECISIONS.md.

    Args:
        decision_title: Short descriptive title
        context:        What problem or situation forced this decision
        decision:       What was decided exactly
        consequences:   Costs, benefits, and limits (what future work must respect)
    """
    return f"""You are recording a new persistent decision.

Title:        {decision_title}
Context:      {context}
Decision:     {decision}
Consequences: {consequences}

## Steps

1. Read the current decisions file:
   Resource → spec://context/decisions

2. Determine the next DEC-XXXX number.

3. Confirm this decision does not duplicate or contradict an existing one.

4. Append to agents/DECISIONS.md:

   ### DEC-XXXX — {decision_title}

   - Fecha: {{today}}
   - Estado: `accepted`
   - Relacionado con specs: (list relevant active specs)
   - Contexto: {context}
   - Decisión: {decision}
   - Consecuencias: {consequences}
   - Reemplaza: none

5. Only record decisions that future initiatives must respect.
   Implementation details or spec-specific choices belong in the spec, not here.
"""


@mcp.prompt()
def close_initiative(initiative_name: str) -> str:
    """
    Close an initiative: verify completion, update spec state and traceability.

    Args:
        initiative_name: The initiative to close
    """
    return f"""You are closing the '{initiative_name}' initiative.

## Steps

1. Verify all tasks are done (or blocked with justification):
   Tool → list_tasks(initiative='{initiative_name}')

2. Verify all acceptance criteria are met:
   Tool → read_spec(initiative='{initiative_name}')
   (Use prompt → review_against_spec first if not already done)

3. Update the spec state:
   - All criteria met → state = 'done'
   - Blocked → state = 'blocked', add blocking reason

4. Update agents/TRACEABILITY.md — add an entry:
   ### {initiative_name.upper()} — SPEC-XXXX

   - Spec:       agents/specs/{initiative_name}/SPEC.md
   - Tasks:      tasks/{initiative_name}/TASKS.md
   - Decisions:  DEC-XXXX (list any decisions made during this initiative)
   - Artifacts:  (key files produced)
   - Validation: (test results, review outcome, CI link)

5. If persistent decisions were made but not yet recorded:
   Use prompt → record_decision for each one.

6. Check agents/ROADMAP.md — if this initiative appeared there, update it.

7. Report what was delivered and what (if anything) remains open.
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _ARGS.transport == "sse":
        mcp.run(transport="sse", port=_ARGS.port)
    else:
        mcp.run(transport="stdio")
