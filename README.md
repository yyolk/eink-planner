# eink-planner

Python port of [Vitaliy Kudryk's LYP](https://github.com/kudrykv/LYP) (MIT, 2026).

LYP generates a yearly planner by emitting **Typst**, then compiling that to **PDF**. This package keeps that architecture: Python reads a YAML config, walks calendar entities, and writes `index.typst` + `index.pdf`. It does **not** draw PDFs with reportlab/fpdf.

Default device is the **SuperNote Nomad** (A6 X2). Kindle Scribe is a second profile.

## Install

Needs [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```shell
cd eink-planner
uv sync
```

`typst` is used to compile the PDF. If it is not on `PATH`, the compile step downloads the official Typst v0.15.1 binary for the current OS/arch into `.tools/typst` (`.tools/typst.exe` on Windows).

## Generate

```shell
# SuperNote Nomad 2026 (default profile) → ./out/index.pdf
uv run lyp generate configs/supernote-nomad.yaml

# Kindle Scribe → ./out/scribe/index.pdf
uv run lyp generate configs/kindle-scribe.yaml -w out/scribe
```

`eink-planner` is an alias for `lyp`:

```shell
uv run eink-planner generate configs/supernote-nomad.yaml --locale en
```

Flags:

| Flag | Default | Meaning |
| --- | --- | --- |
| `-w` / `--workdir` | `./out` | Where `index.typst` and `index.pdf` are written |
| `-l` / `--locale` | `en` | Locale code (`locales/<code>.yaml`) |
| `-g` / `--with-ghostscript` | off | Optional PDF shrink via `gs` |

## Device profiles

Sizes are 1:1 on glass at 300 PPI.

| Device | Pixels | Page (pt) | Page (mm) | Config |
| --- | --- | --- | --- | --- |
| SuperNote Nomad (A6 X2) | 1404×1872 | 336.96×449.28 | 118.87×158.5 | `configs/supernote-nomad.yaml` |
| Kindle Scribe | 1860×2480 | 446.4×595.2 | 157.48×209.97 | `configs/kindle-scribe.yaml` |

Presets also live in `eink_planner.devices`. The Nomad YAML scales strokes, type, and gutters down slightly from the original 158×210 leftie gist so the MOS layout still fits the smaller page.

Both configs keep the gist MOS layout: side menu on the left, reversed months/quarters, Monday week start, daily schedule 8–20, 5 top priorities, 2 extra daily note pages, dotted scratch pad.

## Tests

```shell
uv run pytest
```

## Layout of a generated planner

Enabled MOS sections, in order:

1. Cover
2. Annual (12 little calendars)
3. Quarterly
4. Monthly
5. Weekly
6. Daily (schedule + little calendar + priorities + notes)
7. Daily notes (extra dotted pages)

Internal PDF links use Typst `#padded_link` / `<label>` the same way LYP does.

## License

MIT. This is a port of Vitaliy Kudryk's LYP (MIT 2026). See `LICENSE`.
