from parch.mos.manifest import Manifest


def test_link_or_content_wraps_or_links():
    manifest = Manifest()
    assert manifest.link_or_content("2026-01-15", "15") == "[15]"
    manifest.register_source("2026-01-15")
    assert manifest.link_or_content("2026-01-15", "15") == "padded_link(<2026-01-15>)[15]"
    assert manifest.link_or_content("missing", "Week 1") == "[Week 1]"


def test_dest_is_label_or_none():
    manifest = Manifest()
    assert manifest.dest("2026-01-15") == "none"
    manifest.register_source("2026-01-15")
    assert manifest.dest("2026-01-15") == "<2026-01-15>"
    assert manifest.dest("missing") == "none"
