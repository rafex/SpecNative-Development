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

---

## Quick Start

### Install into an existing repository

```bash
curl -sSL https://github.com/rafex/SpecNative-Development/releases/latest/download/install.py \
  | python3 - --target /path/to/your/repo --profile minimal
```

Or download once and run locally:

```bash
python3 install.py --target /path/to/your/repo --profile minimal --include-examples
```

### Connect via MCP (Claude Code, Claude Desktop, OpenCode, Codex)

```bash
pip install mcp

# Claude Code
claude mcp add specnative \
  python3 /path/to/SpecNative-Development/tools/specnative_mcp.py \
  -- --repo /path/to/your/project
```

See [`.specnative/MCP.md`](./Template-Project-Agents-AI/.specnative/MCP.md) for full configuration per agent.

---

## Repository layout

```
Template-Project-Agents-AI/
├── AGENTS.md              # Agent operating contract — read first
├── README.md              # Navigation index
├── agents/
│   ├── PRODUCT.md         # Problem, users, goals (permanent)
│   ├── ARCHITECTURE.md    # System structure and boundaries
│   ├── STACK.md           # Tech stack and version constraints
│   ├── CONVENTIONS.md     # Code rules, naming, testing
│   ├── COMMANDS.md        # Project-specific dev/test/build commands
│   ├── SPEC.md            # Active spec (or entry point to specs/)
│   ├── DECISIONS.md       # Persistent decisions and trade-offs
│   ├── ROADMAP.md         # Temporal direction
│   ├── TRACEABILITY.md    # Cross-artifact links
│   └── specs/<initiative>/SPEC.md
├── tasks/<initiative>/TASKS.md
├── workflows/             # PLANNING.md, IMPLEMENTATION.md, REVIEW.md
├── pipelines/             # CI.md, CD.md — CI/CD context
└── .specnative/           # Framework infrastructure
    ├── SCHEMA.md          # Framework contract (required files, states)
    ├── CLI.md             # CLI and MCP reference
    └── MCP.md             # MCP server configuration per agent
```

### Document ownership — one truth per document

| Document | Owns |
|---|---|
| `PRODUCT.md` | Problem, users, goals, non-goals |
| `SPEC.md` | What must be built in this initiative (time-bounded) |
| `DECISIONS.md` | Persistent trade-offs future initiatives must respect |
| `ROADMAP.md` | Temporal direction without implementation detail |
| `ARCHITECTURE.md` | System structure, modules, boundaries |
| `CONVENTIONS.md` | Naming, style, testing, commit conventions |
| `COMMANDS.md` | Project commands only — never framework CLI |
| `tasks/**/TASKS.md` | Executable plan with state, owner, close criteria |
| `TRACEABILITY.md` | Cross-artifact links (update at initiative close) |
| `pipelines/CI.md` | Automated gate definitions |
| `pipelines/CD.md` | Delivery process and environments |

---

## Framework tooling

### CLI — `tools/specnative.py`

```bash
python3 specnative.py status              # Spec and task state overview
python3 specnative.py validate            # Check required files and TOML
python3 specnative.py export-index        # Export specs/tasks as JSON
python3 specnative.py export-traceability # Export traceability matrix as JSON
python3 specnative.py install --target /path/to/repo --profile minimal
```

### MCP server — `tools/specnative_mcp.py` (v0.4)

Exposes the repository as MCP resources, tools, and prompts so any MCP-compatible
agent works spec-first without manually navigating the file tree.

**Resources** — context documents by URI:

```
spec://agents                  → AGENTS.md
spec://context/product         → agents/PRODUCT.md
spec://context/architecture    → agents/ARCHITECTURE.md
spec://context/decisions       → agents/DECISIONS.md
spec://context/roadmap         → agents/ROADMAP.md
spec://pipelines/ci            → pipelines/CI.md
spec://schema                  → .specnative/SCHEMA.md
# … and more (see MCP.md)
```

**Tools**: `status`, `validate`, `list_specs`, `list_tasks`, `read_spec`, `read_context`, `export_index`

**Prompts**: `start_initiative`, `plan_tasks`, `implement_task`, `review_against_spec`, `record_decision`, `close_initiative`

#### Configure per agent

**Claude Code**
```bash
claude mcp add specnative \
  python3 /path/to/SpecNative-Development/tools/specnative_mcp.py \
  -- --repo /path/to/project
```

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "specnative": {
      "command": "python3",
      "args": ["/path/to/specnative_mcp.py", "--repo", "/path/to/project"]
    }
  }
}
```

**OpenCode** — `.opencode/config.json`:
```json
{
  "mcp": {
    "servers": {
      "specnative": {
        "command": "python3",
        "args": ["/path/to/specnative_mcp.py", "--repo", "/path/to/project"]
      }
    }
  }
}
```

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

1. Read `AGENTS.md` — agent operating contract.
2. Check `agents/ROADMAP.md` — confirm initiative aligns with direction.
3. Read `agents/PRODUCT.md` + relevant technical context.
4. Read `agents/DECISIONS.md` — respect persistent trade-offs.
5. Review or create a `SPEC.md`.
6. Derive tasks in `tasks/`.
7. Implement following `workflows/IMPLEMENTATION.md`.
8. Record persistent decisions in `DECISIONS.md`.
9. Update `TRACEABILITY.md` when the initiative closes.

**With the MCP server**, agents access all of this through typed resources and structured prompts instead of manual file navigation.

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

---

## License

License information will be added by the project maintainers.
