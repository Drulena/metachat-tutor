#!/bin/sh
# Install the repository's git hooks into this clone.
#
# Git never versions .git/hooks, so scripts/hooks/ holds the source and this
# script copies it into the clone's hooks directory. Run it once per clone, and
# again after a hook changes:
#
#   sh scripts/install-git-hooks.sh
#
# The copy is made rather than symlinked: symlinks need extra rights on Windows
# and checkout conversion (autocrlf) never touches .git/hooks.

set -eu

cd "$(dirname "$0")/.."

hooks_dir=$(git rev-parse --git-path hooks)
mkdir -p "$hooks_dir"

for hook in scripts/hooks/*; do
    [ -f "$hook" ] || continue
    name=${hook##*/}
    cp "$hook" "$hooks_dir/$name"
    chmod +x "$hooks_dir/$name"
    printf 'installed %s\n' "$hooks_dir/$name"
done
