from parch.ir.nodes import Col, Length, Row, Text
from parch.ir.units import resolve_tracks


def test_col_fr_split_matches_resolve_tracks():
    col = Col(
        children=[Text("a"), Text("b"), Text("c")],
        gap=Length.mm(2),
        weights=[Length.mm(10), Length.fr(1), Length.fr(1)],
    )
    heights = resolve_tracks(col.weights, 40, gap_mm=2)
    assert abs(heights[0] - 10) < 1e-9
    assert abs(heights[1] - heights[2]) < 1e-9
    assert abs(sum(heights) + 4 - 40) < 1e-9


def test_row_equal_fr_when_weights_omitted():
    row = Row(children=[Text("L"), Text("R")], gap=Length.mm(4))
    weights = row.weights if row.weights is not None else [Length.fr(1)] * len(row.children)
    widths = resolve_tracks(weights, 20, gap_mm=4)
    assert widths == [8.0, 8.0]
