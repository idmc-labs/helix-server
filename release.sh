#!/bin/bash

export SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function release_custom_hook {
    msg="# managed by release.sh"
    sed -E -i "s/^version = .* $msg$/version = \"${version_tag#v}\"  $msg/" "./pyproject.toml"
    uv sync --all-groups --all-extras
    git add ./pyproject.toml ./uv.lock
}

export -f release_custom_hook
export START_COMMIT=4c0100d4696a6ffec558926a9b0f6323e267e2b5
export RELEASE_CUSTOM_HOOK=release_custom_hook
export REPO_NAME=idmc-labs/helix-server
export DEFAULT_BRANCH=develop

export GIT_CLIFF__REMOTE__GITHUB__OWNER=idmc-labs
export GIT_CLIFF__REMOTE__GITHUB__REPO=helix-server

$SCRIPT_DIR/fugit/scripts/release.sh
