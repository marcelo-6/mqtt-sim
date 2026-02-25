# Release Guide

The release automation is designed around:

- `git-cliff` for changelog generation
- `just` recipes for local parity and release prep
- tag-driven CD for PyPI + Docker publish, then GitHub Release creation

## One-time setup (GitHub repo)

Repository variable:

- `USE_TESTPYPI`
  - Default: `true`
  - Set to `false` before pushing a production release tag

Repository secrets:

- `TEST_PYPI_API_TOKEN`
- `PYPI_API_TOKEN`
- `CODECOV_TOKEN` (optional, used for coverage uploads/badge reliability)

Docker publish:

- The current workflow publishes to GHCR (`ghcr.io/<owner>/mqtt-sim`) using the built-in `GITHUB_TOKEN`.
- No extra Docker registry secret is required for the default GHCR flow.

## Local release prep

Run these before touching tags:

```bash
uv sync --dev
just ci-check
just cd-preflight
```

## Prepare a release changelog

Use the release helper to generate `CHANGELOG.md` and a local `RELEASE_NOTES.md` preview for the tag you plan to create:

```bash
just release vX.Y.Z
```

This does not create a git tag. It prepares the changelog/release notes so you can review and commit them first.

## Production release flow (this repo)

1. Start from an up-to-date release prep branch created from `main`:

   ```bash
   git checkout main
   git pull
   git checkout -b chore/release-vX.Y.Z
   ```

2. Generate/update the changelog for the release:

   ```bash
   just release vX.Y.Z
   ```

3. Review the generated files:

   - `CHANGELOG.md`
   - `RELEASE_NOTES.md` (local preview, ignored)

4. Commit and push the changelog changes:

   ```bash
   git add CHANGELOG.md
   git commit -m "docs(changelog): prepare vX.Y.Z"
   git push -u origin chore/release-vX.Y.Z
   ```

5. Open a PR for the release prep branch and confirm CI is green.

6. Merge to origin/main

7. Set repo variable `USE_TESTPYPI=false` (do this before tagging).

8. Create and push the tag from the merged `main` commit:

   ```bash
   git checkout main
   git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

9.  Wait for the `CD Release` workflow to finish.

The CD workflow will:

- publish the package to PyPI
- publish the Docker image to GHCR
- create the GitHub Release using the matching released entry from `CHANGELOG.md`

## TestPyPI-first package publishing (manual)

You can manually test package publishing without creating a release tag by running the `Publish Package` workflow from GitHub and leaving `use_testpypi=true`.

You can also dry-run locally:

```bash
just publish-testpypi-dry
```

## Notes / recovery

- Do not tag the PR branch before merge. Tag the merged commit on `main`.
- If the tag workflow fails before the GitHub Release is created, fix the issue and re-run the workflow from GitHub Actions.
- Do not create a second tag for the same version.
- If the release notes look wrong, check that `CHANGELOG.md` contains a released section for the pushed tag (not only `Unreleased`).
