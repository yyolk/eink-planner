# eink-planner

Python port of [Vitaliy Kudryk's LYP (latex-yearly-planner)](https://github.com/kudrykv/latex-yearly-planner/tree/alpha) ([fork point commit](https://github.com/kudrykv/latex-yearly-planner/commit/a59229770cfbf4a05b68a656dd70c02913a7df49), MIT, 2026).

LYP generates a yearly planner by emitting **Typst**, then compiling that to **PDF**. This package keeps that architecture: Python reads a **KDL 2.0** device profile, walks calendar entities, and writes `index.typst` + `index.pdf`. It does **not** draw PDFs with reportlab/fpdf.

Default device is the **SuperNote Nomad** (A6 X2), MOS strip on the left. A Nomad MOS-right sibling, Kindle Scribe, and 158×210 MOS-left/MOS-right profiles are also shipped.

## Install

Needs [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```shell
cd eink-planner
uv sync
```

`typst` is used to compile the PDF. If it is not on `PATH`, the compile step downloads the official Typst v0.15.1 binary for the current OS/arch into `.tools/typst` (`.tools/typst.exe` on Windows).

## Generate

```shell
# SuperNote Nomad 2026 (default profile, MOS-left) → ./out/index.pdf
uv run lyp generate configs/supernote-nomad.kdl

# SuperNote Nomad 2027 from the shipped 2026 profile (CLI overlay)
uv run lyp generate configs/supernote-nomad.kdl --year 2027

# SuperNote Nomad MOS-right → ./out/nomad-mos-right/index.pdf
uv run lyp generate configs/supernote-nomad-mos-right.kdl -w out/nomad-mos-right

# 158×210 MOS-left → ./out/mos-left/index.pdf
uv run lyp generate configs/158x210-mos-left.kdl -w out/mos-left

# 158×210 MOS-left lined → ./out/mos-left-lined/index.pdf
uv run lyp generate configs/158x210-mos-left-lined.kdl -w out/mos-left-lined

# 158×210 MOS-right → ./out/mos-right/index.pdf
uv run lyp generate configs/158x210-mos-right.kdl -w out/mos-right

# Kindle Scribe → ./out/scribe/index.pdf
uv run lyp generate configs/kindle-scribe.kdl -w out/scribe
```

`eink-planner` is an alias for `lyp`:

```shell
uv run eink-planner generate configs/supernote-nomad.kdl --locale en
```

Flags:

| Flag | Default | Meaning |
| --- | --- | --- |
| `-w` / `--workdir` | `./out` | Where `index.typst` and `index.pdf` are written |
| `-l` / `--locale` | `en` | Locale code (`locales/<code>.yaml`) |
| `-g` / `--with-ghostscript` | off | Optional PDF shrink via `gs` |
| `--debug` | off | Draw MOS debug strokes (not a config key) |
| `--year` | file year | Overlay planner year (dates and cover title; not a config key) |

`--year` also rewrites the cover title year when the old year is in the title.

A `section` node in KDL is enabled by being present. Comment the node out to disable it. There is no `enabled=#true` flag, and `debug` does not belong in the profile — use `lyp generate --debug`. At least one `section` must remain.

## Device profiles

Sizes are 1:1 on glass at 300 PPI.

| Device | Pixels | Page (pt) | Page (mm) | Config |
| --- | --- | --- | --- | --- |
| SuperNote Nomad (A6 X2) | 1404×1872 | 336.96×449.28 | 118.87×158.5 | `configs/supernote-nomad.kdl` |
| SuperNote Nomad MOS-right | 1404×1872 | 336.96×449.28 | 118.87×158.5 | `configs/supernote-nomad-mos-right.kdl` |
| 158×210 MOS-left | — | 447.87×595.28 | 158×210 | `configs/158x210-mos-left.kdl` |
| 158×210 MOS-left lined | — | 447.87×595.28 | 158×210 | `configs/158x210-mos-left-lined.kdl` |
| 158×210 MOS-right | — | 447.87×595.28 | 158×210 | `configs/158x210-mos-right.kdl` |
| Kindle Scribe | 1860×2480 | 446.4×595.2 | 157.48×209.97 | `configs/kindle-scribe.kdl` |

Presets also live in `eink_planner.devices`. The Nomad profile scales strokes, type, and gutters down slightly from the original 158×210 MOS-left gist so the MOS layout still fits the smaller page.

**MOS** is Months on the Side — the navigation style that places a vertical month menu on the side of the page (as opposed to a top breadcrumb trail).

Shipped configs keep the **MOS** (Months on the Side) layout: side menu on the physical left except 158×210 MOS-right and SuperNote Nomad MOS-right (physical right), reversed months/quarters, Monday week start, daily schedule 8–20, 5 top priorities, 2 extra daily note pages, dotted scratch pad on most shipped configs (the 158×210 MOS-left lined sibling uses `style.scratch-pad lined` with daily notes still dotted). `pattern` is per notes area (dotted default; `lined` is the other option). MOS-left/MOS-right names are the physical MOS strip side (nav left / nav right), not which hand you write with. MOS-left is the right-handed writing layout (nav opposite the writing hand); MOS-right is the left-handed writing layout. Upstream LYP called these leftie/rightie for the same strip-side meaning; the shipped `.kdl` files drop that jargon.

Device profiles are KDL; locale files stay YAML.

## Tests

```shell
uv run pytest
```

CI runs pytest and a Nomad `lyp generate`.

## Layout of a generated planner

Enabled MOS (Months on the Side) sections, in order:

1. Cover
2. Annual (12 little calendars)
3. Quarterly
4. Monthly
5. Weekly
6. Daily (schedule + little calendar + priorities + notes)
7. Daily notes (extra dotted pages)

Internal PDF links use Typst `#padded_link` / `<label>` the same way LYP does. A link is only emitted when the target page exists; otherwise the cell stays plain text.

## License

MIT. This is a port of Vitaliy Kudryk's LYP (MIT 2026). See `LICENSE`.
