def test_seed_data(seed_data):
    assert seed_data["teacher"].id
    assert len(seed_data["students"]) == 3
    assert seed_data["assignment"].teacher_id == seed_data["teacher"].id
    assert seed_data["assignment"].is_locked is False

def test_repositories(teacher_assigned=[]):
    pass
