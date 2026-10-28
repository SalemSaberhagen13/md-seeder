#!/usr/bin/env bash
set -euo pipefail

# DEFAULTS
BRANCH="main"  # you can use tags and versions as well
REPO_URL="git@github.com:SalemSaberhagen13/md-seeder.git"
SSH_KEY=""
FLAT=false
DELETE_EXISTING=false
DEST_DIR="$(pwd)/.claude"

usage() {
    cat <<EOF
Use: $0 [-r <git@github.com:user/repo.git>] [-b <branch>] [-k <path_ssh_key>] [-o <output_dir>] [-f] [-d] [-h]

Options:
  -r <repo_url>      Git repository URL to clone (default: $REPO_URL)
  -b <branch>        Branch or tag to clone (default: master)
  -k <path_ssh_key>  Path to SSH private key (optional; uses ssh-agent by default)
  -o <output_dir>    Output folder to copy .md files into (default: $(pwd)/.claude)
  -f                 Flatten: copy all .md files directly into the output folder without subfolders
  -d                 Delete existing .md files in the output folder before copying new ones
  -h                 Show this help message and exit
EOF
    exit 1
}

while getopts "r:b:k:o:fdh" opt; do
    case "$opt" in
        r) REPO_URL="$OPTARG" ;;      # -r git@github...
        b) BRANCH="$OPTARG" ;;        # -b master
        k) SSH_KEY="$OPTARG" ;;       # -k ~/.ssh/id_ed25519
        o) DEST_DIR="$OPTARG" ;;      # -o /path/to/output
        f) FLAT=true ;;               # -f flatten into output folder
        d) DELETE_EXISTING=true ;;    # -d delete existing .md files in output folder
        *) usage ;;                   # you failed
    esac
done

cat <<'EOF'
               _                         _
 _ __ ___   __| |      ___  ___  ___  __| | ___ _ __
| '_ ` _ \ / _` |_____/ __|/ _ \/ _ \/ _` |/ _ \ '__|
| | | | | | (_| |_____\__ \  __/  __/ (_| |  __/ |
|_| |_| |_|\__,_|     |___/\___|\___|\__,_|\___|_|
EOF

TMP_DIR=$(mktemp -d)  # Creates folder under /tmp . Command is evaluated as a path.
MD_DIR="$TMP_DIR/md_files"

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

shopt -s nullglob globstar # This prevents errors in absence of md files

if [[ "$DELETE_EXISTING" == true ]]; then
    for old_file in "$DEST_DIR"/**/*.md; do
        [[ -f "$old_file" ]] || continue
        echo "rm -f $old_file"
        rm -f "$old_file"
    done
fi

COPIED_COUNT=0
for file in "$MD_DIR"/**/*.md; do
    [[ -f "$file" ]] || continue  # Skips folders
    if [[ "$FLAT" == true ]]; then
        echo "cp -f $file $DEST_DIR/"
        cp -f "$file" "$DEST_DIR/"
    else
        rel_path="${file#"$TMP_DIR"/}"  # Where file is in given path. Cool
        target_file="$DEST_DIR/$rel_path"
        mkdir -p "$(dirname "$target_file")"
        echo "cp -f $file $target_file"
        cp -f "$file" "$target_file"
    fi
    COPIED_COUNT=$((COPIED_COUNT + 1))
done

echo "SUCCESS: $COPIED_COUNT file(s) copied in $DEST_DIR"
