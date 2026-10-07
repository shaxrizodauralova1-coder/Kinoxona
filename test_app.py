import hashlib, hmac, json, time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

import api, catalog, config


@pytest.fixture(scope="module")
def c():
    mp = pytest.MonkeyPatch()

    async def fake_resolve(ia):  # tarmoqsiz test
        return "https://archive.org/download/" + ia.split("|")[0] + "/film.mp4"

    mp.setattr(catalog, "resolve", fake_resolve)
    from main import app
    with TestClient(app) as client:
        yield client
    mp.undo()


def test_health(c):
    assert c.get("/health").json() == {"ok": True}
    assert "Kinoxona" in c.get("/").text


def test_bootstrap_catalog(c):
    b = c.get("/api/bootstrap").json()
    assert len(b["movies"]) == len(catalog.FILMS) == 7
    assert {m["st"] for m in b["movies"]} == {"blender", "klassika"}
    assert {s["id"] for s in b["studios"]} == {"blender", "klassika"}
    assert b["user"]["sub"] == "free"


def test_paywall_then_subscribe(c):
    movies = {m["title"]: m for m in c.get("/api/bootstrap").json()["movies"]}
    free, std, prem = movies["Big Buck Bunny"], movies["Sintel"], movies["Nosferatu"]
    assert free["lvl"] == 0 and std["lvl"] == 1 and prem["lvl"] == 2

    r = c.get(f"/api/stream/{free['code']}")
    assert r.status_code == 200 and r.json()["url"].endswith(".mp4")
    assert c.get(f"/api/stream/{std['code']}").status_code == 403
    assert c.get(f"/api/stream/{prem['code']}").status_code == 403

    assert c.post("/api/invoice", json={"plan": "standard"}).json() == {"demo": True}
    assert c.get(f"/api/stream/{std['code']}").status_code == 200
    assert c.get(f"/api/stream/{prem['code']}").status_code == 403

    assert c.post("/api/invoice", json={"plan": "premium"}).json() == {"demo": True}
    assert c.get(f"/api/stream/{prem['code']}").status_code == 200
    assert c.post("/api/invoice", json={"plan": "nope"}).status_code == 400


def test_fav_follow_watch(c):
    code = c.get("/api/bootstrap").json()["movies"][0]["code"]
    assert code in c.post(f"/api/fav/{code}").json()["fav"]
    assert code not in c.post(f"/api/fav/{code}").json()["fav"]
    assert "blender" in c.post("/api/follow/blender").json()["follow"]
    assert c.post(f"/api/watch/{code}").json() == {"ok": True}
    assert code in c.get("/api/bootstrap").json()["user"]["hist"]
    assert c.post("/api/fav/999999").status_code == 404
    assert c.post("/api/follow/yoq").status_code == 404


def test_poster_redirect(c):
    movies = {m["title"]: m for m in c.get("/api/bootstrap").json()["movies"]}
    assert movies["Nosferatu"]["poster"] is True
    r = c.get(f"/api/poster/{movies['Nosferatu']['code']}", follow_redirects=False)
    assert r.status_code == 302 and "archive.org/services/img/" in r.headers["location"]
    assert movies["Tears of Steel"]["poster"] is False
    assert c.get(f"/api/poster/{movies['Tears of Steel']['code']}").status_code == 404


def test_apply_rate_limit(c):
    body = {"name": "Test", "contact": "@test", "about": "salom"}
    assert c.post("/api/apply", json=body).status_code == 200
    assert c.post("/api/apply", json=body).status_code == 429
    assert c.post("/api/apply", json={"name": "", "contact": "x"}).status_code == 422


def test_send_without_bot(c):
    code = c.get("/api/bootstrap").json()["movies"][0]["code"]
    assert c.post(f"/api/send/{code}").status_code == 503


def test_auth_required_without_dev(c, monkeypatch):
    monkeypatch.setattr(config, "DEV", False)
    assert c.get("/api/bootstrap").status_code == 401
    assert c.get("/api/bootstrap", headers={"X-Init-Data": "hash=bad"}).status_code == 401


def test_verify_init_data(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "123:TEST")
    pairs = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 42, "first_name": "Ali"})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", b"123:TEST", hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    assert api.verify(urlencode(pairs))["id"] == 42
    pairs["hash"] = "0" * 64
    assert api.verify(urlencode(pairs)) is None


def test_pick_prefers_h264_and_hint():
    files = [
        {"name": "a_512kb.mp4", "format": "512Kb MPEG4", "size": "40000000"},
        {"name": "a.mp4", "format": "h.264", "size": "300000000"},
        {"name": "a.ogv", "format": "Ogg Video", "size": "1"},
        {"name": "Tears of Steel.mp4", "format": "MPEG4", "size": "50000000"},
        {"name": "Sintel.mp4", "format": "MPEG4", "size": "60000000"},
        {"name": "huge.mp4", "format": "h.264", "size": str(5 * 1024 ** 3)},
    ]
    assert catalog.pick(files) == "a.mp4"
    assert catalog.pick(files, "tears of steel") == "Tears of Steel.mp4"
    assert catalog.pick([{"name": "x.ogv"}]) is None
