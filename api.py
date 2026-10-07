import os, json, time, hmac, hashlib
from urllib.parse import parse_qsl
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from aiogram.types import LabeledPrice
import config, db, catalog
import bot as tb

r = APIRouter(prefix="/api")
POSTERS = os.path.join(os.path.dirname(config.DB_PATH) or ".", "posters")


def verify(init: str):
    pairs = dict(parse_qsl(init, keep_blank_values=True))
    h = pairs.pop("hash", None)
    if not h or not config.BOT_TOKEN:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(hmac.new(secret, check.encode(), hashlib.sha256).hexdigest(), h):
        return None
    if time.time() - int(pairs.get("auth_date", "0")) > 86400:
        return None
    try:
        return json.loads(pairs["user"])
    except Exception:
        return None


async def me(x_init_data: str = Header(default="")):
    if not x_init_data:
        if config.DEV:
            return await db.upsert_user(1, "Dev")
        raise HTTPException(401, "Telegram ichida oching")
    u = verify(x_init_data)
    if not u:
        raise HTTPException(401, "Avtorizatsiya xatosi")
    return await db.upsert_user(u["id"], u.get("first_name"))


async def toggle(table, col, uid, val):
    if await db.one(f"SELECT 1 FROM {table} WHERE uid=? AND {col}=?", (uid, val)):
        await db.x(f"DELETE FROM {table} WHERE uid=? AND {col}=?", (uid, val))
    else:
        await db.x(f"INSERT INTO {table}(uid,{col}) VALUES(?,?)", (uid, val))


async def get_movie(code, u):
    m = await db.one("SELECT * FROM movies WHERE code=? AND pub=1", (code,))
    if not m:
        raise HTTPException(404, "Kino topilmadi")
    if m["lvl"] > db.rank(u):
        raise HTTPException(403, "Bu kino uchun obuna kerak")
    return m


@r.get("/bootstrap")
async def bootstrap(u=Depends(me)):
    ms = await db.q("SELECT * FROM movies WHERE pub=1 ORDER BY created")
    sts = await db.q("SELECT s.*,(SELECT COUNT(*) FROM follow f WHERE f.studio=s.id) fol FROM studios s")
    return {"user": {"id": u["id"], "name": u["name"], "sub": u["sub"], "exp": u["exp"], **await db.user_state(u["id"])},
            "movies": [db.pub(m) for m in ms],
            "studios": [{"id": s["id"], "name": s["name"], "about": s["about"], "h": s["hue"], "fol": str(s["fol"])} for s in sts]}


@r.post("/fav/{code}")
async def fav(code: str, u=Depends(me)):
    if not await db.one("SELECT 1 FROM movies WHERE code=? AND pub=1", (code,)):
        raise HTTPException(404, "Kino topilmadi")
    await toggle("fav", "code", u["id"], code)
    return {"fav": (await db.user_state(u["id"]))["fav"]}


@r.post("/follow/{sid}")
async def follow(sid: str, u=Depends(me)):
    if not await db.one("SELECT 1 FROM studios WHERE id=?", (sid,)):
        raise HTTPException(404, "Studiya topilmadi")
    await toggle("follow", "studio", u["id"], sid)
    return {"follow": (await db.user_state(u["id"]))["follow"]}


@r.post("/watch/{code}")
async def watch(code: str, u=Depends(me)):
    await get_movie(code, u)
    await db.x("INSERT INTO hist(uid,code,ts) VALUES(?,?,?) ON CONFLICT(uid,code) DO UPDATE SET ts=excluded.ts", (u["id"], code, db.now()))
    return {"ok": True}


@r.get("/stream/{code}")
async def stream(code: str, u=Depends(me)):
    m = await get_movie(code, u)
    url = m["video_url"]
    if not url and m["ia"]:
        # archive.org dagi film: birinchi ijroda MP4 havolasi topilib bazaga saqlanadi
        url = await catalog.resolve(m["ia"])
        if url:
            await db.x("UPDATE movies SET video_url=? WHERE code=?", (url, code))
        else:
            raise HTTPException(502, "Video manbasi hozir javob bermayapti, keyinroq urinib ko'ring")
    if not url:
        raise HTTPException(404, "Bu kino Mini Appda yo'q, 'Botga yuborish' tugmasidan foydalaning")
    return {"url": url}


@r.post("/send/{code}")
async def send(code: str, u=Depends(me)):
    m = await get_movie(code, u)
    if not tb.bot:
        raise HTTPException(503, "Bot sozlanmagan")
    await tb.deliver(u["id"], m)
    return {"ok": True}


@r.get("/poster/{code}")
async def poster(code: str):
    m = await db.one("SELECT poster_id,poster_url FROM movies WHERE code=? AND pub=1", (code,))
    if not m:
        raise HTTPException(404)
    if m["poster_url"]:
        return RedirectResponse(m["poster_url"], 302, headers={"Cache-Control": "public,max-age=86400"})
    if not m["poster_id"] or not tb.bot:
        raise HTTPException(404)
    path = os.path.join(POSTERS, hashlib.md5(m["poster_id"].encode()).hexdigest() + ".jpg")
    if not os.path.exists(path):
        os.makedirs(POSTERS, exist_ok=True)
        await tb.bot.download(m["poster_id"], destination=path)
    return FileResponse(path, headers={"Cache-Control": "public,max-age=86400"})


class Inv(BaseModel):
    plan: str


@r.post("/invoice")
async def invoice(b: Inv, u=Depends(me)):
    p = config.PLANS.get(b.plan)
    if not p:
        raise HTTPException(400, "Reja topilmadi")
    if config.DEMO_PAYMENTS:
        await db.activate(u["id"], b.plan)
        return {"demo": True}
    if not (tb.bot and config.PROVIDER_TOKEN):
        raise HTTPException(503, "To'lov hali sozlanmagan")
    link = await tb.bot.create_invoice_link(
        title=f"Kinoxona {p['name']}", description=f"{config.DAYS} kunlik obuna",
        payload=f"sub:{b.plan}:{u['id']}", provider_token=config.PROVIDER_TOKEN, currency="UZS",
        prices=[LabeledPrice(label=p["name"], amount=p["price"] * 100)])
    return {"link": link}


class App(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    contact: str = Field(min_length=1, max_length=80)
    about: str = Field(default="", max_length=1000)


@r.post("/apply")
async def apply(b: App, u=Depends(me)):
    last = await db.one("SELECT ts FROM apps WHERE uid=? ORDER BY ts DESC", (u["id"],))
    if last and db.now() - last["ts"] < 3600000:
        raise HTTPException(429, "Ariza yaqinda yuborilgan, keyinroq urinib ko'ring")
    await db.x("INSERT INTO apps(uid,name,contact,about,ts) VALUES(?,?,?,?,?)", (u["id"], b.name, b.contact, b.about, db.now()))
    await tb.notify_admins(f"Yangi hamkorlik arizasi\n{b.name}\n{b.contact}\n{b.about}\nTelegram ID: {u['id']}")
    return {"ok": True}
