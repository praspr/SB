"""Tests for the REST surface using FastAPI's TestClient."""


def test_health(app_client):
    resp = app_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["todos_count"] == 0


def test_create_and_list(app_client):
    resp = app_client.post(
        "/api/todos", json={"title": "Ship it", "priority": 1, "domain": "work"}
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] == 1
    assert created["title"] == "Ship it"
    assert created["priority"] == 1
    assert created["domain"] == "work"
    assert created["is_completed"] is False

    resp = app_client.get("/api/todos")
    assert resp.status_code == 200
    todos = resp.json()
    assert len(todos) == 1
    assert todos[0]["id"] == 1


def test_get_single(app_client):
    created = app_client.post("/api/todos", json={"title": "Task"}).json()
    resp = app_client.get(f"/api/todos/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Task"


def test_get_missing(app_client):
    resp = app_client.get("/api/todos/9999")
    assert resp.status_code == 404


def test_patch_update(app_client):
    created = app_client.post("/api/todos", json={"title": "Old title"}).json()
    resp = app_client.patch(f"/api/todos/{created['id']}", json={"title": "New title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"


def test_complete_and_uncomplete(app_client):
    created = app_client.post("/api/todos", json={"title": "Task"}).json()
    todo_id = created["id"]

    resp = app_client.post(f"/api/todos/{todo_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["is_completed"] is True

    resp = app_client.post(f"/api/todos/{todo_id}/uncomplete")
    assert resp.status_code == 200
    assert resp.json()["is_completed"] is False


def test_delete(app_client):
    created = app_client.post("/api/todos", json={"title": "Delete me"}).json()
    todo_id = created["id"]

    resp = app_client.delete(f"/api/todos/{todo_id}")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True, "id": todo_id}

    resp = app_client.delete(f"/api/todos/{todo_id}")
    assert resp.status_code == 404


def test_search(app_client):
    app_client.post("/api/todos", json={"title": "Fix the login bug"})
    app_client.post("/api/todos", json={"title": "Unrelated task"})

    resp = app_client.get("/api/todos/search", params={"q": "login"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "Fix the login bug"


def test_list_filters(app_client):
    app_client.post("/api/todos", json={"title": "A", "priority": 1, "domain": "work"})
    app_client.post("/api/todos", json={"title": "B", "priority": 3, "domain": "personal"})

    resp = app_client.get("/api/todos", params={"priority": 1})
    assert len(resp.json()) == 1

    resp = app_client.get("/api/todos", params={"domain": "personal"})
    assert len(resp.json()) == 1

    resp = app_client.get("/api/todos", params={"status": "invalid"})
    assert resp.status_code == 400
