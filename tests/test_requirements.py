from datetime import date

from app.requirements import answer_requirement, requirement_values_count


def test_bored_pile_cage_returns_all_applicable_tolerances():
    answer = answer_requirement("Отклонение каркаса в буронабивном столбе")
    assert answer is not None
    assert "±1 см" in answer
    assert "±2 см" in answer
    assert "±5 см" in answer
    assert "±10 см" in answer
    assert "СП 46.13330.2012" in answer
    assert "таблица 6, позиция 3" in answer


def test_specific_cage_component_returns_only_its_value():
    answer = answer_requirement("Расстояние между кольцами жесткости каркаса буровой сваи")
    assert answer is not None
    assert "кольцами жёсткости: ±10 см" in answer
    assert "шаг спирали" not in answer


def test_asphalt_elevation_explains_percentile_limits():
    answer = answer_requirement("отклонение по высоте асфальт верхнего слоя А16")
    assert answer is not None
    assert "90% результатов" in answer
    assert "±10 мм" in answer
    assert "10% результатов" in answer
    assert "±20 мм" in answer
    assert "ГОСТ Р 59120-2021" in answer
    assert "8.10.1–8.10.2" in answer
    assert "СП 78.13330.2012" in answer


def test_asphalt_thickness_is_not_confused_with_elevation():
    answer = answer_requirement("допуск толщины верхнего слоя асфальта А16 по керну")
    assert answer is not None
    assert "уменьшение не более 20%" in answer
    assert "уменьшение не более 15%" in answer
    assert "±20 мм" not in answer
    assert "пункты 8.1.1 и 8.1.3" in answer


def test_unknown_or_underspecified_query_is_not_guessed():
    assert answer_requirement("отклонение каркаса здания") is None
    assert answer_requirement("какой допуск") is None


def test_column_axis_question_returns_values_not_only_document_cards():
    answer = answer_requirement("отклонение от плана или оси колонн")
    assert answer is not None
    assert "стальная колонна одноэтажного здания" in answer
    assert "±5 мм" in answer
    assert "сборная железобетонная колонна" in answer
    assert "8 мм" in answer
    assert "Σh/(200√n)" in answer
    assert "таблица 4.9, позиция 3" in answer
    assert "таблица 6.1, позиция 3" in answer
    assert "Официальная карточка" in answer


def test_typo_in_column_deviation_still_matches_numeric_rule():
    answer = answer_requirement("отклоение оси колон")
    assert answer is not None
    assert "±5 мм" in answer
    assert "СП 70.13330.2012" in answer


def test_specific_steel_column_support_section_filters_variants():
    answer = answer_requirement("смещение оси стальной колонны в опорном сечении")
    assert answer is not None
    assert "опорном сечении: ±5 мм" in answer
    assert "сборная железобетонная колонна" not in answer
    assert "Σh/(200√n)" not in answer


def test_plural_steel_beams_query_matches_tolerances():
    answer = answer_requirement("монтаж стальных балок")
    assert answer is not None
    assert "СП 70.13330.2012" in answer
    assert "таблица 4.9" in answer


def test_precast_column_verticality_returns_length_ranges():
    answer = answer_requirement("вертикальность сборной жб колонны одноэтажного здания")
    assert answer is not None
    assert "20 / 25 / 30 / 40 мм" in answer
    assert "таблица 6.1, позиция 4" in answer
    assert "±10 / ±12 / ±15 / ±20 мм" not in answer


def test_monolithic_anchor_bolt_plan_tolerance():
    answer = answer_requirement("допуск анкерных болтов в плане внутри контура опоры")
    assert answer is not None
    assert "внутри контура опоры: 5 мм" in answer
    assert "таблица 5.12, позиция 10" in answer
    assert "вне контура" not in answer


def test_excavation_final_bottom_level_tolerance():
    answer = answer_requirement("отклонение отметки дна котлована после окончательной разработки")
    assert answer is not None
    assert "±5 см" in answer
    assert "таблица 6.3, позиция 5" in answer
    assert "драглайном" not in answer


def test_current_plaster_rule_does_not_repeat_removed_tolerances():
    answer = answer_requirement("допуск штукатурки от вертикали")
    assert answer is not None
    assert "требованиям заказчика" in answer
    assert "таблица 7.4 исключена" in answer
    assert "нельзя выдавать как действующее" in answer


def test_rebar_lap_length_returns_formula_and_clause():
    answer = answer_requirement("допуск длины нахлеста арматуры")
    assert answer is not None
    assert "не менее 0,95L" in answer
    assert "таблица 5.10, позиция 3" in answer


def test_rebar_cover_uses_both_dimensions():
    answer = answer_requirement("защитный слой 20 мм сечение 300 мм допуск")
    assert answer is not None
    assert "+10 / −3 мм" in answer
    assert "таблица 5.10, позиция 7" in answer


def test_rebar_cover_genitive_form_is_understood():
    answer = answer_requirement("допуск защитного слоя бетона")
    assert answer is not None
    assert "таблица 5.10, позиция 7" in answer


def test_brick_wall_axis_tolerance():
    answer = answer_requirement("смещение кирпичной стены от разбивочной оси")
    assert answer is not None
    assert "от разбивочной оси: 10 мм" in answer
    assert "таблица 9.8" in answer


def test_requirement_value_counter_counts_verified_values():
    assert requirement_values_count(date(2026, 8, 30)) == 92


def test_time_limited_values_are_not_returned_after_replacement_date():
    answer = answer_requirement("отклонение оси колонны", date(2027, 3, 1))
    assert answer is None
