# Releasing

A published GitHub Release is the ship step. Tag `vX.Y.Z` must match `[project].version` in `pyproject.toml` (no `v` in the file). Hatchling embeds that file version on the tagged commit; `publish.yml` fails the build if the tag and file differ.

1. Merge a version-bump PR to `master` and wait for CI (`parch press supernote-nomad`).
2. **Releases → Draft a new release.** Tag `vX.Y.Z` (create on publish), target `master`.
3. Publish. Every Release goes to [TestPyPI](https://test.pypi.org/project/parch/). A stable Release (pre-release unchecked) also waits on the `pypi` environment, then uploads to [PyPI](https://pypi.org/project/parch/). The wheel and sdist attach to that Release.

Do not `git push origin vX.Y.Z` to ship. Never retag. A pre-release is `0.1.2rc1` / `v0.1.2rc1`, then a new `0.1.2` / `v0.1.2` for PyPI — not the same version string twice.

Manual TestPyPI-only: **Actions → Publish → `testpypi`**.
