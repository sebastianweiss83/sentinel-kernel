#!/bin/bash
# Safe push that handles sync-all race condition.
#
# Usage:
#   ./scripts/push.sh              # push current commits
#   ./scripts/push.sh --tag v3.1.0 # push, then tag after CI completes
#
# This script:
#   1. Fetches origin/main
#   2. Rebases local commits on top
#   3. Auto-resolves conflicts in auto-generated files
#   4. Pushes to main
#
# For releases, use --tag to push the tag AFTER CI completes:
#   ./scripts/push.sh --tag v3.1.0
#   → pushes to main, waits for CI, then pushes tag

set -euo pipefail

TAG=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --tag) TAG="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# Auto-generated files that sync-all owns — always take ours on conflict
AUTO_FILES=(
  CLAUDE.md
  docs/preview/data.json
  docs/preview/index.html
  docs/preview/report.html
  docs/project-status.md
)

echo "Fetching origin/main..."
git fetch origin main

echo "Rebasing on origin/main..."
if ! git rebase origin/main; then
  echo "Rebase conflict — resolving auto-generated files..."
  for f in "${AUTO_FILES[@]}"; do
    if [ -f "$f" ]; then
      git checkout --ours "$f" 2>/dev/null || true
    fi
  done
  git add "${AUTO_FILES[@]}" 2>/dev/null || true
  git rebase --continue || git rebase --skip
fi

echo "Pushing to main..."
git push origin main
echo "✓ Pushed to main"

if [ -n "$TAG" ]; then
  echo ""
  echo "Waiting for CI to complete before tagging..."
  # Get the run triggered by our push
  sleep 5  # brief pause for GitHub to register the run
  RUN_ID=$(gh run list --branch main --limit 1 --json databaseId -q '.[0].databaseId')
  if [ -n "$RUN_ID" ]; then
    echo "Watching CI run #$RUN_ID..."
    gh run watch "$RUN_ID" --exit-status || {
      echo "✗ CI failed — NOT pushing tag $TAG"
      exit 1
    }
  fi
  echo ""
  echo "CI passed. Pushing tag $TAG..."
  git tag "$TAG"
  git push origin "$TAG"
  echo "✓ Tag $TAG pushed — Release workflow will publish to PyPI"
fi
