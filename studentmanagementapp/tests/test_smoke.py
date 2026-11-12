def test_smoke(app, client):
    r = client.get("/api/v1/health")
    print("STATUS", r.status_code, r.get_data(as_text=True)[:300])
