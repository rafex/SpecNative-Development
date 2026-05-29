#!/usr/bin/env python3
"""
SpecNative MCP Server — v0.5

Exposes a SpecNative repository as MCP resources, tools, and prompts so any
MCP-compatible agent (Claude Desktop, Claude Code, OpenCode, Codex, etc.) can
work spec-first without manually navigating the file tree.

v0.5 adds multi-agent continuity tools:
  checkpoint   — save active work state so the next agent can resume
  resume       — read last checkpoint and return a handoff summary
  update_task  — update a task state directly from MCP
  log_decision — append a new decision to DECISIONS.md
  context_snapshot — full context dump for new-agent onboarding
  handoff prompt   — generate structured handoff note

Resources  — read repository context documents by URI
Tools      — validate, status, list specs/tasks, read, export, session tools
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit(
        "mcp package not found.\n"
        "Install with:  pip install mcp\n"
        "Then retry:    python3 specnative_mcp.py --repo /path/to/project\n"
    )

VERSION = "dev"  # replaced by CI on release

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
        "Read AGENTS.md first. All project context is in spec-native/. "
        "If there is active work, call resume() before starting. "
        "Load only the minimum context needed for the current task."
    ),
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

SN = REPO / "spec-native"


def _read(path: Path) -> str:
    """Return file contents or a clear placeholder when the file is absent."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"(file not found: {path.relative_to(REPO) if path.is_relative_to(REPO) else path})"


def _find_specs() -> list[Path]:
    return sorted(
        p for p in REPO.rglob("SPEC.md")
        if ".specnative" not in p.parts and "spec-native" in p.parts
    )


def _find_task_files() -> list[Path]:
    tasks_dir = SN / "tasks"
    return sorted(tasks_dir.rglob("TASKS.md")) if tasks_dir.exists() else []


def _toml_loads(text: str) -> dict[str, Any]:
    """Parse the first ```toml block in *text*, return {} on any failure."""
    match = re.search(r"```toml\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        # Also try +++ TOML front matter (used in SESSION.md)
        match = re.search(r"^\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL | re.MULTILINE)
        if not match:
            return {}
    raw = match.group(1)
    try:
        import tomllib          # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # backport
        except ImportError:
            result: dict[str, Any] = {}
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _update_session(fields: dict[str, str], sections: dict[str, str]) -> None:
    """Write or update spec-native/SESSION.md with new TOML front matter and sections."""
    session_path = SN / "SESSION.md"

    # Read existing content
    existing = session_path.read_text(encoding="utf-8") if session_path.exists() else ""

    # Parse existing TOML front matter
    meta_match = re.search(r"^\+\+\+\s*\n(.*?)\n\+\+\+", existing, re.DOTALL | re.MULTILINE)
    if meta_match:
        existing_meta_raw = meta_match.group(1)
    else:
        existing_meta_raw = ""

    # Merge fields
    meta_lines: list[str] = []
    existing_fields: dict[str, str] = {}
    for line in existing_meta_raw.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            existing_fields[k.strip()] = v.strip().strip('"')

    merged = {**existing_fields, **fields}
    meta_section = "[session]\n" + "\n".join(f'{k} = "{v}"' for k, v in merged.items())

    # Build new content
    body_parts = [f"+++\n{meta_section}\n+++\n\n# Active Session\n"]
    for heading, content in sections.items():
        body_parts.append(f"\n## {heading}\n\n{content}\n")

    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text("".join(body_parts), encoding="utf-8")


# ---------------------------------------------------------------------------
# Resources — repository context documents
# ---------------------------------------------------------------------------

@mcp.resource("spec://agents")
def resource_agents_contract() -> str:
    """AGENTS.md — agent operating contract and MCP reference. Read this first."""
    return _read(REPO / "AGENTS.md")


@mcp.resource("spec://session")
def resource_session() -> str:
    """spec-native/SESSION.md — active work state. Call resume() to get a summary."""
    return _read(SN / "SESSION.md")


@mcp.resource("spec://context/product")
def resource_product() -> str:
    """PRODUCT.md — problem, users, goals (permanent)."""
    return _read(SN / "PRODUCT.md")


@mcp.resource("spec://context/architecture")
def resource_architecture() -> str:
    """ARCHITECTURE.md — system structure, boundaries, constraints."""
    return _read(SN / "ARCHITECTURE.md")


@mcp.resource("spec://context/stack")
def resource_stack() -> str:
    """STACK.md — tech stack and version constraints."""
    return _read(SN / "STACK.md")


@mcp.resource("spec://context/conventions")
def resource_conventions() -> str:
    """CONVENTIONS.md — code rules, naming, testing approach."""
    return _read(SN / "CONVENTIONS.md")


@mcp.resource("spec://context/commands")
def resource_commands() -> str:
    """COMMANDS.md — project-specific dev/test/build commands."""
    return _read(SN / "COMMANDS.md")


@mcp.resource("spec://context/decisions")
def resource_decisions() -> str:
    """DECISIONS.md — persistent decisions and trade-offs."""
    return _read(SN / "DECISIONS.md")


@mcp.resource("spec://context/roadmap")
def resource_roadmap() -> str:
    """ROADMAP.md — temporal direction and priorities."""
    return _read(SN / "ROADMAP.md")


@mcp.resource("spec://context/traceability")
def resource_traceability() -> str:
    """TRACEABILITY.md — cross-artifact links (update when initiative closes)."""
    return _read(SN / "TRACEABILITY.md")


@mcp.resource("spec://pipelines/ci")
def resource_ci() -> str:
    """spec-native/pipelines/CI.md — automated validation gates."""
    return _read(SN / "pipelines" / "CI.md")


@mcp.resource("spec://pipelines/cd")
def resource_cd() -> str:
    """spec-native/pipelines/CD.md — delivery process and environments."""
    return _read(SN / "pipelines" / "CD.md")


@mcp.resource("spec://schema")
def resource_schema() -> str:
    """.specnative/SCHEMA.md — framework contract (required files, states, ownership)."""
    return _read(REPO / ".specnative" / "SCHEMA.md")


# ---------------------------------------------------------------------------
# Tools — read-only queries
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
            initiative = sp.parent.name
            candidate = SN / "tasks" / initiative / "TASKS.md"
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
        "spec-native/tasks/README.md",
        "spec-native/workflows/README.md",
        "spec-native/pipelines/README.md",
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
        initiative: Folder name under spec-native/tasks/ (e.g. 'authentication')
    """
    tf = SN / "tasks" / initiative / "TASKS.md"
    if not tf.exists():
        return f"Task file not found: spec-native/tasks/{initiative}/TASKS.md"

    text = tf.read_text(encoding="utf-8")
    blocks = re.findall(r"```toml\s*\n(.*?)\n```", text, re.DOTALL)

    if not blocks:
        return f"No TOML blocks in spec-native/tasks/{initiative}/TASKS.md\n\n{text[:800]}"

    rows = []
    for block in blocks:
        meta = _toml_loads(f"```toml\n{block}\n```")
        if not meta.get("id"):
            continue
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
        initiative: Initiative name (empty → spec-native/SPEC.md if exists,
                    otherwise spec-native/specs/{initiative}/SPEC.md)
    """
    path = (
        SN / "SPEC.md"
        if not initiative
        else SN / "specs" / initiative / "SPEC.md"
    )
    return _read(path)


@mcp.tool()
def read_context(document: str) -> str:
    """
    Read a context document by short name.

    Args:
        document: One of: product, architecture, stack, conventions, commands,
                  decisions, roadmap, traceability, session, agents, schema, ci, cd
    """
    mapping: dict[str, Path] = {
        "product":       SN / "PRODUCT.md",
        "architecture":  SN / "ARCHITECTURE.md",
        "stack":         SN / "STACK.md",
        "conventions":   SN / "CONVENTIONS.md",
        "commands":      SN / "COMMANDS.md",
        "decisions":     SN / "DECISIONS.md",
        "roadmap":       SN / "ROADMAP.md",
        "traceability":  SN / "TRACEABILITY.md",
        "session":       SN / "SESSION.md",
        "agents":        REPO / "AGENTS.md",
        "schema":        REPO / ".specnative" / "SCHEMA.md",
        "ci":            SN / "pipelines" / "CI.md",
        "cd":            SN / "pipelines" / "CD.md",
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
# Tools — multi-agent continuity (v0.5)
# ---------------------------------------------------------------------------

@mcp.tool()
def resume() -> str:
    """
    Read SESSION.md and return a structured continuity summary.
    Call this first when entering a repository where another agent may have
    been working. Works regardless of which agent created the checkpoint.
    """
    session_path = SN / "SESSION.md"
    if not session_path.exists():
        return "No SESSION.md found. Start fresh or call status() to see active specs."

    text = session_path.read_text(encoding="utf-8")
    meta = _toml_loads(text)

    session = meta.get("session", meta)  # support both [session] table and flat
    state = session.get("state", "idle")

    if state == "idle":
        return (
            "SESSION state: idle — no active work.\n"
            "Call status() to see specs, or start_initiative() to begin new work."
        )

    initiative = session.get("initiative", "(unknown)")
    task = session.get("task", "(unknown)")
    agent = session.get("agent", "(unknown)")
    intent = session.get("intent", "")
    last_updated = session.get("last_updated", "")

    # Extract narrative sections from markdown body
    sections: dict[str, str] = {}
    body_match = re.search(r"\+\+\+.*?\+\+\+(.*)", text, re.DOTALL)
    body = body_match.group(1) if body_match else text
    for m in re.finditer(r"^##\s+(.+?)\s*$\n(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL):
        heading = m.group(1).strip()
        content = m.group(2).strip()
        if content and not content.startswith("<!--"):
            sections[heading] = content

    lines = [
        f"SESSION RESUME — {REPO.name}",
        f"",
        f"State      : {state}",
        f"Initiative : {initiative}",
        f"Task       : {task}",
        f"Last agent : {agent}",
        f"Updated    : {last_updated}",
    ]
    if intent:
        lines += ["", f"Intent: {intent}"]
    for heading, content in sections.items():
        lines += ["", f"── {heading} ──", content]

    lines += [
        "",
        "── Suggested next actions ──",
        f"  list_tasks(initiative='{initiative}')  → see task states",
        f"  read_spec(initiative='{initiative}')   → review spec",
        f"  update_task('{initiative}', '{task}', 'in_progress')  → claim the task",
    ]

    return "\n".join(lines)


@mcp.tool()
def checkpoint(
    initiative: str,
    task_id: str,
    intent: str,
    next_steps: str,
    context_notes: str = "",
    agent_name: str = "",
) -> str:
    """
    Save current work state to SESSION.md so the next agent can resume.
    Call this before ending a session or switching agents.

    Args:
        initiative:    Active initiative name (e.g. 'authentication')
        task_id:       Task currently in progress (e.g. 'TASK-AUTH-0002')
        intent:        One sentence — what you were trying to accomplish
        next_steps:    Ordered list of next actions (one per line)
        context_notes: Optional — decisions, gotchas, env vars, touched files
        agent_name:    Optional — name/id of the agent saving the checkpoint
    """
    fields = {
        "state":        "in_progress",
        "agent":        agent_name or "unknown",
        "initiative":   initiative,
        "task":         task_id,
        "intent":       intent,
        "last_updated": _now_iso(),
    }
    sections: dict[str, str] = {
        "Current state": intent,
        "Next steps": next_steps,
    }
    if context_notes:
        sections["Context for next agent"] = context_notes

    _update_session(fields, sections)
    return (
        f"Checkpoint saved to spec-native/SESSION.md.\n"
        f"Initiative: {initiative} | Task: {task_id}\n"
        f"The next agent can call resume() to continue from here."
    )


@mcp.tool()
def update_task(initiative: str, task_id: str, state: str, notes: str = "") -> str:
    """
    Update the state of a task in spec-native/tasks/{initiative}/TASKS.md.
    Valid states: todo, in_progress, blocked, done.

    Args:
        initiative: Initiative folder name (e.g. 'authentication')
        task_id:    Task ID to update (e.g. 'TASK-AUTH-0002')
        state:      New state: todo | in_progress | blocked | done
        notes:      Optional note appended below the task heading
    """
    valid_states = {"todo", "in_progress", "blocked", "done"}
    if state not in valid_states:
        return f"Invalid state '{state}'. Must be one of: {', '.join(sorted(valid_states))}"

    tf = SN / "tasks" / initiative / "TASKS.md"
    if not tf.exists():
        return f"Task file not found: spec-native/tasks/{initiative}/TASKS.md"

    text = tf.read_text(encoding="utf-8")

    # Replace the state field inside the task's TOML block
    pattern = re.compile(
        r'(```toml\s*\n(?:(?!```).)*?\bid\s*=\s*"' + re.escape(task_id) +
        r'"(?:(?!```).)*?)(\bstate\s*=\s*"[^"]*")((?:(?!```).)*?```)',
        re.DOTALL,
    )
    new_text, count = pattern.subn(lambda m: m.group(1) + f'state = "{state}"' + m.group(3), text)

    if count == 0:
        return f"Task '{task_id}' not found or has no TOML state field in spec-native/tasks/{initiative}/TASKS.md"

    if notes:
        # Append note after the task heading
        heading_pattern = re.compile(
            r"(###\s+" + re.escape(task_id) + r".*?\n)", re.IGNORECASE
        )
        new_text = heading_pattern.sub(
            lambda m: m.group(0) + f"\n> **Update {_now_iso()}:** {notes}\n",
            new_text,
            count=1,
        )

    tf.write_text(new_text, encoding="utf-8")
    return f"Task {task_id} state updated to '{state}' in spec-native/tasks/{initiative}/TASKS.md."


@mcp.tool()
def log_decision(
    title: str,
    context: str,
    decision: str,
    consequences: str,
) -> str:
    """
    Append a new persistent decision to spec-native/DECISIONS.md.
    Use this for trade-offs that future initiatives must respect.

    Args:
        title:        Short descriptive title
        context:      What problem or situation forced this decision
        decision:     What was decided exactly
        consequences: Costs, benefits, and limits future work must respect
    """
    decisions_path = SN / "DECISIONS.md"
    existing = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""

    # Determine next DEC number
    ids = re.findall(r"DEC-(\d+)", existing)
    next_num = (max(int(i) for i in ids) + 1) if ids else 1
    dec_id = f"DEC-{next_num:04d}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = f"""
### {dec_id} — {title}

- Fecha: {today}
- Estado: `accepted`
- Relacionado con specs:
- Contexto: {context}
- Decisión: {decision}
- Consecuencias: {consequences}
- Reemplaza: none
"""

    decisions_path.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")
    return f"Decision {dec_id} appended to spec-native/DECISIONS.md."


@mcp.tool()
def context_snapshot(initiative: str = "") -> str:
    """
    Return a full context dump for onboarding a new agent.
    Includes: product, architecture, stack, active spec, pending tasks, session.
    Use this when starting work in an unfamiliar repository.

    Args:
        initiative: Optional — include spec and tasks for this initiative
    """
    parts: list[str] = [
        f"# SpecNative Context Snapshot — {REPO.name}",
        f"Generated: {_now_iso()}",
        "",
    ]

    for label, path in [
        ("PRODUCT", SN / "PRODUCT.md"),
        ("ARCHITECTURE", SN / "ARCHITECTURE.md"),
        ("STACK", SN / "STACK.md"),
        ("DECISIONS", SN / "DECISIONS.md"),
        ("ROADMAP", SN / "ROADMAP.md"),
    ]:
        content = _read(path)
        parts += [f"## {label}", content, ""]

    if initiative:
        spec_path = SN / "specs" / initiative / "SPEC.md"
        tasks_path = SN / "tasks" / initiative / "TASKS.md"
        parts += [f"## SPEC ({initiative})", _read(spec_path), ""]
        parts += [f"## TASKS ({initiative})", _read(tasks_path), ""]

    # Session
    session_content = _read(SN / "SESSION.md")
    parts += ["## SESSION", session_content, ""]

    return "\n".join(parts)


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

4. Create spec-native/specs/{initiative_name}/SPEC.md with:
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
- Persistent trade-offs → DECISIONS.md (or use log_decision tool)
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
   Read file: spec-native/workflows/PLANNING.md

3. Read constraints before planning:
   Resource → spec://context/decisions
   Resource → spec://context/architecture

4. Decompose the spec into tasks (one task = one verifiable unit):
   - Every task produces observable evidence
   - Every task has a clear close criterion
   - Dependencies between tasks are explicit

5. Create spec-native/tasks/{initiative_name}/TASKS.md:

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

1. Check for active session:
   Tool → resume()

2. Read the spec for acceptance context:
   Tool → read_spec(initiative='{initiative_name}')

3. Read the task details:
   Tool → list_tasks(initiative='{initiative_name}')

4. Load constraints:
   Resource → spec://context/architecture
   Resource → spec://context/stack
   Resource → spec://context/conventions
   Resource → spec://context/commands   (to run project commands)

5. Mark the task as in progress:
   Tool → update_task('{initiative_name}', '{task_id}', 'in_progress')

6. Implement {task_id}:
   - Respect architecture boundaries
   - Follow stack constraints and conventions
   - Produce the expected_files listed in the task TOML
   - Run the validation command from the task TOML

7. After validation:
   - If passes → update_task('{initiative_name}', '{task_id}', 'done')
   - If blocked → update_task('{initiative_name}', '{task_id}', 'blocked', notes='reason')

8. If a persistent trade-off emerged:
   Tool → log_decision(title, context, decision, consequences)

9. Save a checkpoint before ending the session:
   Tool → checkpoint('{initiative_name}', '{task_id}', intent, next_steps)

10. Check spec-native/pipelines/CI.md to confirm change passes automated gates.
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
   File: spec-native/workflows/REVIEW.md

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
def handoff(summary: str, next_steps: str, decisions_made: str = "") -> str:
    """
    Generate a structured handoff for the next agent and save it to SESSION.md.
    Use this when you are ending a session and another agent will continue.

    Args:
        summary:          What was accomplished in this session
        next_steps:       Ordered list of what the next agent should do first
        decisions_made:   Optional — decisions taken mid-session not yet in DECISIONS.md
    """
    return f"""You are generating a handoff for the next agent.

Summary of this session:
{summary}

Next steps for the next agent:
{next_steps}

{f"Decisions made (not yet in DECISIONS.md):{chr(10)}{decisions_made}" if decisions_made else ""}

## Steps

1. Save checkpoint via MCP tool:
   checkpoint(
     initiative=<current_initiative>,
     task_id=<current_task>,
     intent=<one line summary>,
     next_steps='''{next_steps}''',
     context_notes='''{decisions_made or "none"}'''
   )
   This updates SESSION.md with state = "waiting_handoff".

2. If any decisions were made mid-session, save them:
   log_decision(title, context, decision, consequences)

3. Confirm the handoff is ready:
   read_context('session')   → verify SESSION.md was updated

The next agent should start with:
   resume()   → to see this handoff
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
    Prefer tool log_decision() for quick inline use.
    Use this prompt for decisions that need review before saving.

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

2. Confirm this decision does not duplicate or contradict an existing one.

3. Use the tool to append:
   Tool → log_decision(
     title="{decision_title}",
     context="{context}",
     decision="{decision}",
     consequences="{consequences}"
   )

4. Only record decisions that future initiatives must respect.
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

4. Update spec-native/TRACEABILITY.md — add an entry:
   ### {initiative_name.upper()} — SPEC-XXXX

   - Spec:       spec-native/specs/{initiative_name}/SPEC.md
   - Tasks:      spec-native/tasks/{initiative_name}/TASKS.md
   - Decisions:  DEC-XXXX (list any decisions made during this initiative)
   - Artifacts:  (key files produced)
   - Validation: (test results, review outcome, CI link)

5. If persistent decisions were made but not yet recorded:
   Tool → log_decision(title, context, decision, consequences)

6. Reset SESSION.md to idle:
   Update state = "idle", clear initiative, task, intent fields.

7. Check spec-native/ROADMAP.md — if this initiative appeared there, update it.

8. Report what was delivered and what (if anything) remains open.
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _ARGS.transport == "sse":
        mcp.run(transport="sse", port=_ARGS.port)
    else:
        mcp.run(transport="stdio")
