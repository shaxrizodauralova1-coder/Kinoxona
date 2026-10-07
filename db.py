import aiosqlite, os, time
import config
from config import DB_PATH, PLANS, DAYS

_db = None
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,sub TEXT DEFAULT 'free',exp INTEGER DEFAULT 0,created INTEGER);
CREATE TABLE IF NOT EXISTS studios(id TEXT PRIMARY KEY,name TEXT,about TEXT,hue INTEGER);
CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY,title TEXT,cat TEXT,year INTEGER,minutes INTEGER,descr TEXT,hue INTEGER,studio TEXT,lvl INTEGER DEFAULT 0,video_url TEXT,file_id TEXT,poster_id TEXT,poster_url TEXT,ia TEXT,pub INTEGER DEFAULT 0,created INTEGER);
CREATE TABLE IF NOT EXISTS fav(uid INTEGER,code TEXT,PRIMARY KEY(uid,code));
CREATE TABLE IF NOT EXISTS hist(uid INTEGER,code TEXT,ts INTEGER,PRIMARY KEY(uid,code));
CREATE TABLE IF NOT EXISTS follow(uid INTEGER,studio TEXT,PRIMARY KEY(uid,studio));
CREATE TABLE IF NOT EXISTS pay(id INTEGER PRIMARY KEY AUTOINCREMENT,uid INTEGER,plan TEXT,amount INTEGER,charge TEXT UNIQUE,ts INTEGER);
CREATE TABLE IF NOT EXISTS apps(id INTEGER PRIMARY KEY AUTOINCREMENT,uid INTEGER,name TEXT,contact TEXT,about TEXT,ts INTEGER);
"""
now = lambda: int(time.time() * 1000)
hue = lambda s: sum(map(ord, s)) % 360

async def init():
    global _db
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.executescript(SCHEMA)
    # eski bazalar uchun migratsiya
    cols = {r["name"] for r in await q("PRAGMA table_info(movies)")}
    for c in ("poster_url", "ia"):
        if c not in cols:
            await _db.execute(f"ALTER TABLE movies ADD COLUMN {c} TEXT")
    await _db.commit()


async def close():
    global _db
    if _db:
        await _db.close()
        _db = None

async def q(sql, a=()):
    async with _db.execute(sql, a) as c:
        return [dict(r) for r in await c.fetchall()]

async def one(sql, a=()):
    r = await q(sql, a)
    return r[0] if r else None

async def x(sql, a=()):
    c = await _db.execute(sql, a)
    await _db.commit()
    return c.lastrowid

async def upsert_user(uid, name):
    await x("INSERT INTO users(id,name,created) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",
            (uid, name or "Foydalanuvchi", now()))
    u = await one("SELECT * FROM users WHERE id=?", (uid,))
    if u["sub"] != "free" and u["exp"] < now():
        await x("UPDATE users SET sub='free',exp=0 WHERE id=?", (uid,))
        u["sub"], u["exp"] = "free", 0
    return u

def rank(u):
    return 0 if u["sub"] == "free" else PLANS.get(u["sub"], {"rank": 0})["rank"]

async def activate(uid, plan, days=DAYS):
    await x("INSERT OR IGNORE INTO users(id,name,created) VALUES(?,?,?)", (uid, "Foydalanuvchi", now()))
    u = await one("SELECT * FROM users WHERE id=?", (uid,))
    base = max(now(), u["exp"]) if u["sub"] == plan else now()
    await x("UPDATE users SET sub=?,exp=? WHERE id=?", (plan, base + days * 86400000, uid))

async def user_state(uid):
    fav = [r["code"] for r in await q("SELECT code FROM fav WHERE uid=?", (uid,))]
    hist = [r["code"] for r in await q("SELECT code FROM hist WHERE uid=? ORDER BY ts DESC LIMIT 12", (uid,))]
    fol = [r["studio"] for r in await q("SELECT studio FROM follow WHERE uid=?", (uid,))]
    return {"fav": fav, "hist": hist, "follow": fol}

def pub(m):
    return {"code": m["code"], "title": m["title"], "cat": m["cat"], "year": m["year"], "min": m["minutes"],
            "desc": m["descr"] or "", "h": m["hue"], "st": m["studio"], "lvl": m["lvl"], "poster": bool(m["poster_id"] or m.get("poster_url"))}

async def next_code():
    r = await one("SELECT MAX(CAST(code AS INTEGER)) m FROM movies")
    return str((r["m"] or 1000) + 1)

async def seed():
    """SEED_DEMO=1 va baza bo'sh bo'lsa, bepul qonuniy filmlar katalogini yuklaydi."""
    if not config.SEED_DEMO or await one("SELECT 1 FROM studios"):
        return
    import catalog  # kech import: catalog ham db ni ishlatadi
    await catalog.import_free()
