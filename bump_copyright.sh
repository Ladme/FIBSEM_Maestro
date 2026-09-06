#!/bin/bash

# Usage: ./bump_copyright.sh [-n] [DIRECTORY]
#   -n   dry run: show which files would change, without modifying anything

set -euo pipefail

OLD='# Copyright (c) 2024-2025 CEMCOF'
NEW='# Copyright (c) 2024-2026 CEMCOF'

dry_run=0
while getopts ':n' opt; do
    case "$opt" in
        n) dry_run=1 ;;
        *) echo "Usage: $0 [-n] [DIRECTORY]" >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

dir="${1:-.}"
[[ -d "$dir" ]] || { echo "Not a directory: $dir" >&2; exit 1; }

# escape regex metacharacters so '(c)' and '.' are matched literally
old_re=$(printf '%s' "$OLD" | sed 's/[][\.^$*+?(){}|\\]/\\&/g')
# escape characters special on sed's replacement side
new_sub=$(printf '%s' "$NEW" | sed 's/[&\\|]/\\&/g')

pattern="^([[:space:]]*)${old_re}[[:space:]]*$"

count=0
while IFS= read -r -d '' file; do
    if (( dry_run )); then
        echo "would update: $file"
    else
        sed -i -E "s|${pattern}|\1${new_sub}|" "$file"
        echo "updated: $file"
    fi
    count=$((count + 1))
done < <(grep -rlZ --binary-files=without-match --exclude-dir=.git -E "$pattern" "$dir" || true)

echo "${count} file(s) matched."
