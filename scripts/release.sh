#!/usr/bin/env bash

set -euo pipefail

if ! command -v git-cliff >/dev/null 2>&1; then
  echo "git-cliff is required. Install: https://git-cliff.org/docs/installation/"
  exit 1
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: ./scripts/release.sh vX.Y.Z"
  exit 1
fi

tag="$1"
if [[ ! "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Tag must match vX.Y.Z (got: $tag)"
  exit 1
fi

echo "Preparing release notes and changelog for $tag..."
git-cliff --config cliff.toml --tag "$tag" --tag-pattern '^(?:v)?[0-9]+\.[0-9]+\.[0-9]+$' --output CHANGELOG.md
python3 .github/scripts/extract_latest_changelog.py --changelog CHANGELOG.md --tag "$tag" --output RELEASE_NOTES.md

echo
echo "Prepared files:"
echo "  - CHANGELOG.md"
echo "  - RELEASE_NOTES.md"
echo
echo "Next steps:"
echo "  1. Review CHANGELOG.md and RELEASE_NOTES.md"
echo "  2. Commit and push"
echo "  3. Wait for CI to pass"
echo "  4. Make sure repository variable USE_TESTPYPI=false"
echo "  5. Create/push the tag: git tag $tag && git push origin $tag"
