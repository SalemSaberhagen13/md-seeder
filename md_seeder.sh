#!/usr/bin/env bash
set -euo pipefail

# DEFAULT VARS
BRANCH="master"  # or tag, is the same
REPO_URL=""
SSH_KEY=""
FLAT=false
DELETE_EXISTING=false
DEST_DIR="$(pwd)/.claude"

usage() {
    cat <<EOF
Use: $0 -r <git@github.com:user/repo.git> [-b <branch>] [-k <path_ssh_key>] [-f] [-d] [-h]

Options:
  -r <repo_url>      Git repository URL to clone (required)
  -b <branch>        Branch or tag to clone (default: master)
  -k <path_ssh_key>  Path to SSH private key (optional; uses ssh-agent by default)
  -f                 Flatten: copy all .md files directly into .claude/ without subfolders
  -d                 Delete existing .md files in .claude/ before copying new ones
  -h                 Show this help message and exit
EOF
    exit 1
}

while getopts "r:b:k:fdh" opt; do
    case "$opt" in
        r) REPO_URL="$OPTARG" ;;      # -r git@github...
        b) BRANCH="$OPTARG" ;;        # -b master
        k) SSH_KEY="$OPTARG" ;;       # -k ~/.ssh/id_ed25519
        f) FLAT=true ;;               # -f flatten into .claude/
        d) DELETE_EXISTING=true ;;    # -d delete existing .md files in .claude/
        *) usage ;;                   # you failed
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

if [[ "$DELETE_EXISTING" == true ]]; then
    for old_file in "$DEST_DIR"/**/*.md; do
        [[ -f "$old_file" ]] || continue
        echo "rm -f $old_file"
        rm -f "$old_file"
    done
fi

for file in "$TMP_DIR"/**/*.md; do
    [[ -f "$file" ]] || continue
    [[ "$file" == "$TMP_DIR/tui/"* ]] && continue

    if [[ "$FLAT" == true ]]; then
        echo "cp -f $file $DEST_DIR/"
        cp -f "$file" "$DEST_DIR/"
    else
        rel_path="${file#"$TMP_DIR"/}"
        target_file="$DEST_DIR/$rel_path"
        mkdir -p "$(dirname "$target_file")"
        echo "cp -f $file $target_file"
        cp -f "$file" "$target_file"
    fi
done

echo 'Magic done'
