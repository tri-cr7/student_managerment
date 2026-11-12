"""Test tìm kiếm học sinh của Giáo viên — GET /students/search."""
import pytest


def test_search_by_name(app, client, seed_data, auth_headers):
    resp = client.get(
        "/api/v1/students/search?q=Nguy%E1%BB%85n%20V%C4%83n%201",
        headers=auth_headers("TEACHER", seed_data["teacher"].id),
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert len(data) == 1
    assert data[0]["student_code"] == seed_data["students"][0].student_code


def test_search_by_code(app, client, seed_data, auth_headers):
    code = seed_data["students"][1].student_code
    resp = client.get(
        f"/api/v1/students/search?q={code}",
        headers=auth_headers("TEACHER", seed_data["teacher"].id),
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert any(s["student_code"] == code for s in data)


def test_search_empty_returns_all_my_students(app, client, seed_data, auth_headers):
    resp = client.get(
        "/api/v1/students/search",
        headers=auth_headers("TEACHER", seed_data["teacher"].id),
    )
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 3


def test_search_only_my_classes(app, client, seed_data, auth_headers):
    # Không tìm thấy HS thuộc lớp của GV khác, không liệt kê lớp đó
    resp = client.get(
        "/api/v1/students/search?q=Nguy%E1%BB%85n",
        headers=auth_headers("TEACHER", seed_data["teacher"].id),
    )
    assert resp.status_code == 200
    for s in resp.get_json()["data"]:
        for c in s["classes"]:
            assert c["class_id"] == seed_data["class"].id


def test_search_other_class_forbidden(app, client, seed_data, auth_headers):
    resp = client.get(
        f"/api/v1/students/search?class_id={seed_data['other_class'].id}",
        headers=auth_headers("TEACHER", seed_data["teacher"].id),
    )
    assert resp.status_code == 403


def test_search_no_match_returns_empty(app, client, seed_data, auth_headers):
    resp = client.get(
        "/api/v1/students/search?q=ZZZ_KHONG_CO_AI",
        headers=auth_headers("TEACHER", seed_data["teacher"].id),
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"] == []
