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
  5. Creates .specnative/.venv and installs the mcp package.

--reinstall mode:
  Reinstalls only the MCP server and venv without touching other files.
  Does not require a clean worktree. Use this to repair a broken MCP.
  Usage: python3 install.py --reinstall [--target /path/to/repo]

Profiles (each layer is cumulative):

    context   AI context layer — enough for an agent to understand and
              navigate the project. It installs the required document indexes
              but no task/example content.
              Every profile also installs native agent commands:
              .claude/commands/spec-*.md, codex.toml and a shared command manifest.
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
import re
import subprocess
import shutil
import sys
import venv as _venv
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
VENV_GITIGNORE_ENTRY = ".specnative/.venv/"
VENV_GITIGNORE_COMMENT = "# SpecNative — venv is generated; do not commit\n"


def purge_stale_venv(target: Path) -> None:
    """Remove a leftover .specnative/.venv/ before git operations.

    A failed previous install may leave venv files (with Windows CRLF
    line endings, binary data, etc.) that cause 'fatal: CRLF would be
    replaced by LF' errors when git inspects the working tree.
    The venv is always recreated by setup_venv(), so it is safe to delete.
    """
    venv_dir = target / ".specnative" / ".venv"
    if venv_dir.exists():
        print("Removing stale .specnative/.venv/ before git operations …",
              file=sys.stderr, flush=True)
        shutil.rmtree(venv_dir)


def ensure_venv_gitignore(target: Path, created: list[str]) -> None:
    """Add .specnative/.venv/ to .gitignore so git never tracks venv files."""
    gitignore = target / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if VENV_GITIGNORE_ENTRY in content:
            return  # already ignored
        updated = (content.rstrip("\n")
                   + f"\n\n{VENV_GITIGNORE_COMMENT}{VENV_GITIGNORE_ENTRY}\n")
        gitignore.write_text(updated, encoding="utf-8")
        created.append(".gitignore")
    else:
        gitignore.write_text(
            f"{VENV_GITIGNORE_COMMENT}{VENV_GITIGNORE_ENTRY}\n",
            encoding="utf-8",
        )
        created.append(".gitignore")


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


def setup_venv(target: Path) -> tuple[Path, list[str]]:
    """Create .specnative/.venv with a Python >= 3.10, upgrade pip, install mcp."""
    venv_dir = target / ".specnative" / ".venv"
    errors: list[str] = []

    python_bin = find_python310()
    if python_bin is None:
        errors.append(
            "mcp requires Python >= 3.10 but none was found on this system.\n"
            "  Install Python 3.10+ (e.g. 'brew install python@3.12') then\n"
            "  re-run the installer with --force to retry the venv setup."
        )
        return venv_dir, errors

    print(f"Setting up .specnative/.venv (Python: {python_bin}) …",
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
        "# codex.toml — generated from the SpecNative command manifest.\n"
        "# Framework maintainers regenerate it from .specnative/commands.json.\n\n"
        "[mcp_servers.specnative]\n"
        'command = "./.specnative/.venv/bin/python3"\n'
        'args = ["./.specnative/specnative_mcp.py"]\n'
        'type = "stdio"\n'
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
        if not re.search(r"^\[mcp_servers\.specnative\]\s*$", content, re.MULTILINE):
            additions.append(
                "\n[mcp_servers.specnative]\n"
                'command = "./.specnative/.venv/bin/python3"\n'
                'args = ["./.specnative/specnative_mcp.py"]\n'
                'type = "stdio"\n'
            )
        for name, command in commands.items():
            pattern = rf"^\[prompts\.{re.escape(name)}\]\s*$"
            if not re.search(pattern, content, re.MULTILINE):
                additions.append(_codex_prompt_block(name, command))
        if additions:
            codex_file.write_text(content.rstrip() + "\n" + "".join(additions), encoding="utf-8")
            created.append("codex.toml (merged)")
    except OSError as exc:
        errors.append(f"Failed to update codex.toml safely: {exc}")


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


# ---------------------------------------------------------------------------
# Reinstall MCP only
# ---------------------------------------------------------------------------

def reinstall_mcp(target: Path, version: str, force: bool = False) -> None:
    """Repair MCP server and venv without touching other files.

    Does not require a clean worktree or create a git branch.
    Only reinstalls .specnative/specnative_mcp.py and .specnative/.venv.
    """
    ensure_git_repo(target)

    errors: list[str] = []

    print("Reinstalling MCP server …", file=sys.stderr, flush=True)

    # Download and write MCP server
    mcp_dest = target / ".specnative" / "specnative_mcp.py"
    mcp_url = release_asset_url(version, "specnative_mcp.py")
    try:
        mcp_content = download_file(mcp_url)
        mcp_dest.parent.mkdir(parents=True, exist_ok=True)
        mcp_dest.write_bytes(mcp_content)
        mcp_dest.chmod(0o755)
        print(f"✓ Downloaded .specnative/specnative_mcp.py", file=sys.stderr)
    except RuntimeError as exc:
        errors.append(str(exc))

    # Purge and recreate venv
    purge_stale_venv(target)
    venv_dir, venv_errors = setup_venv(target)
    errors.extend(venv_errors)

    if sys.platform == "win32":
        venv_python = str(venv_dir / "Scripts" / "python.exe")
    else:
        venv_python = str(venv_dir / "bin" / "python3")

    created: list[str] = []
    setup_mcp_configs(target, created, errors, force=force)

    print(json.dumps({
        "version": version,
        "target": str(target),
        "mode": "reinstall_mcp_only",
        "venv": str(venv_dir),
        "venv_python": venv_python,
        "created": created,
        "errors": errors,
    }, indent=2, ensure_ascii=False))

    if errors:
        print(f"\n{len(errors)} error(s) during MCP reinstall.", file=sys.stderr)
        sys.exit(1)

    print(
        f"\n✓ MCP reinstalled successfully.\n"
        f"MCP server : .specnative/specnative_mcp.py\n"
        f"Venv Python: {venv_python}\n"
        f"Configure your agent following: .specnative/MCP.md"
    )


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
    purge_stale_venv(target)      # remove leftover venv before git sees it
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

    ensure_venv_gitignore(target, created)  # add .venv to .gitignore early

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

    # Download MCP server into .specnative/
    mcp_dest = target / ".specnative" / "specnative_mcp.py"
    if mcp_dest.exists() and not force:
        skipped.append(".specnative/specnative_mcp.py")
    else:
        mcp_url = release_asset_url(version, "specnative_mcp.py")
        try:
            mcp_content = download_file(mcp_url)
            mcp_dest.parent.mkdir(parents=True, exist_ok=True)
            mcp_dest.write_bytes(mcp_content)
            mcp_dest.chmod(0o755)
            created.append(".specnative/specnative_mcp.py")
        except RuntimeError as exc:
            errors.append(str(exc))

    # Create .specnative/.venv and install mcp
    venv_dir, venv_errors = setup_venv(target)
    if sys.platform == "win32":
        venv_python = str(venv_dir / "Scripts" / "python.exe")
    else:
        venv_python = str(venv_dir / "bin" / "python3")
    errors.extend(venv_errors)

    # Create MCP configuration files for OpenCode and other clients
    setup_mcp_configs(target, created, errors, force=force)

    print(json.dumps({
        "version": version,
        "target": str(target),
        "branch": branch,
        "profile": profile,
        "include_examples": include_examples,
        "created": created,
        "skipped_existing": skipped,
        "venv": str(venv_dir),
        "venv_python": venv_python,
        "errors": errors,
    }, indent=2, ensure_ascii=False))

    if errors:
        print(f"\n{len(errors)} error(s) during install.", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nSpecNative {version} installed on branch '{branch}'.\n"
        f"MCP server : .specnative/specnative_mcp.py\n"
        f"Venv Python: {venv_python}\n"
        f"Configure your agent following: .specnative/MCP.md\n"
        f"Review the files, then merge the branch into your main branch."
    )


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    version = resolve_version(args.version)
    target = Path(args.target).resolve()

    if args.reinstall:
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
