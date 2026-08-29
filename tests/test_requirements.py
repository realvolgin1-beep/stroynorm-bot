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


def test_requirement_value_counter_counts_verified_values():
    assert requirement_values_count() == 15
