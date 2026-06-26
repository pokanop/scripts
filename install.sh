#!/usr/bin/env bash
# install.sh — Install pokanop/scripts on macOS / Linux
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/pokanop/scripts/main/install.sh | bash
#   ./install.sh [--update] [--tools medcat,pluck] [--dir PATH] [--in-place]
#
set -euo pipefail

REPO_URL="${SCRIPTS_REPO_URL:-https://github.com/pokanop/scripts.git}"
REPO_REF="${SCRIPTS_REPO_REF:-main}"

INSTALL_DIR="${SCRIPTS_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/scripts}"
BIN_DIR="${SCRIPTS_BIN:-${XDG_BIN_HOME:-$HOME/.local/bin}}"

UPDATE=0
IN_PLACE=0
NO_PATH=0
TOOLS_ARG=""
CUSTOM_DIR=""

usage() {
    cat <<'EOF'
Usage: install.sh [options]

Options:
  --update              Update an existing install (git pull + refresh deps)
  --tools LIST          Comma-separated tools to add (default: harness only; use 'all' for every tool)
  --dir PATH            Install directory (default: ~/.local/share/scripts)
  --bin-dir PATH        Wrapper directory (default: ~/.local/bin)
  --in-place            Install using this repo directory (for git clones)
  --no-path             Do not modify shell rc PATH
  -h, --help            Show this help

Examples:
  curl -fsSL https://raw.githubusercontent.com/pokanop/scripts/main/install.sh | bash
  git clone https://github.com/pokanop/scripts.git && cd scripts && ./install.sh --in-place
  ./install.sh --update
  ./install.sh --tools medcat,pluck
  ./install.sh --tools all
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --update) UPDATE=1; shift ;;
        --in-place) IN_PLACE=1; shift ;;
        --no-path) NO_PATH=1; shift ;;
        --dir) CUSTOM_DIR="$2"; shift 2 ;;
        --bin-dir) BIN_DIR="$2"; shift 2 ;;
        --tools) TOOLS_ARG="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -n "$CUSTOM_DIR" ]]; then
    INSTALL_DIR="$CUSTOM_DIR"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$IN_PLACE" -eq 1 ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/scripts" && -d "$SCRIPT_DIR/requirements" && -d "$SCRIPT_DIR/.git" ]]; then
    # Running from a git clone: install in-place by default.
    INSTALL_DIR="$SCRIPT_DIR"
    IN_PLACE=1
fi

echo "==> pokanop/scripts installer"
echo "    Install dir: $INSTALL_DIR"
echo "    Bin dir:     $BIN_DIR"
echo

if [[ "$IN_PLACE" -eq 0 && ! -d "$INSTALL_DIR/.git" ]]; then
    if [[ -d "$INSTALL_DIR" ]]; then
        echo "==> Using existing directory: $INSTALL_DIR"
    else
        echo "==> Cloning $REPO_URL (ref: $REPO_REF)"
        git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$INSTALL_DIR"
    fi
elif [[ "$UPDATE" -eq 1 && -d "$INSTALL_DIR/.git" ]]; then
    echo "==> Pulling latest changes"
    git -C "$INSTALL_DIR" pull --ff-only
fi

if [[ ! -f "$INSTALL_DIR/scripts" ]]; then
    echo "error: $INSTALL_DIR does not look like a scripts checkout" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required" >&2
    exit 1
fi

PYTHON="${SCRIPTS_PYTHON:-python3}"

INSTALL_ARGS=(--dir "$INSTALL_DIR" --bin-dir "$BIN_DIR")
if [[ "$NO_PATH" -eq 1 ]]; then
    INSTALL_ARGS+=(--no-path)
fi
if [[ "$UPDATE" -eq 1 ]]; then
    INSTALL_ARGS+=(--upgrade)
fi
if [[ -n "$TOOLS_ARG" ]]; then
    IFS=',' read -r -a TOOL_LIST <<< "$TOOLS_ARG"
    INSTALL_ARGS+=("${TOOL_LIST[@]}")
fi

echo "==> Running scripts install"
exec "$PYTHON" "$INSTALL_DIR/scripts" install "${INSTALL_ARGS[@]}"