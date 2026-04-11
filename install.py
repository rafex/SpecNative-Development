#!/usr/bin/env python3
"""
SpecNative Development installer.

Downloads and installs the SpecNative template into an existing git
repository on a dedicated branch, without touching uncommitted work.

Usage:
    python3 install.py
    python3 install.py --target /path/to/repo
    python3 install.py --include-examples
    python3 install.py --profile full --branch specnative/setup

The installer:
  1. Validates the target is a clean git repository.
  2. Creates a dedicated branch.
  3. Downloads template files from the SpecNative GitHub release.
  4. Writes them to the target repository.

Options:
    --target PATH         Target repository path (default: current directory)
    --version VERSION     SpecNative version to install (default: latest release)
    --profile PROFILE     minimal (default) or full (also installs README.md)
    --include-examples    Install the authentication example initiative
    --branch NAME         Branch to create (default: specnative/install-VERSION)
    --force               Overwrite existing files
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request

REPO = "rafex/SpecNative-Development"
VERSION = "dev"  # replaced by CI on release

TEMPLATE_ROOT = "Template-Project-Agents-AI"
INSTALL_BRANCH_PREFIX = "specnative/install"

PATHS_MINIMAL = [
    "AGENTS.md",
    "agents/README.md",
    "agents/PRODUCT.md",
    "agents/ARCHITECTURE.md",
    "agents/STACK.md",
    "agents/CONVENTIONS.md",
    "agents/COMMANDS.md",
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
    ".specnative/README.md",
    ".specnative/CLI.md",
    ".specnative/SCHEMA.md",
]

PATHS_EXAMPLES = [
    "agents/specs/authentication/README.md",
    "agents/specs/authentication/SPEC.md",
    "tasks/authentication/README.md",
    "tasks/authentication/TASKS.md",
]


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

    paths = list(PATHS_MINIMAL)
    if profile == "full" and not (target / "README.md").exists():
        paths.append("README.md")
    if include_examples:
        paths.extend(PATHS_EXAMPLES)

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
        print(f"\n{len(errors)} file(s) failed to download.", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nSpecNative {version} installed on branch '{branch}'.\n"
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
        choices=("minimal", "full"),
        default="minimal",
        help="minimal (default) or full (also installs README.md if absent)",
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    version = resolve_version(args.version)
    branch = args.branch or f"{INSTALL_BRANCH_PREFIX}-{version}"
    target = Path(args.target).resolve()

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
