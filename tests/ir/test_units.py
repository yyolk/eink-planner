from parch.ir.nodes import Length
from parch.ir.units import parse, parse_tracks, resolve_tracks, to_mm


def test_parse_mm_pt_fr_auto():
    assert parse("10mm") == Length.mm(10)
    assert parse("0.4pt") == Length.pt(0.4)
    assert parse("1fr") == Length.fr(1)
    assert parse("auto") == Length.auto()
    assert parse(5) == Length.mm(5)
    assert abs(to_mm(parse("72pt")) - 25.4) < 1e-9


def test_parse_tracks():
    assert parse_tracks("(3fr, 5fr)") == [Length.fr(3), Length.fr(5)]
    assert parse_tracks("10mm, 1fr, auto") == [Length.mm(10), Length.fr(1), Length.auto()]


def test_resolve_tracks_fr_and_fixed():
    # 100mm, two 10mm gaps, 20mm + 1fr + 2fr → leftover 60, split 20 / 40
    sizes = resolve_tracks([Length.mm(20), Length.fr(1), Length.fr(2)], 100, gap_mm=10)
    assert abs(sizes[0] - 20) < 1e-9
    assert abs(sizes[1] - 20) < 1e-9
    assert abs(sizes[2] - 40) < 1e-9
    assert abs(sum(sizes) + 20 - 100) < 1e-9  # two gaps of 10


def test_resolve_tracks_auto_uses_intrinsics():
    sizes = resolve_tracks(
        [Length.auto(), Length.fr(1)],
        50,
        gap_mm=0,
        autos=[12.0, 0.0],
    )
    assert sizes == [12.0, 38.0]
