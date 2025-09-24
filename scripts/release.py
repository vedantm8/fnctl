#!/usr/bin/env python3
"""Interactive release helper for fnctl."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from getpass import getpass
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INIT = ROOT / "fnctl" / "__init__.py"
SETUP_PY = ROOT / "setup.py"
SERVER_PY = ROOT / "fnctl" / "server.py"

VERSION_PATTERN = re.compile(r'__version__\s*=\s*"([^"]+)"')
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def read_current_version() -> str:
    text = PACKAGE_INIT.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if not match:
        raise SystemExit("Could not find __version__ in fnctl/__init__.py")
    return match.group(1)


def bump_version(version: str, release_type: str) -> str:
    match = SEMVER_PATTERN.match(version)
    if not match:
        raise SystemExit(f"Current version '{version}' is not a valid SemVer string")
    major, minor, patch = (int(group) for group in match.groups())
    if release_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif release_type == "minor":
        minor += 1
        patch = 0
    elif release_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Unsupported release type: {release_type}")
    return f"{major}.{minor}.{patch}"


def prompt_release_type(current_version: str) -> str:
    while True:
        choice = input(
            "Release type [major/minor/patch/custom/keep] (default minor): "
        ).strip().lower()
        if not choice:
            choice = "minor"
        if choice in {"major", "ma", "m"}:
            return bump_version(current_version, "major")
        if choice in {"minor", "mi", "n"}:
            return bump_version(current_version, "minor")
        if choice in {"patch", "p"}:
            return bump_version(current_version, "patch")
        if choice in {"custom", "c"}:
            return prompt_custom_version()
        if choice in {"keep", "same", "current", "k"}:
            print("Keeping current version number.")
            return current_version
        print("Please enter 'major', 'minor', 'patch', 'custom', or 'keep'.")


def prompt_custom_version() -> str:
    while True:
        entered = input("Enter the new version (x.y.z): ").strip()
        if SEMVER_PATTERN.match(entered):
            return entered
        print("Version must follow semantic versioning (e.g. 1.2.3). Try again.")


def confirm_version(current: str, new: str) -> bool:
    while True:
        answer = input(f"Bump version {current} -> {new}? [Y/n]: ").strip().lower()
        if answer in {"", "y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")


def update_version_strings(new_version: str) -> None:
    replacements = (
        (SETUP_PY, r'version\s*=\s*"[^"]+"', f'version="{new_version}"'),
        (PACKAGE_INIT, r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new_version}"'),
        (SERVER_PY, r'server_version\s*=\s*"fnctl/[^"]+"', f'server_version = "fnctl/{new_version}"'),
    )
    for path, pattern, replacement in replacements:
        content = path.read_text(encoding="utf-8")
        new_content, count = re.subn(pattern, replacement, content, count=1)
        if count != 1:
            raise SystemExit(f"Failed to update version in {path}")
        path.write_text(new_content, encoding="utf-8")
        print(f"Updated {path.relative_to(ROOT)}")


def prompt_repository() -> str:
    while True:
        choice = input("Publish target [prod/test] (default prod): ").strip().lower()
        if not choice or choice in {"prod", "p", "pypi"}:
            return "pypi"
        if choice in {"test", "t", "testpypi"}:
            return "testpypi"
        print("Please enter 'prod' or 'test'.")


def prompt_bool(message: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{message} [{suffix}]: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")


def ensure_credentials(use_pypirc: bool, repository: str) -> Dict[str, str]:
    env_overrides: Dict[str, str] = {}
    if use_pypirc:
        pypirc = Path.home() / ".pypirc"
        if not pypirc.exists():
            raise SystemExit("~/.pypirc not found. Create it or choose environment credentials.")
        text = pypirc.read_text(encoding="utf-8", errors="ignore")
        section = f"[{repository}]"
        if section not in text:
            raise SystemExit(f"Section {section} not found in ~/.pypirc")
        print(f"Using credentials from {pypirc}")
        return env_overrides

    env = os.environ.copy()
    username = env.get("TWINE_USERNAME")
    password = env.get("TWINE_PASSWORD") or env.get("TWINE_API_KEY")

    if not username:
        default_username = "__token__"
        entered = input(
            f"Twine username (press Enter for '{default_username}'): "
        ).strip()
        username = entered or default_username
    if not password:
        password = getpass("Twine password / token: ").strip()
    if not password:
        raise SystemExit("Twine password/token is required when not using ~/.pypirc")

    env_overrides["TWINE_USERNAME"] = username
    env_overrides["TWINE_PASSWORD"] = password
    print("Using Twine credentials from environment / prompt inputs")
    return env_overrides


def run_command(cmd: list[str], env_overrides: Dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


def main() -> None:
    current_version = read_current_version()
    print(f"Current version: {current_version}")

    while True:
        new_version = prompt_release_type(current_version)
        if confirm_version(current_version, new_version):
            break
        print("Let's choose again.")

    update_version_strings(new_version)

    # Confirm PyPI repository and credentials
    repository = prompt_repository()
    use_pypirc = prompt_bool("Use ~/.pypirc for credentials?", default=True)
    env_overrides = ensure_credentials(use_pypirc, repository)
    
    # Run tests before publishing
    print("\nRunning pytest before publishing...")
    run_command([sys.executable, "-m", "pytest", "-q"])
    
    # Publish using the publish.sh script
    publish_script = ROOT / "scripts" / "publish.sh"
    if not publish_script.exists():
        raise SystemExit("scripts/publish.sh not found. Cannot continue.")
    
    repo_arg = "prod" if repository == "pypi" else "test"
    run_command(["bash", str(publish_script), repo_arg], env_overrides)

    print("\nVersion bump complete. Publishing commands are commented out.\n")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Command failed with exit code {exc.returncode}")
