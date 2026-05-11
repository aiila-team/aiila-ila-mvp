from uuid import uuid4


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_auth_login_invalid(client):
    r = client.post("/api/v1/auth/login", json={"username": "nope", "password": "bad"})
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body or "error" in body


def test_auth_login_ok(client):
    r = client.post("/api/v1/auth/login", json={"username": "likhitha", "password": "ila@2026"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data


def test_auth_me_unauthorized(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_dashboard_stats(client):
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    j = r.json()
    assert "total_entities" in j
    assert "alerts_last_24h_by_hour" in j
    assert "high_risk_entities" in j


def test_search_requires_q(client):
    r = client.get("/api/v1/search")
    assert r.status_code == 422


def test_search_ok(client):
    r = client.get("/api/v1/search", params={"q": "test", "page": 1, "page_size": 5})
    assert r.status_code == 200
    j = r.json()
    assert j["query"] == "test"
    assert "items" in j


def test_sources_list(client):
    r = client.get("/api/v1/sources")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_entities_list(client):
    r = client.get("/api/v1/entities")
    assert r.status_code == 200
    assert "items" in r.json()


def test_alerts_list(client):
    r = client.get("/api/v1/alerts")
    assert r.status_code == 200
    assert "items" in r.json()


def test_alert_patch_not_found(client):
    tok = client.post("/api/v1/auth/login", json={"username": "likhitha", "password": "ila@2026"}).json()[
        "access_token"
    ]
    rid = str(uuid4())
    r = client.patch(
        f"/api/v1/alerts/{rid}/status",
        headers={"Authorization": f"Bearer {tok}"},
        json={"status": "under_review"},
    )
    assert r.status_code == 404


def test_investigation_not_found(client):
    tok = client.post("/api/v1/auth/login", json={"username": "likhitha", "password": "ila@2026"}).json()[
        "access_token"
    ]
    r = client.get(
        f"/api/v1/investigations/{uuid4()}",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 404


def test_evidence_validation_error(client):
    tok = client.post("/api/v1/auth/login", json={"username": "likhitha", "password": "ila@2026"}).json()[
        "access_token"
    ]
    r = client.post(
        "/api/v1/evidence",
        headers={"Authorization": f"Bearer {tok}"},
        json={"entity_id": str(uuid4()), "investigation_note": ""},
    )
    assert r.status_code == 422
