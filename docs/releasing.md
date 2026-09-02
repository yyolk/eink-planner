# Releasing

A published GitHub Release is the ship step. Tag `vX.Y.Z` must match `[project].version` in `pyproject.toml` (no `v` in the file). Hatchling embeds that file version on the tagged commit; `publish.yml` fails the build if the tag and file differ.

1. Merge a version-bump PR to `master` and wait for CI (`parch press supernote-nomad`).
2. **Releases → Draft a new release.** Tag `vX.Y.Z` (create on publish), target `master`.
3. Publish. Every Release goes to [TestPyPI](https://test.pypi.org/project/parch/). A stable Release (pre-release unchecked) also waits on the `pypi` environment, then uploads to [PyPI](https://pypi.org/project/parch/). The wheel and sdist attach to that Release.

Do not `git push origin vX.Y.Z` to ship. Never retag.

Manual TestPyPI-only: **Actions → Publish → `testpypi`**.

## Version bumps

`uv version` writes `[project].version`. Exact string: `uv version 0.1.2rc1 --no-sync`. Do not hand-edit the field. `parch --version` and `__version__` read the installed package metadata, not a second string.

From a checkout on a bump branch:

```shell
uv version --short                          # current, e.g. 0.1.1
uv version --bump patch --no-sync           # 0.1.1 => 0.1.2
uv version --bump minor --no-sync           # 0.1.1 => 0.2.0
uv version --bump major --no-sync           # 0.1.1 => 1.0.0
uv version --dry-run --bump patch           # print next, do not write
```

`--no-sync` skips rewriting the venv; the file is the point. Commit that `pyproject.toml` (and the lockfile if `uv version` touched it) and open the bump PR.

The Release tag is `v` plus `uv version --short` after the bump.

## Pre-release

Same loop as stable. The version string is a PEP 440 pre-release and the GitHub Release has **Set as a pre-release** checked. TestPyPI gets it; PyPI does not.

From `0.1.1`:

```shell
# first rc of the next patch
uv version --bump patch --bump rc --no-sync
# 0.1.1 => 0.1.2rc1

# another rc of the same version
uv version --bump rc --no-sync
# 0.1.2rc1 => 0.1.2rc2

# drop the suffix when that cut is good
uv version --bump stable --no-sync
# 0.1.2rc2 => 0.1.2
```

`--bump alpha` / `--bump beta` work the same way as `--bump rc`.

1. Merge the bump PR (`0.1.2rc1`) to `master`. Wait for CI.
2. Draft a Release. Tag `v0.1.2rc1` (create on publish), target `master`, tick **Set as a pre-release**.
3. Publish. TestPyPI gets `0.1.2rc1`. The `pypi` environment is skipped. Wheel and sdist attach.

Stable later is another bump PR (`uv version --bump stable`) and a new Release `v0.1.2` with the box unchecked. Do not reuse `0.1.2rc1`. Do not un-tick pre-release on the same tag. Do not publish `0.1.2` to TestPyPI as a pre-release and then the same `0.1.2` to PyPI.
