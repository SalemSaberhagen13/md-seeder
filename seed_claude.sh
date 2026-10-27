#!/usr/bin/env bash
set -euo pipefail

# DEFAULT VARS
BRANCH="master"  # or tag, is the same
REPO_URL=""
SSH_KEY=""
DEST_DIR="$(pwd)/.claude"

usage() {
    echo "Use: $0 -r <git@github.com:user/repo.git> [-b <branch>] [-k <path_ssh_key>]"
    exit 1
}

while getopts "r:b:k:h" opt; do
    case "$opt" in
        r) REPO_URL="$OPTARG" ;; # -r git@github...
        b) BRANCH="$OPTARG" ;;   # -b master
        k) SSH_KEY="$OPTARG" ;;  # -k ~/.ssh/id_ed25519
        *) usage ;;              # you failed
    esac
done

if [[ -z "$REPO_URL" ]] ; then  # You failed miserably
    usage
fi

TMP_DIR=$(mktemp -d)  # Creates folder under /tmp . Command is evaluated as a path.
# Cleans stuff if something fails for whatever reason. Even if it is temporary
trap 'rm -rf "$TMP_DIR"' EXIT

echo -e "Downloading branch/version $BRANCH from $REPO_URL\nPlease wait..."

if [[ -z "$SSH_KEY" ]] ; then
    echo "Hope you've set up your ssh agent"
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"
else
    GIT_SSH_COMMAND="ssh -i \"$SSH_KEY\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"
fi

mkdir -p "$DEST_DIR"

shopt -s nullglob globstar # claude says this prevent errors in case of no md files
for file in "$TMP_DIR"/**/*.md; do
    echo "cp -f $file $DEST_DIR/"
    cp -f "$file" "$DEST_DIR/"
done

echo 'Magic done'
