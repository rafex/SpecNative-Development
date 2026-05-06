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

Profiles:
    context   Living AI context layer only — AGENTS.md + project docs.
              No spec lifecycle, no tasks, no pipelines. Ideal for solo
              developers or any project that wants an AI agent to understand
              its codebase without extra process overhead.

    spec      Spec-driven development without CI/CD pipelines. Adds the full
              initiative lifecycle: specs, tasks, workflows, decisions, roadmap,
              and traceability. Ideal for startups and solo developers building
              features spec-first.

    team      Full spec lifecycle plus pipeline documentation (CI/CD). Adds
              schema governance and the CLI reference. Ideal for small-to-medium
              teams that review pull requests and maintain automated pipelines.

    platform  Everything in team plus README.md (if absent) and example
              initiatives. Ideal for open-source projects, enterprise platforms,
              or multi-team organisations that need reference implementations.

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

# context — living AI context layer (AGENTS.md philosophy)
# Just enough for an agent to understand the project. No process overhead.
PATHS_CONTEXT = [
    "AGENTS.md",
    "agents/README.md",
    "agents/PRODUCT.md",
    "agents/ARCHITECTURE.md",
    "agents/STACK.md",
    "agents/CONVENTIONS.md",
    "agents/COMMANDS.md",
    ".specnative/README.md",
    ".specnative/MCP.md",
]

# spec — full initiative lifecycle without CI/CD (Agent OS philosophy)
# Adds specs, tasks, workflows, decisions, roadmap, and traceability.
PATHS_SPEC = [
    "agents/DECISIONS.md",
    "agents/ROADMAP.md",
    "agents/SPEC.md",
    "agents/TRACEABILITY.md",
    "agents/specs/README.md",
    "tasks/README.md",
    "tasks/TASKS.template.md",
    "workflows/README.md",
    "workflows/IMPLEMENTATION.md",
    "workflows/PLANNING.md",
    "workflows/REVIEW.md",
]

# team — adds CI/CD pipeline docs and schema governance
PATHS_TEAM = [
    "pipelines/README.md",
    "pipelines/CI.md",
    "pipelines/CD.md",
    ".specnative/CLI.md",
    ".specnative/SCHEMA.md",
]

# platform — example initiatives (also adds README.md if absent)
PATHS_EXAMPLES = [
    "agents/specs/authentication/README.md",
    "agents/specs/authentication/SPEC.md",
    "tasks/authentication/README.md",
    "tasks/authentication/TASKS.md",
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
            [str(python), "-m", "pip", "install", "mcp"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        errors.append(f"mcp install failed: {exc.stderr.strip()}")

    return venv_dir, errors


# ---------------------------------------------------------------------------
# Reinstall MCP only
# ---------------------------------------------------------------------------

def reinstall_mcp(target: Path, version: str) -> None:
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

    print(json.dumps({
        "version": version,
        "target": str(target),
        "mode": "reinstall_mcp_only",
        "venv": str(venv_dir),
        "venv_python": venv_python,
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
        reinstall_mcp(target=target, version=version)
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
