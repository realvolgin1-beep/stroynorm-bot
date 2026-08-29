from app.catalog import search_catalog


def test_bridge_component_query_finds_bridge_documents():
    hits = search_catalog("Пролетное строение")

    codes = {document["code"] for document in hits}
    assert hits[0]["code"] == "СП 35.13330.2011"
    assert hits[1]["code"] == "ГОСТ 33384-2015"
    assert "СП 35.13330.2011" in codes
    assert "ГОСТ 33384-2015" in codes


def test_road_sign_query_finds_traffic_standard():
    hits = search_catalog("установка дорожных знаков")

    assert hits[0]["code"] == "ГОСТ Р 52289-2019"


def test_typo_in_bridge_query_is_understood():
    hits = search_catalog("пролтное строние")

    assert hits[0]["code"] == "СП 35.13330.2011"


def test_fire_query_finds_evacuation_rules():
    hits = search_catalog("ширина эвакуационного выхода")

    assert hits[0]["code"] == "СП 1.13130.2020"


def test_masonry_query_finds_masonry_rules():
    hits = search_catalog("кирпичная кладка")

    assert hits[0]["code"] == "СП 15.13330.2020"


def test_sp46_compact_number_finds_bridge_construction_rules():
    hits = search_catalog("СП46")

    assert hits[0]["code"] == "СП 46.13330.2012"
