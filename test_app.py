import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def make(client, **kwargs):
    payload = {"title": "Write report", **kwargs}
    return client.post("/tasks", json=payload)


def test_create_and_get(client):
    res = make(client, priority="high", due_date="2030-01-15")
    assert res.status_code == 201
    task = res.get_json()
    assert task["title"] == "Write report"
    assert task["priority"] == "high"
    assert task["done"] is False

    res = client.get(f"/tasks/{task['id']}")
    assert res.status_code == 200
    assert res.get_json() == task


@pytest.mark.parametrize("payload, message", [
    ({}, "title"),
    ({"title": "   "}, "title"),
    ({"title": "x", "priority": "urgent"}, "priority"),
    ({"title": "x", "due_date": "15/01/2030"}, "due_date"),
    ({"title": "x", "done": "yes"}, "done"),
])
def test_validation(client, payload, message):
    res = client.post("/tasks", json=payload)
    assert res.status_code == 400
    assert message in res.get_json()["error"]


def test_non_json_body_rejected(client):
    res = client.post("/tasks", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_list_filters_and_sorting(client):
    make(client, title="later", due_date="2030-12-01")
    make(client, title="sooner", due_date="2030-01-01", priority="high")
    make(client, title="no date")
    titles = [t["title"] for t in client.get("/tasks").get_json()]
    assert titles == ["sooner", "later", "no date"]

    high = client.get("/tasks?priority=high").get_json()
    assert [t["title"] for t in high] == ["sooner"]


def test_update(client):
    task_id = make(client).get_json()["id"]
    res = client.patch(f"/tasks/{task_id}", json={"done": True, "title": "Final report"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["done"] is True
    assert body["title"] == "Final report"
    assert client.get("/tasks?done=true").get_json()[0]["id"] == task_id


def test_update_missing_task(client):
    assert client.patch("/tasks/999", json={"done": True}).status_code == 404


def test_delete(client):
    task_id = make(client).get_json()["id"]
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404
    assert client.delete(f"/tasks/{task_id}").status_code == 404


def test_stats(client):
    make(client, title="old", due_date="2000-01-01")
    done_id = make(client, title="finished").get_json()["id"]
    client.patch(f"/tasks/{done_id}", json={"done": True})
    assert client.get("/stats").get_json() == {"total": 2, "done": 1, "open": 1, "overdue": 1}
