from fastapi.testclient import TestClient

from app.main import app


def client(resources):
    app.state.resources = resources
    return TestClient(app)


def test_invert_endpoint(resources):
    with client(resources) as c:
        res = c.post("/api/invert", json={"text": "高い山に登ります。", "mode": "dict", "seed": 42})
    assert res.status_code == 200
    body = res.json()
    assert body["result"] == "低い谷に下ります。"
    assert body["seed"] == 42
    first = body["tokens"][0]
    assert first == {
        "surface": "高い",
        "lemma": "高い",
        "pos": "形容詞",
        "replaced": "低い",
        "method": "csv",
        "score": None,
    }


def test_invert_rejects_bad_input(resources):
    with client(resources) as c:
        assert c.post("/api/invert", json={"text": ""}).status_code == 422
        assert c.post("/api/invert", json={"text": "あ" * 201}).status_code == 422
        assert c.post("/api/invert", json={"text": "高い", "mode": "llm"}).status_code == 422


def test_health(resources):
    with client(resources) as c:
        body = c.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["antonym_pairs"] > 0
    assert body["vectors_loaded"] is False


def test_frontend_is_served(resources):
    with client(resources) as c:
        res = c.get("/")
    assert res.status_code == 200
    assert "対義文ジェネレーター" in res.text
