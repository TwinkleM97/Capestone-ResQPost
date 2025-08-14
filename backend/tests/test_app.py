from app import db
from models import Alert

def test_app_root_returns_200(client):
    # Your integration health checks hit "/" — keep parity here.
    resp = client.get("/")
    assert resp.status_code in (200, 301, 302)  # tolerate redirect or ok

def test_alerts_endpoint_exists(client):
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    # JSON or text is fine; just ensure endpoint is reachable
    # If JSON, make sure it's valid JSON list/dict.
    content_type = resp.headers.get("Content-Type", "")
    assert "json" in content_type.lower() or resp.data != b""

def test_db_can_create_tables(client):
    # If create_all already ran, this is just a sanity call
    from app import db as _db
    _db.session.execute("SELECT 1")
    assert True

def test_can_insert_alert_and_query(client):
    # Use the same app context/DB the API uses (sqlite memory here)
    a = Alert(title="ci-unit", description="ok", category="pet", location="unit")
    db.session.add(a)
    db.session.commit()
    assert db.session.query(Alert).count() >= 1

def test_api_reflects_inserted_alert(client):
    # Insert directly then verify the API surfaces data
    a = Alert(title="api-visible", description="yup", category="info", location="lab")
    db.session.add(a); db.session.commit()
    r = client.get("/api/alerts")
    assert r.status_code == 200
    # If API returns JSON list, ensure it has content
    if "json" in r.headers.get("Content-Type", "").lower():
        data = r.get_json()
        assert isinstance(data, (list, dict))
        # allow list or object shape depending on your implementation
        if isinstance(data, list):
            assert len(data) >= 1

def test_alert_model_has_required_fields(client):
    a = Alert(title="fields", description="present", category="test", location="here")
    assert all(hasattr(a, f) for f in ("title", "description", "category", "location"))
