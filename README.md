![SpecNative Development Logo](./docs/assets/specnative-logo.svg)

# SpecNative Development

Repository-structured, specification-first development for AI agents and humans.

**[Website](https://specnative-d.rafex.io) · [AI Agent Guide](https://specnative-d.rafex.io/ai/) · [Template](./Template-Project-Agents-AI) · [Releases](https://github.com/rafex/SpecNative-Development/releases)**

---

## What is SpecNative Development

SpecNative is a development model where specifications, architecture rules, conventions, and decisions live in stable repository files so agents can plan and implement work with less runtime ambiguity.

**The repository is the context system. Prompts are thin triggers, not project manuals.**

```
prompt → select spec  (not: explain project from scratch)
```

Instead of rebuilding project context in every session, the repository encodes it once and the agent navigates it deterministically.

## Use SpecNative

Use one short entry point for any request:

```text
/spec <request>                 # Claude Code
spec <request>                  # OpenCode and Codex prompt
specnative(request)             # MCP prompt
```

The workflow reads the repository contract, checks active work, and routes to
the smallest correct action: initiative, backlog, implementation, decision,
review, handoff, or closure. Skills installed with the template make this
workflow available to Claude Code and OpenCode; Codex also receives matching
project prompts.

For focused work, use `/spec-backlog-add <request>` to capture work as a
canonical task or a triaged intake item. Use MCP `list_architecture(tag)`,
`list_conventions(tag)`, `list_decisions(tag)`, and `read_context_artifact(id)`
to load only the related context.

---

## Quick Start

**Current Release:** [v0.8.1](https://github.com/rafex/SpecNative-Development/releases/tag/v0.8.1) <!-- CURRENT_RELEASE -->

### Install into an existing repository

Download and run in one step:

```bash
# Minimal context layer (AGENTS.md + docs)
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --target /path/to/your/repo --profile context

# Full spec lifecycle + CI/CD pipelines (recommended)
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --target /path/to/your/repo --profile team

# Full setup with examples
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --target /path/to/your/repo --profile platform --include-examples
```

Or download once and run locally:

```bash
python3 install.py --target /path/to/your/repo --profile team
python3 install.py --target /path/to/your/repo --profile platform --include-examples
```

### Repair broken MCP

If your MCP installation is broken, reinstall it without touching other files:

```bash
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --reinstall --target /path/to/your/repo
```

Or locally:

```bash
python3 install.py --reinstall --target /path/to/your/repo
```

### Installation profiles

Profiles are cumulative — each one adds files on top of the previous layer.

| Profile | What it installs | Best for |
|---------|-----------------|----------|
| `context` | Core context plus navigation indexes, `SESSION.md` and `.specnative/{README,MCP,SCHEMA}.md`; no task templates or examples | Solo devs and projects that want a coherent AI context layer |
| `spec` | **context** + task template and complete planning/review workflows | Startups and solo devs building spec-first without CI/CD |
| `team` *(default)* | **spec** + `spec-native/pipelines/{CI,CD}.md` · `.specnative/{CLI,SCHEMA}.md` | Teams with automated pipelines and pull request workflows |
| `platform` | **team** + `README.md` (if absent) + authentication example initiative | Open-source projects and orgs that need reference implementations |

Add `--include-examples` to any profile to include the example authentication initiative.

### Connect via MCP (Claude Code, Claude Desktop, OpenCode)

**MCP configs are created automatically** during installation to `opencode.json`.

For Claude Desktop, add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "specnative": {
      "command": "python3",
      "args": ["/path/to/.specnative/specnative_mcp.py"]
    }
  }
}
```

For Claude Code:

```bash
claude mcp add specnative \
  python3 /path/to/.specnative/specnative_mcp.py
```

See [`.specnative/MCP.md`](./Template-Project-Agents-AI/.specnative/MCP.md) for full per-agent configuration.

---

## Repository layout

```
AGENTS.md                    # Meta-index — what is SpecNative, where is everything, MCP reference
spec-native/
├── README.md                # Navigation index
├── PRODUCT.md               # Problem, users, goals (permanent)
├── ARCHITECTURE.md          # System structure and boundaries
├── STACK.md                 # Tech stack and version constraints
├── CONVENTIONS.md           # Code rules, naming, testing
├── COMMANDS.md              # Project-specific dev/test/build commands
├── DECISIONS.md             # Persistent decisions and trade-offs
├── ROADMAP.md               # Temporal direction
├── TRACEABILITY.md          # Cross-artifact links
├── SESSION.md               # Active work state — for multi-agent continuity
├── specs/
│   └── <initiative>/SPEC.md
├── tasks/
│   └── <initiative>/TASKS.md
├── backlog/                 # Generated delivery-board views; never edit state here
├── workflows/               # PLANNING.md, IMPLEMENTATION.md, REVIEW.md
└── pipelines/               # CI.md, CD.md — CI/CD context
.specnative/                 # Framework infrastructure
├── SCHEMA.md                # Framework contract (required files, states)
├── CLI.md                   # CLI reference
├── MCP.md                   # MCP server configuration per agent
└── specnative_mcp.py        # MCP server (installed automatically)
```

### Document ownership — one truth per document

| Document | Owns |
|---|---|
| `spec-native/PRODUCT.md` | Problem, users, goals, non-goals |
| `spec-native/specs/*/SPEC.md` | What must be built in this initiative (time-bounded) |
| `spec-native/DECISIONS.md` | Persistent trade-offs future initiatives must respect |
| `spec-native/ROADMAP.md` | Temporal direction without implementation detail |
| `spec-native/ARCHITECTURE.md` | System structure, modules, boundaries |
| `spec-native/CONVENTIONS.md` | Naming, style, testing, commit conventions |
| `spec-native/COMMANDS.md` | Project commands only — never framework CLI |
| `spec-native/tasks/**/TASKS.md` | Executable plan with state, owner, close criteria |
| `spec-native/TRACEABILITY.md` | Cross-artifact links (update at initiative close) |
| `spec-native/pipelines/CI.md` | Automated gate definitions |
| `spec-native/pipelines/CD.md` | Delivery process and environments |
| `spec-native/SESSION.md` | Active work state for multi-agent continuity |

---

## Framework tooling

### CLI — `tools/specnative.py`

```bash
python3 tools/specnative.py status --target /path/to/project              # Spec and task state overview
python3 tools/specnative.py validate --target /path/to/project            # Check required files and TOML
python3 tools/specnative.py export-index --target /path/to/project        # Export specs/tasks as JSON
python3 tools/specnative.py export-traceability --target /path/to/project # Export traceability matrix as JSON
python3 tools/specnative.py board --target /path/to/project               # Derived delivery board
python3 tools/specnative.py board --target /path/to/project --format mermaid
python3 tools/specnative.py github-project plan --target /path/to/project # No-side-effect export plan
```

### Work management

`TASKS.md` remains the only editable execution record. `board` calculates
`ready`, `in_progress`, `blocked`, `waiting`, and `done` from task state and
dependencies; it is not a second backlog file. A task can reach `done` only
when it records completion evidence in addition to planned validation.

GitHub Projects is optional and currently begins with a deterministic export
plan. Copy `.specnative/integrations/github-project.toml.example`, configure
the ProjectV2 node ID and status names, then inspect the JSON produced by
`github-project plan`. It performs no network requests and does not make
GitHub authoritative.

### MCP server — `tools/specnative_mcp.py` (v0.8) <!-- MCP_VERSION -->

Exposes the repository as MCP resources, tools, and prompts so any MCP-compatible
agent works spec-first without manually navigating the file tree.

**v0.5 adds multi-agent continuity** — agents can checkpoint their work and resume
from exactly where another agent left off, regardless of which agent or tool was used.

**Resources** — context documents by URI:

```
spec://agents                  → AGENTS.md
spec://session                 → spec-native/SESSION.md  ← NEW
spec://context/product         → spec-native/PRODUCT.md
spec://context/architecture    → spec-native/ARCHITECTURE.md
spec://context/decisions       → spec-native/DECISIONS.md
spec://context/roadmap         → spec-native/ROADMAP.md
spec://pipelines/ci            → spec-native/pipelines/CI.md
spec://schema                  → .specnative/SCHEMA.md
```

**Tools**:

| Tool | Description |
|------|-------------|
| `status()` | Spec and task state overview |
| `validate()` | Check required files |
| `list_specs()` | List specs with states |
| `list_tasks(initiative)` | List tasks for an initiative |
| `board(format?)` | Read-only delivery board derived from canonical task files |
| `capture_backlog_item(...)` | Capture an executable task or a triaged intake idea |
| `list_decisions(tag?)` | List persistent decisions by tag |
| `list_architecture(tag?)` | List architecture artifacts by tag |
| `list_conventions(tag?)` | List convention artifacts by tag |
| `read_context_artifact(id)` | Read one decision, architecture, or convention artifact |
| `read_spec(initiative)` | Read a spec file |
| `read_context(document)` | Read a context document |
| `export_index()` | Export specs/tasks as JSON |
| `context_snapshot(initiative?)` | Full context dump for new-agent onboarding |
| `resume()` | Read SESSION.md and return continuity summary |
| `checkpoint(initiative, task_id, intent, next_steps, ...)` | Save work state |
| `update_task(initiative, task_id, state, notes?, completion_evidence?)` | Update task state; evidence is required to close |
| `log_decision(title, context, decision, consequences)` | Append decision |

**Prompts**: `start_initiative`, `plan_tasks`, `implement_task`, `review_against_spec`, `handoff`, `record_decision`, `close_initiative`

#### Configure per agent

**Claude Code**
```bash
claude mcp add specnative \
  "$(pwd)/.specnative/.venv/bin/python3" "$(pwd)/.specnative/specnative_mcp.py" \
  -- --repo "$(pwd)"
```

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "specnative": {
      "command": "/path/to/.specnative/.venv/bin/python3",
      "args": ["/path/to/.specnative/specnative_mcp.py", "--repo", "/path/to/project"]
    }
  }
}
```

**OpenCode** — generated automatically to `opencode.json` during install.

**Codex CLI** — `~/.codex/config.toml` or `codex.toml`:
```toml
[mcp_servers.specnative]
command = "python3"
args = ["/path/to/specnative_mcp.py", "--repo", "/path/to/project"]
type = "stdio"
```

---

## Core principles

- **Specification-first.** Behavior is defined before implementation. Specs are executable context, not documentation afterthoughts.
- **Repository as context system.** Durable project knowledge lives in files, not transient chat history.
- **One truth per document.** Facts exist in one authoritative document. Never duplicated across prompts, tickets, or local notes.
- **Deterministic navigation.** Agents read `AGENTS.md` first, navigate via `README.md` files, load minimum context for the task.
- **TOML is optional.** Documents are valid without TOML metadata. Add it when you want `validate`/`status`/`export` CLI commands to work automatically.
- **Minimal runtime dependency.** No specific agent runtime or proprietary orchestration required.

---

## How agents work with a SpecNative repository

**Any agent, any tool** — Claude Code, Codex, Cursor, or any other — follows the same flow:

1. Read `AGENTS.md` — what is SpecNative, where is everything, how to use MCP.
2. Call `resume()` — check if another agent left work in progress.
3. Call `context_snapshot()` or read `spec-native/ROADMAP.md` for orientation.
4. Read `spec-native/DECISIONS.md` — respect persistent trade-offs.
5. Review or create a spec in `spec-native/specs/`.
6. Derive tasks in `spec-native/tasks/`.
7. Implement following `spec-native/workflows/IMPLEMENTATION.md`.
8. Record decisions with `log_decision()` as they emerge.
9. Call `checkpoint()` before ending the session.
10. Update `spec-native/TRACEABILITY.md` when the initiative closes.

**With the MCP server**, agents access all of this through typed resources and structured prompts. No manual file navigation. No context lost between sessions.

### Multi-agent continuity

```
Agent A (Claude Code) — runs out of tokens mid-task:
  → checkpoint(initiative='auth', task_id='TASK-AUTH-0002',
               intent='Implementing JWT middleware',
               next_steps='1. Add /refresh endpoint\n2. Write integration tests',
               context_notes='JWT secret in env AUTH_SECRET. Do not hardcode.')

Agent B (Codex) — picks up the work:
  → resume()
  ← "Task TASK-AUTH-0002 in progress. Next: Add /refresh endpoint..."
  → Continues without friction, no context lost
```

SESSION.md is versioned in git — any agent on any machine can resume.

---

## When to use this

Most useful when:
- AI-assisted coding is a regular part of the workflow.
- Repeated context explanation across sessions is costly.
- Multiple agents or contributors need to work from the same architectural assumptions.
- Deterministic and auditable workflows matter.

Less useful for very small, short-lived prototypes where maintaining structured context exceeds the value of reuse.

---

## Versions

| Version | Highlights |
|---|---|
| v0.1 | Initial concept — context documents in `agents/` |
| v0.2 | Structured specs and task files |
| v0.3 | Framework contract (`.specnative/`), `pipelines/`, `install.py`, TOML optional, `status` command |
| v0.4 | MCP server — resources, tools, and prompts for Claude Code, Claude Desktop, OpenCode, Codex |
| v0.4.7–v0.4.9 | `--reinstall` flag · Auto-generate `opencode.json` · Profile documentation improved |
| v0.5.0 | `agents/` → `spec-native/` · tasks/workflows/pipelines consolidated · `SESSION.md` · Multi-agent continuity tools |
| v0.6.0 | Native agent commands (`/spec-init`, `/spec-update`, `/spec-status`, `/spec-handoff`) · `codex.toml` · `opencode.json` prompts · `specnative init/update` CLI |
| v0.6.1 | `read_template()` · `update_section()` — safe incremental doc updates, Copilot compatible |
| v0.6.2 | Fix `opencode.json` schema compliance (`command` key, `instructions` for AGENTS.md auto-load) |
| **v0.7.0** | **Archetypes (`java-hexagonal` built-in) · Spec templates · Decision snippets · `.specnative/archetypes/` + `.specnative/templates/`** |
| **v0.8.0** | **Short `/spec` workflow · Skills · Markdown backlog · Context indexes · GitHub Projects export plan** |
<!-- END_VERSIONS -->

---

## License

License information will be added by the project maintainers.
