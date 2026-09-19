#!/usr/bin/env python3
"""
SpecNative Development installer.

Downloads and installs the SpecNative template into an existing git
repository on a dedicated branch, without touching uncommitted work.

Usage:
    python3 install.py
    python3 install.py --target /path/to/repo
    python3 install.py --profile spec
    python3 install.py --profile team --branch specnative/setup
    python3 install.py --profile platform --include-examples
    python3 install.py --reinstall                              # Repair MCP only

The installer:
  1. Validates the target is a clean git repository.
  2. Creates a dedicated branch.
  3. Downloads template files from the SpecNative GitHub release.
  4. Writes them to the target repository.
  5. Installs only the repository contract and agent prompts.

--global mode:
  Installs one MCP server and venv for the current user, then configures
  supported agent clients globally. Use --migrate-local to remove recognised
  legacy runtime files from one repository after the global install.

Profiles (each layer is cumulative):

    context   AI context layer — enough for an agent to understand and
              navigate the project. It installs the required document indexes
              but no task/example content.
              Every profile also installs native agent commands:
              .claude/commands/spec-*.md, .codex/config.toml, codex.toml and a
              shared command manifest.
              Files: AGENTS.md, spec-native/{README,PRODUCT,ARCHITECTURE,STACK,
                     CONVENTIONS,COMMANDS,SESSION}.md, .specnative/{README,MCP}.md

    spec      Adds the full initiative lifecycle on top of context: specs,
              tasks, workflows, decisions, roadmap, and traceability.
              Ideal for solo developers and startups building spec-first.
              Adds: spec-native/{DECISIONS,ROADMAP,TRACEABILITY}.md,
                    spec-native/specs/README.md,
                    spec-native/intake/{README,IDEAS}.md,
                    spec-native/tasks/{README,TASKS.template}.md,
                    spec-native/backlog/README.md,
                    spec-native/workflows/{README,IMPLEMENTATION,PLANNING,REVIEW}.md

    team      Adds CI/CD pipeline docs, schema governance, archetypes and
              templates on top of spec. Ideal for teams that run automated
              pipelines and want reusable project starting points.
              Adds: spec-native/pipelines/{README,CI,CD}.md,
                    .specnative/{CLI,SCHEMA}.md,
                    .specnative/integrations/github-project.toml.example,
                    .specnative/archetypes/README.md,
                    .specnative/templates/{README,specs/README,decisions/README}.md

    platform  Everything in team plus README.md (if absent) and reference
              example initiatives. Ideal for open-source projects or
              organisations that need working examples to onboard contributors.
              Adds: README.md (if missing),
                    spec-native/specs/authentication/{README,SPEC}.md,
                    spec-native/tasks/authentication/{README,TASKS}.md

Options:
    --target PATH         Target repository path (default: current directory)
    --version VERSION     SpecNative version to install (default: latest release)
    --profile PROFILE     context | spec | team (default) | platform
    --include-examples    Add example initiatives to any profile
    --branch NAME         Branch to create (default: specnative/install-VERSION)
    --force               Overwrite existing files
    --reinstall           Repair MCP only (no branch, no worktree check)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import shutil
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request

REPO = "rafex/SpecNative-Development"
VERSION = "dev"  # replaced by CI on release

TEMPLATE_ROOT = "Template-Project-Agents-AI"
INSTALL_BRANCH_PREFIX = "specnative/install"

# ---------------------------------------------------------------------------
# Profile file lists (each layer is cumulative)
# ---------------------------------------------------------------------------

# context — AI context layer. Includes all navigation and core context files so
# the installed MCP can validate the repository. It does not include task
# templates, pipeline details, archetypes, or example initiatives.
# Includes native commands for Claude Code, OpenCode and Codex out of the box.
PATHS_CONTEXT = [
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
    "spec-native/intake/README.md",
    "spec-native/intake/IDEAS.md",
    "spec-native/tasks/README.md",
    "spec-native/workflows/README.md",
    "spec-native/workflows/IMPLEMENTATION.md",
    "spec-native/pipelines/README.md",
    ".specnative/README.md",
    ".specnative/MCP.md",
    ".specnative/SCHEMA.md",
    ".specnative/commands.json",
    ".claude/skills/specnative-workflow/SKILL.md",
    ".codex/skills/specnative-workflow/SKILL.md",
]

# spec — adds executable task templates and complete planning/review workflows
# on top of the context skeleton.
PATHS_SPEC = [
    "spec-native/DECISIONS.md",
    "spec-native/ROADMAP.md",
    "spec-native/TRACEABILITY.md",
    "spec-native/specs/README.md",
    "spec-native/tasks/README.md",
    "spec-native/tasks/TASKS.template.md",
    "spec-native/backlog/README.md",
    "spec-native/workflows/README.md",
    "spec-native/workflows/IMPLEMENTATION.md",
    "spec-native/workflows/PLANNING.md",
    "spec-native/workflows/REVIEW.md",
]

# team — adds CI/CD pipeline docs, schema governance, archetypes and templates.
PATHS_TEAM = [
    "spec-native/pipelines/README.md",
    "spec-native/pipelines/CI.md",
    "spec-native/pipelines/CD.md",
    ".specnative/CLI.md",
    ".specnative/SCHEMA.md",
    ".specnative/archetypes/README.md",
    ".specnative/templates/README.md",
    ".specnative/templates/specs/README.md",
    ".specnative/templates/decisions/README.md",
    ".specnative/integrations/github-project.toml.example",
]

# platform — adds README.md (if absent) and reference example initiatives.
PATHS_EXAMPLES = [
    "spec-native/specs/authentication/README.md",
    "spec-native/specs/authentication/SPEC.md",
    "spec-native/tasks/authentication/README.md",
    "spec-native/tasks/authentication/TASKS.md",
]

PROFILE_PATHS: dict[str, list[str]] = {
    "context": PATHS_CONTEXT,
    "spec":    PATHS_CONTEXT + PATHS_SPEC,
    "team":    PATHS_CONTEXT + PATHS_SPEC + PATHS_TEAM,
    "platform": PATHS_CONTEXT + PATHS_SPEC + PATHS_TEAM,
}

DEFAULT_PROFILE = "team"


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def resolve_version(version: str) -> str:
    """Return the version string to use. Fetches latest release if needed."""
    if version != "dev":
        return version
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        req = Request(url, headers={"Accept": "application/vnd.github+json"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        tag = data.get("tag_name", "")
        if not tag:
            raise ValueError("GitHub API returned no tag_name")
        return tag
    except (URLError, ValueError) as exc:
        print(f"Error: could not fetch latest release from GitHub: {exc}", file=sys.stderr)
        print("Specify a version with --version (e.g. --version v0.3)", file=sys.stderr)
        sys.exit(1)


def raw_url(version: str, relative: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{REPO}/refs/tags/{version}"
        f"/{TEMPLATE_ROOT}/{relative}"
    )


def release_asset_url(version: str, filename: str) -> str:
    return f"https://github.com/{REPO}/releases/download/{version}/{filename}"


def download_file(url: str) -> bytes:
    try:
        with urlopen(url, timeout=15) as resp:
            if resp.status != 200:
                raise URLError(f"HTTP {resp.status}")
            return resp.read()
    except URLError as exc:
        raise RuntimeError(f"download failed: {url}\n  {exc}") from exc


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def ensure_git_repo(target: Path) -> None:
    if not target.exists():
        print(f"Error: path does not exist: {target}", file=sys.stderr)
        sys.exit(1)
    try:
        result = run_git(["rev-parse", "--is-inside-work-tree"], cwd=target)
    except subprocess.CalledProcessError:
        print(f"Error: not a git repository: {target}", file=sys.stderr)
        sys.exit(1)
    if result.stdout.strip() != "true":
        print(f"Error: not inside a git work tree: {target}", file=sys.stderr)
        sys.exit(1)


def ensure_clean_worktree(target: Path) -> None:
    result = run_git(["status", "--porcelain"], cwd=target)
    if result.stdout.strip():
        print(
            "Error: target repository has uncommitted changes.\n"
            "Commit or stash them before running the installer.",
            file=sys.stderr,
        )
        sys.exit(1)


def create_branch(target: Path, branch: str) -> None:
    existing = run_git(["branch", "--list", branch], cwd=target)
    if existing.stdout.strip():
        print(f"Error: branch already exists: {branch}", file=sys.stderr)
        print("Choose a different name with --branch or delete it first.", file=sys.stderr)
        sys.exit(1)
    run_git(["checkout", "-b", branch], cwd=target)


# ---------------------------------------------------------------------------
# Venv helpers
# ---------------------------------------------------------------------------

MCP_MIN_PYTHON = (3, 10)


def find_python310() -> str | None:
    """Return the path to a Python >= 3.10 interpreter, or None if not found.

    Tries the current interpreter first, then common versioned names so that
    systems whose default python3 is older (e.g. macOS with Python 3.9) can
    still build a working venv for mcp.
    """
    if sys.version_info >= MCP_MIN_PYTHON:
        return sys.executable

    candidates: list[str] = []
    # Prefer explicit versioned names (newest first)
    for minor in range(14, 9, -1):
        candidates.append(f"python3.{minor}")
    candidates += ["python3", "python"]

    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "-c",
                 "import sys; print(sys.version_info >= (3, 10))"],
                capture_output=True, text=True, check=True, timeout=5,
            )
            if result.stdout.strip() == "True":
                which = subprocess.run(
                    ["which", candidate],
                    capture_output=True, text=True, check=True,
                )
                return which.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired):
            continue
    return None


def setup_global_venv(runtime_root: Path) -> tuple[Path, list[str]]:
    """Create the single user-scoped venv used by every SpecNative repository."""
    venv_dir = runtime_root / ".venv"
    errors: list[str] = []

    python_bin = find_python310()
    if python_bin is None:
        errors.append(
            "mcp requires Python >= 3.10 but none was found on this system.\n"
            "  Install Python 3.10+ (e.g. 'brew install python@3.12') then\n"
            "  re-run the installer with --force to retry the venv setup."
        )
        return venv_dir, errors

    print(f"Setting up global SpecNative venv (Python: {python_bin}) …",
          file=sys.stderr, flush=True)
    try:
        subprocess.run(
            [python_bin, "-m", "venv", str(venv_dir)],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        errors.append(f"venv creation failed: {exc.stderr.strip()}")
        return venv_dir, errors

    python = (
        venv_dir / ("Scripts" if sys.platform == "win32" else "bin") /
        ("python.exe" if sys.platform == "win32" else "python3")
    )
    if not python.exists():
        errors.append(f"venv python not found: {python}")
        return venv_dir, errors

    print("Upgrading pip …", file=sys.stderr, flush=True)
    try:
        subprocess.run(
            [str(python), "-m", "pip", "install", "-U", "pip"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        errors.append(f"pip upgrade failed: {exc.stderr.strip()}")

    print("Installing mcp …", file=sys.stderr, flush=True)
    try:
        subprocess.run(
            # The server uses the FastMCP 1.x API. Keep installations aligned
            # with the version exercised by the repository CI.
            [str(python), "-m", "pip", "install", "mcp>=1.0,<2.0"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        errors.append(f"mcp install failed: {exc.stderr.strip()}")

    return venv_dir, errors


# ---------------------------------------------------------------------------
# MCP client configuration
# ---------------------------------------------------------------------------

def _load_agent_commands(target: Path) -> dict[str, dict[str, str]]:
    """Load the command manifest shared by Claude, Codex and OpenCode."""
    manifest_path = target / ".specnative" / "commands.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_commands = data.get("commands")
    if not isinstance(raw_commands, list):
        raise ValueError("commands.json must contain a commands array")
    commands: dict[str, dict[str, str]] = {}
    for entry in raw_commands:
        if not isinstance(entry, dict):
            raise ValueError("each command manifest entry must be an object")
        name = entry.get("name")
        description = entry.get("description")
        prompt = entry.get("prompt")
        if not all(isinstance(value, str) and value for value in (name, description, prompt)):
            raise ValueError("each command requires name, description and prompt")
        if name in commands or not re.fullmatch(r"spec(?:-[a-z0-9]+)*", name):
            raise ValueError(f"invalid or duplicate command name: {name!r}")
        commands[name] = {
            "description": description,
            "prompt": prompt,
            # OpenCode receives the request as command input; keep this wording
            # runtime-neutral instead of exposing Claude's $ARGUMENTS token.
            "template": prompt.replace("$ARGUMENTS", "la solicitud del desarrollador"),
        }
    return commands


def _codex_prompt_block(name: str, command: dict[str, str]) -> str:
    prompt = command["template"].replace('"""', '\\\"\\\"\\\"')
    return (
        f"\n[prompts.{name}]\n"
        f"description = {json.dumps(command['description'], ensure_ascii=False)}\n"
        f'prompt = """\n{prompt}\n"""\n'
    )


def _write_claude_commands(
    target: Path,
    commands: dict[str, dict[str, str]],
    created: list[str],
    skipped: list[str],
    force: bool,
) -> None:
    """Generate Claude slash commands from the installed command manifest."""
    command_dir = target / ".claude" / "commands"
    for name, command in commands.items():
        destination = command_dir / f"{name}.md"
        relative = str(destination.relative_to(target))
        if destination.exists() and not force:
            skipped.append(relative)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(command["prompt"].strip() + "\n", encoding="utf-8")
        created.append(relative)


def _default_codex_config(commands: dict[str, dict[str, str]]) -> str:
    content = (
        "# codex.toml — prompts generated from the SpecNative command manifest.\n"
        "# Framework maintainers regenerate it from .specnative/commands.json.\n"
    )
    return content + "".join(_codex_prompt_block(name, command) for name, command in commands.items())


def _merge_codex_prompts(
    target: Path,
    commands: dict[str, dict[str, str]],
    created: list[str],
    errors: list[str],
) -> None:
    """Add missing managed SpecNative prompts without replacing user Codex config."""
    codex_file = target / "codex.toml"
    if not codex_file.exists():
        codex_file.write_text(_default_codex_config(commands), encoding="utf-8")
        created.append("codex.toml")
        return
    try:
        content = codex_file.read_text(encoding="utf-8")
        additions = []
        for name, command in commands.items():
            pattern = rf"^\[prompts\.{re.escape(name)}\]\s*$"
            if not re.search(pattern, content, re.MULTILINE):
                additions.append(_codex_prompt_block(name, command))
        if additions:
            codex_file.write_text(content.rstrip() + "\n" + "".join(additions), encoding="utf-8")
            created.append("codex.toml (merged)")
    except OSError as exc:
        errors.append(f"Failed to update codex.toml safely: {exc}")


def _codex_mcp_config(target: Path) -> str:
    """Render the project-scoped Codex MCP configuration with absolute paths."""
    target = target.resolve()
    if sys.platform == "win32":
        python = target / ".specnative" / ".venv" / "Scripts" / "python.exe"
    else:
        python = target / ".specnative" / ".venv" / "bin" / "python3"
    server = target / ".specnative" / "specnative_mcp.py"
    quoted = lambda value: json.dumps(str(value), ensure_ascii=False)
    return (
        "# Generated by SpecNative. Codex loads project MCP servers from this file.\n"
        "# Keep the paths absolute so the server works from any Codex surface.\n\n"
        "[mcp_servers.specnative]\n"
        f"command = {quoted(python)}\n"
        f"args = [{quoted(server)}, \"--repo\", {quoted(target)}]\n"
        f"cwd = {quoted(target)}\n"
        "enabled = true\n"
        "startup_timeout_sec = 30\n"
    )


def _merge_codex_mcp_config(
    target: Path,
    created: list[str],
    errors: list[str],
    force: bool,
) -> None:
    """Create or update the project-scoped Codex MCP configuration safely."""
    codex_dir = target / ".codex"
    codex_file = codex_dir / "config.toml"
    rendered = _codex_mcp_config(target)
    try:
        if not codex_file.exists():
            codex_dir.mkdir(parents=True, exist_ok=True)
            codex_file.write_text(rendered, encoding="utf-8")
            created.append(".codex/config.toml")
            return

        content = codex_file.read_text(encoding="utf-8")
        if re.search(r"^\[mcp_servers\.specnative\]\s*$", content, re.MULTILINE):
            if force:
                content = re.sub(
                    r"(?ms)^\[mcp_servers\.specnative\]\s*.*?(?=^\[|\Z)",
                    rendered,
                    content,
                )
                codex_file.write_text(content.rstrip() + "\n", encoding="utf-8")
                created.append(".codex/config.toml (updated)")
            return

        codex_file.write_text(content.rstrip() + "\n\n" + rendered, encoding="utf-8")
        created.append(".codex/config.toml (merged)")
    except (OSError, re.error) as exc:
        errors.append(f"Failed to update .codex/config.toml safely: {exc}")


def setup_mcp_configs(
    target: Path,
    created: list[str],
    errors: list[str],
    force: bool = False,
) -> None:
    """Create MCP configuration files for OpenCode, Claude Desktop, and Codex.

    opencode.json schema reference: https://opencode.ai/config.json
    Custom commands live under the 'command' key (not 'prompts').
    The 'instructions' key tells OpenCode to auto-load context files.
    """
    venv_python = str(target / ".specnative" / (".venv/Scripts/python3" if sys.platform == "win32" else ".venv/bin/python3"))

    # OpenCode — MCP server + custom commands + auto-loaded instructions
    # Schema: https://opencode.ai/config.json
    # 'command' keys use 'template' (required) + 'description' (optional)
    # 'instructions' auto-loads files as context in every session
    try:
        agent_commands = _load_agent_commands(target)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Failed to load SpecNative command manifest: {exc}")
        return

    _write_claude_commands(target, agent_commands, created, skipped=[], force=force)
    _merge_codex_prompts(target, agent_commands, created, errors)
    _merge_codex_mcp_config(target, created, errors, force=force)

    opencode_config = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": [
            "AGENTS.md",
            "spec-native/README.md",
        ],
        "mcp": {
            "specnative": {
                "type": "local",
                "enabled": True,
                "command": [
                    venv_python,
                    "./.specnative/specnative_mcp.py",
                ],
            }
        },
        "command": agent_commands,
    }

    opencode_file = target / "opencode.json"
    existed_before = opencode_file.exists()
    try:
        if not existed_before or force:
            merged_config = opencode_config
        else:
            with open(opencode_file, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, dict):
                raise ValueError("root value must be a JSON object")

            merged_config = dict(existing)
            instructions = merged_config.get("instructions", [])
            if not isinstance(instructions, list):
                raise ValueError("'instructions' must be a JSON array")
            merged_config["instructions"] = list(instructions)
            for instruction in opencode_config["instructions"]:
                if instruction not in merged_config["instructions"]:
                    merged_config["instructions"].append(instruction)

            mcp = merged_config.get("mcp", {})
            if not isinstance(mcp, dict):
                raise ValueError("'mcp' must be a JSON object")
            merged_config["mcp"] = dict(mcp)
            merged_config["mcp"].setdefault("specnative", opencode_config["mcp"]["specnative"])

            commands = merged_config.get("command", {})
            if not isinstance(commands, dict):
                raise ValueError("'command' must be a JSON object")
            merged_config["command"] = dict(commands)
            for name, command in opencode_config["command"].items():
                merged_config["command"].setdefault(name, command)

        with open(opencode_file, "w", encoding="utf-8") as f:
            json.dump(merged_config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        created.append("opencode.json" if not existed_before else "opencode.json (merged)")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Failed to update opencode.json safely: {exc}")


def setup_agent_commands(target: Path, created: list[str], errors: list[str], force: bool = False) -> None:
    """Install repository-owned prompts and commands, never an MCP runtime/config."""
    try:
        commands = _load_agent_commands(target)
        _write_claude_commands(target, commands, created, skipped=[], force=force)
        _merge_codex_prompts(target, commands, created, errors)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Failed to load SpecNative command manifest: {exc}")


def global_runtime_root() -> Path:
    """Return the platform-native per-user location for the shared MCP runtime."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "SpecNative"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SpecNative"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "specnative"


def _global_python(runtime_root: Path) -> Path:
    return runtime_root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python3")


def _global_server(runtime_root: Path) -> Path:
    return runtime_root / "specnative_mcp.py"


def _merge_toml_server(config: Path, rendered: str, created: list[str], errors: list[str]) -> None:
    """Add or replace the managed server table while preserving other TOML tables."""
    try:
        content = config.read_text(encoding="utf-8") if config.exists() else ""
        pattern = r"(?ms)^\[mcp_servers\.specnative\]\s*.*?(?=^\[|\Z)"
        updated = re.sub(pattern, rendered, content) if re.search(pattern, content) else content.rstrip() + ("\n\n" if content.strip() else "") + rendered
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(updated.rstrip() + "\n", encoding="utf-8")
        created.append(str(config))
    except (OSError, re.error) as exc:
        errors.append(f"Failed to update {config}: {exc}")


def setup_global_mcp_configs(runtime_root: Path, created: list[str], errors: list[str]) -> None:
    """Register the shared executable in user-scoped MCP configurations."""
    python, server = _global_python(runtime_root), _global_server(runtime_root)
    quoted = lambda value: json.dumps(str(value), ensure_ascii=False)
    _merge_toml_server(
        Path.home() / ".codex" / "config.toml",
        "[mcp_servers.specnative]\n"
        f"command = {quoted(python)}\nargs = [{quoted(server)}]\n"
        "enabled = true\nstartup_timeout_sec = 30\n",
        created, errors,
    )

    opencode = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "opencode" / "opencode.json"
    try:
        data = json.loads(opencode.read_text(encoding="utf-8")) if opencode.exists() else {"$schema": "https://opencode.ai/config.json"}
        mcp_config = data.setdefault("mcp", {})
        servers = mcp_config.setdefault("servers", {})
        servers["specnative"] = {"type": "local", "command": [str(python), str(server)]}
        opencode.parent.mkdir(parents=True, exist_ok=True)
        opencode.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(str(opencode))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Failed to update {opencode}: {exc}")

    if sys.platform == "darwin":
        desktop = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":
        desktop = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Claude" / "claude_desktop_config.json"
    else:
        desktop = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Claude" / "claude_desktop_config.json"
    try:
        desktop_data = json.loads(desktop.read_text(encoding="utf-8")) if desktop.exists() else {}
        desktop_data.setdefault("mcpServers", {})["specnative"] = {"command": str(python), "args": [str(server)]}
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(json.dumps(desktop_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(str(desktop))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Failed to update {desktop}: {exc}")

    claude = shutil.which("claude")
    if claude:
        try:
            subprocess.run([claude, "mcp", "add", "--scope", "user", "specnative", "--", str(python), str(server)], check=True, capture_output=True, text=True)
            created.append("Claude Code user MCP configuration")
        except subprocess.CalledProcessError as exc:
            errors.append(f"Failed to configure Claude Code: {exc.stderr.strip()}")


def install_global(version: str) -> None:
    """Install or update one MCP runtime and user-scoped client configurations."""
    runtime_root = global_runtime_root()
    runtime_root.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    created: list[str] = []
    try:
        _global_server(runtime_root).write_bytes(download_file(release_asset_url(version, "specnative_mcp.py")))
        _global_server(runtime_root).chmod(0o755)
        created.append(str(_global_server(runtime_root)))
    except RuntimeError as exc:
        errors.append(str(exc))
    _, venv_errors = setup_global_venv(runtime_root)
    errors.extend(venv_errors)
    setup_global_mcp_configs(runtime_root, created, errors)
    print(json.dumps({"version": version, "mode": "global", "runtime": str(runtime_root), "created": created, "errors": errors}, indent=2, ensure_ascii=False))
    if errors:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Reinstall MCP only
# ---------------------------------------------------------------------------

def reinstall_mcp(target: Path, version: str, force: bool = False) -> None:
    """Backward-compatible alias for the global MCP installer."""
    print("--reinstall is deprecated; installing the user-scoped MCP instead.", file=sys.stderr)
    install_global(version)


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install(
    target: Path,
    version: str,
    profile: str,
    include_examples: bool,
    branch: str,
    force: bool,
) -> None:
    ensure_git_repo(target)
    ensure_clean_worktree(target)
    create_branch(target, branch)

    paths = list(PROFILE_PATHS[profile])
    if profile == "platform" and not (target / "README.md").exists():
        paths.append("README.md")
    if include_examples or profile == "platform":
        for ex in PATHS_EXAMPLES:
            if ex not in paths:
                paths.append(ex)

    created: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for relative in paths:
        dest = target / relative
        if dest.exists() and not force:
            skipped.append(relative)
            continue
        url = raw_url(version, relative)
        try:
            content = download_file(url)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        created.append(relative)

    # Commands and prompts are project content; MCP runtime/configuration is global.
    setup_agent_commands(target, created, errors, force=force)

    print(json.dumps({
        "version": version,
        "target": str(target),
        "branch": branch,
        "profile": profile,
        "include_examples": include_examples,
        "created": created,
        "skipped_existing": skipped,
        "errors": errors,
    }, indent=2, ensure_ascii=False))

    if errors:
        print(f"\n{len(errors)} error(s) during install.", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nSpecNative {version} installed on branch '{branch}'.\n"
        f"Install the global MCP once with: python3 install.py --global\n"
        f"Review the files, then merge the branch into your main branch."
    )


def migrate_local_mcp(target: Path) -> None:
    """Remove only recognisable legacy SpecNative MCP artifacts from one repo."""
    removed: list[str] = []
    server = target / ".specnative" / "specnative_mcp.py"
    if server.exists() and "SpecNative MCP Server" in server.read_text(encoding="utf-8", errors="ignore"):
        server.unlink()
        removed.append(str(server.relative_to(target)))
    venv_dir = target / ".specnative" / ".venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
        removed.append(str(venv_dir.relative_to(target)))

    codex = target / ".codex" / "config.toml"
    if codex.exists():
        content = codex.read_text(encoding="utf-8")
        updated = re.sub(r"(?ms)^\[mcp_servers\.specnative\]\s*.*?(?=^\[|\Z)", "", content).strip()
        if updated != content.strip():
            if updated:
                codex.write_text(updated + "\n", encoding="utf-8")
            else:
                codex.unlink()
            removed.append(str(codex.relative_to(target)))

    opencode = target / "opencode.json"
    if opencode.exists():
        try:
            data = json.loads(opencode.read_text(encoding="utf-8"))
            mcp_config = data.get("mcp", {})
            if isinstance(mcp_config, dict) and "specnative" in mcp_config:
                del mcp_config["specnative"]
                if not mcp_config:
                    data.pop("mcp", None)
                opencode.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                removed.append(str(opencode.relative_to(target)))
        except json.JSONDecodeError:
            pass
    print(json.dumps({"mode": "migrate_local_mcp", "target": str(target), "removed": removed}, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the SpecNative template into a git repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Target repository path (default: current directory)",
    )
    parser.add_argument(
        "--version",
        default=VERSION,
        help="SpecNative version to install (default: latest release)",
    )
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILE_PATHS),
        default=DEFAULT_PROFILE,
        help=(
            "context — AI context layer only | "
            "spec — context + full initiative lifecycle | "
            "team — spec + CI/CD pipelines (default) | "
            "platform — team + README + examples"
        ),
    )
    parser.add_argument(
        "--include-examples",
        action="store_true",
        help="Install the authentication example initiative",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Branch to create in the target repository (default: specnative/install-VERSION)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="Repair MCP only (no branch, no worktree check)",
    )
    parser.add_argument(
        "--global",
        dest="global_install",
        action="store_true",
        help="Install or update the user-scoped SpecNative MCP and client configs",
    )
    parser.add_argument(
        "--migrate-local",
        action="store_true",
        help="Remove recognised legacy project-scoped MCP artifacts from --target",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    version = resolve_version(args.version)
    target = Path(args.target).resolve()

    if args.global_install:
        install_global(version)
        if args.migrate_local:
            migrate_local_mcp(target)
    elif args.migrate_local:
        migrate_local_mcp(target)
    elif args.reinstall:
        reinstall_mcp(target=target, version=version, force=args.force)
    else:
        branch = args.branch or f"{INSTALL_BRANCH_PREFIX}-{version}"
        install(
            target=target,
            version=version,
            profile=args.profile,
            include_examples=args.include_examples,
            branch=branch,
            force=args.force,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
