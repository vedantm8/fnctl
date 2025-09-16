#!/usr/bin/env bash
set -euo pipefail

# fnctl install script
# - Installs from GitHub source tarball (no PyPI required yet)
# - Prefers pipx; falls back to pip --user
# - Pin tag via VERSION env var (e.g., VERSION=0.1.0)

APP="fnctl"
REPO="vedantm8/fnctl"
VERSION="${VERSION:-}" # empty means latest (master)

# Build GitHub tarball URL (avoids requiring git on target machine)
# If VERSION is set, use refs/tags/vX.Y.Z; else refs/heads/master
ref_type="heads"
ref_name="master"
if [ -n "$VERSION" ]; then
  ref_type="tags"
  ref_name="v${VERSION#v}"
fi
TARBALL_URL="https://github.com/${REPO}/archive/refs/${ref_type}/${ref_name}.tar.gz"

log() { printf "%s\n" "$*" >&2; }
die() { log "Error: $*"; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1; }

python_bin=""
pick_python() {
  if need_cmd python3; then python_bin=python3; elif need_cmd python; then python_bin=python; else die "Python is required but not found"; fi
}

pipx_install() {
  if ! need_cmd pipx; then
    return 1
  fi
  log "pipx: installing from ${TARBALL_URL}"
  # --force ensures upgrade if already installed
  pipx install --force "$TARBALL_URL"
}

pip_user_install() {
  pick_python
  if ! "$python_bin" -m pip --version >/dev/null 2>&1; then
    die "pip is required but not found for ${python_bin}"
  fi
  log "pip: installing --user from ${TARBALL_URL}"
  "$python_bin" -m pip install --upgrade --user "$TARBALL_URL"

  # Best-effort PATH hint for --user installs
  user_base="$($python_bin -m site --user-base 2>/dev/null || true)"
  if [ -n "$user_base" ]; then
    bin_dir="${user_base}/bin"
    if ! echo ":$PATH:" | grep -q ":${bin_dir}:"; then
      log "Add to PATH: export PATH=\"${bin_dir}:$PATH\""
    fi
  fi
}

verify_install() {
  if command -v "$APP" >/dev/null 2>&1; then
    resolved="$(command -v "$APP")"
    log "Installed $APP at: $resolved"
    "$APP" --help >/dev/null 2>&1 || true
    exit 0
  else
    die "$APP not found on PATH after install. Please ensure your PATH includes pipx or pip --user bin directory."
  fi
}

main() {
  log "Installing ${APP} ${VERSION:+(version ${VERSION})}..."
  if pipx_install; then
    :
  else
    log "pipx not found; falling back to pip --user"
    pip_user_install
  fi
  verify_install
}

main "$@"
