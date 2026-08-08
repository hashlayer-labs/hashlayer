#!/usr/bin/env bash
# Print a random allowed author as: name|email
set -euo pipefail
hooks_dir=$(cd "$(dirname "$0")" && pwd)
authors=()
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  authors+=("$line")
done < "$hooks_dir/allowed-authors"
n=${#authors[@]}
if [[ "$n" -lt 1 ]]; then
  echo "No authors in allowed-authors" >&2
  exit 1
fi
echo "${authors[$((RANDOM % n))]}"
