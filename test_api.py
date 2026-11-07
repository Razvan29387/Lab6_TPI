from fastapi.testclient import TestClient
from main import app, DB  # importă instanța din fisierul tău

client = TestClient(app)

def setup_function():
    # Curățăm DB înainte de fiecare rulare completă a modulului de teste
    # pentru a asigura comportament predictibil.
    pass

def test_1_post_valid_reading():
    DB.clear() # pornim cu un mediu curat (server proaspăt pornit)
    resp = client.post("/readings", json={"dev":"senzor-1", "seq":1, "ts":1762096000, "temp":21.5, "hum":40})
    assert resp.status_code == 201

def test_2_post_duplicate_seq():
    # Aceeași cerere de la #1 ar trebui să genereze 409
    resp = client.post("/readings", json={"dev":"senzor-1", "seq":1, "ts":1762096000, "temp":21.5, "hum":40})
    assert resp.status_code == 409

def test_3_post_temp_out_of_bounds():
    # seq=2, dar temp=100 (>85 max admis)
    resp = client.post("/readings", json={"dev":"senzor-1", "seq":2, "ts":1762096000, "temp":100, "hum":40})
    assert resp.status_code == 422

def test_4_post_invalid_dev_name():
    # majuscule și spațiu nepermis de regex
    resp = client.post("/readings", json={"dev":"Senzor 1", "seq":2, "ts":1762096000, "temp":21.5, "hum":40})
    assert resp.status_code == 422

def test_5_post_missing_hum():
    # seq=2, fără hum (care e opțional)
    resp = client.post("/readings", json={"dev":"senzor-1", "seq":2, "ts":1762096000, "temp":21.5})
    assert resp.status_code == 201

def test_6_get_all_readings():
    # default since=0 (seq > 0), le va prinde pe 1 și 2
    resp = client.get("/devices/senzor-1/readings")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

def test_7_get_with_since():
    # since=1 -> trebuie să returneze doar seq > 1 (adică seq 2)
    resp = client.get("/devices/senzor-1/readings?since=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["seq"] == 2

def test_8_get_with_limit():
    # limit=1, returnează doar primul (seq 1)
    resp = client.get("/devices/senzor-1/readings?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["seq"] == 1

def test_9_get_invalid_limit():
    # limit=0 (sub limit ge=1)
    resp = client.get("/devices/senzor-1/readings?limit=0")
    assert resp.status_code == 422

def test_10_get_unknown_device():
    # dispozitiv care nu are înregistrări
    resp = client.get("/devices/necunoscut/readings")
    assert resp.status_code == 404

def test_11_get_invalid_dev_id():
    # dev_id cu majuscule nu corespunde Path pattern
    resp = client.get("/devices/ABC/readings")
    assert resp.status_code == 422