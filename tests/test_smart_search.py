from app.smart_search import analyze_query, fts_query


def test_topic_detection_handles_typo():
    profile = analyze_query("допуск для пролтного строния моста")

    assert "bridges" in profile.categories
    assert "measurements" in profile.categories


def test_topic_detection_separates_bridge_from_documentation():
    profile = analyze_query("пролетное строение")

    assert "bridges" in profile.categories
    assert "documentation" not in profile.categories


def test_fts_query_adds_topic_terms():
    query = fts_query("кирпичная кладка")

    assert '"кладк"*' in query
    assert '"конструкц"*' in query


def test_bns_abbreviation_expands_to_bored_pile_topic():
    profile = analyze_query("допуск каркаса БНС")

    assert "буровая" in profile.tokens
    assert "свая" in profile.tokens
    assert "geotechnics" in profile.categories
