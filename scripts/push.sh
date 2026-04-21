#!/bin/bash
# Safe push that handles the sync-all race condition.
#
# Usage:
#   ./scripts/push.sh              # push current commits
#   ./scripts/push.sh --tag v3.1.0 # push, then tag after CI completes
#
# This script:
#   1. Fetches origin/main.
#   2. Rebases local commits on top — falling back to a fast-forward
#      check first, which is the common case when no sync-all
#      [skip ci] commit has raced us.
#   3. On a conflict, auto-resolves files that sync-all owns by
#      taking OUR (local) version; CI will regenerate them on the
#      next push anyway. If the resulting patch is empty (the commit
#      consisted only of auto-file changes), abort loudly — never
#      silently `--skip` the commit, which has dropped release
#      commits twice in production (fix for the v3.4.1 rebase-skip bug).
#   4. Pushes to main.
#
# For releases, use --tag to push the tag AFTER CI completes:
#   ./scripts/push.sh --tag v3.1.0
#   → pushes to main, waits for CI, then pushes the tag.

set -euo pipefail

TAG=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --tag) TAG="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# Files that `scripts/sync_all.py` owns. On a rebase conflict we take
# the LOCAL version (–theirs in git-rebase-speak) so the commit's
# non-auto changes survive. CI regenerates these files deterministically
# on the next push, so a brief mismatch has no persistent effect.
AUTO_FILES=(
  CLAUDE.md
  docs/preview/data.json
  docs/preview/index.html
  docs/preview/report.html
  docs/project-status.md
)

fail() {
  echo ""
  echo "╔═════════════════════════════════════════════════════════════════"
  echo "║ push.sh — ABORT"
  echo "║ $1"
  echo "╚═════════════════════════════════════════════════════════════════"
  echo ""
  echo "Your commits are safe locally. Resolve manually:"
  echo "  git status"
  echo "  git rebase --abort   # to get back to pre-rebase state"
  echo "  # or fix the conflict and: git rebase --continue"
  exit 1
}

echo "Fetching origin/main..."
git fetch origin main

echo "Rebasing on origin/main..."
# `GIT_EDITOR=true` makes rebase accept existing commit messages
# without opening an editor in the non-interactive path — otherwise
# `git rebase --continue` can fail silently on headless runners.
if ! GIT_EDITOR=true git rebase origin/main; then
  echo "Rebase conflict — resolving sync-all auto-files (taking local)..."
  for f in "${AUTO_FILES[@]}"; do
    # During a rebase, --theirs = the commit being replayed (our
    # local commit), --ours = the branch being rebased onto
    # (origin/main). We take --theirs so our commit's work survives;
    # CI sync-all regenerates the auto-files on the next push.
    if [ -f "$f" ] || git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
      git checkout --theirs "$f" 2>/dev/null || true
      git add "$f" 2>/dev/null || true
    fi
  done

  # Any remaining unresolved paths? If yes, we have a non-auto-file
  # conflict that needs human eyes — abort loudly rather than skip.
  if [ -n "$(git diff --name-only --diff-filter=U)" ]; then
    fail "conflict in non-auto file: $(git diff --name-only --diff-filter=U | paste -sd ',' -)"
  fi

  # Continue the rebase. NEVER fall back to --skip — v3.4.1
  # rebase-skip bug dropped the release commit twice by doing exactly
  # that. If --continue fails, the commit should be inspected, not
  # discarded.
  if ! GIT_EDITOR=true git rebase --continue; then
    fail "git rebase --continue failed — the rebase may have produced an empty patch."
  fi
fi

# Defensive: if the rebase silently produced nothing (HEAD unchanged
# from origin/main despite local work), alert instead of pushing.
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
  # Check if there were actually commits to replay. If HEAD equals
  # origin/main AND reflog shows we just rebased, something was lost.
  if git reflog --format=%s -5 | head -1 | grep -q "rebase"; then
    fail "HEAD matches origin/main after rebase — commits may have been dropped. Check 'git reflog'."
  fi
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

  # Belt-and-braces: tag the commit that carries the version bump,
  # not HEAD (which may be a [skip ci] auto-sync).
  RELEASE_SHA=$(git log --format=%H --grep="^release:" -1)
  if [ -z "$RELEASE_SHA" ]; then
    RELEASE_SHA=$(git rev-parse HEAD)
    echo "No 'release:' commit found; tagging HEAD ($RELEASE_SHA)."
  else
    echo "Tagging the release commit: $RELEASE_SHA"
  fi

  echo ""
  echo "CI passed. Pushing tag $TAG..."
  git tag "$TAG" "$RELEASE_SHA"
  git push origin "$TAG"
  echo "✓ Tag $TAG pushed — Release workflow will publish to PyPI"
fi
