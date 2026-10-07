import asyncio, logging
from urllib.parse import urlencode
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (InlineKeyboardButton as B, InlineKeyboardMarkup as M, WebAppInfo, Message,
                           CallbackQuery, PreCheckoutQuery, MenuButtonWebApp)
import config, db, catalog

log = logging.getLogger("bot")
bot = Bot(config.BOT_TOKEN) if config.BOT_TOKEN else None
dp = Dispatcher(storage=MemoryStorage())
r = Router()
dp.include_router(r)
adm = F.from_user.id.in_(config.ADMIN_IDS)


def app_kb(text="Kinoxonani ochish", **q):
    url = config.WEBAPP_URL + ("?" + urlencode(q) if q else "")
    return M(inline_keyboard=[[B(text=text, web_app=WebAppInfo(url=url))]])


async def is_member(uid):
    for ch in config.CHANNELS:
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status in ("left", "kicked"):
                return False
        except Exception as e:  # bot kanalda admin emas yoki kanal noto'g'ri
            log.warning("Kanal tekshiruvi %s: %s", ch, e)
    return True


def sub_kb():
    rows = [[B(text=f"Obuna bo'lish: {c}", url=f"https://t.me/{c.lstrip('@')}")] for c in config.CHANNELS]
    return M(inline_keyboard=rows + [[B(text="Tekshirish", callback_data="chk")]])


async def deliver(cid, mv):
    cap = f"🎬 {mv['title']}\n{mv['cat']}, {mv['year']}, {mv['minutes']} daqiqa\n\n{mv['descr'] or ''}"[:1000]
    if mv["file_id"]:
        await bot.send_video(cid, mv["file_id"], caption=cap, protect_content=True)
    else:
        await bot.send_message(cid, cap, reply_markup=app_kb("Mini Appda ko'rish", code=mv["code"]))


async def notify_admins(text):
    if not bot:
        return
    for a in config.ADMIN_IDS:
        try:
            await bot.send_message(a, text)
        except Exception as e:
            log.warning("Admin %s ga yuborilmadi: %s", a, e)


async def send_code(m: Message, code):
    u = await db.upsert_user(m.from_user.id, m.from_user.first_name)
    mv = await db.one("SELECT * FROM movies WHERE code=? AND pub=1", (code,))
    if not mv:
        return await m.answer("Bunday kodli kino topilmadi.")
    if mv["lvl"] > db.rank(u):
        pl = "Premium" if mv["lvl"] == 2 else "Standart"
        return await m.answer(f"«{mv['title']}» {pl} obunada mavjud.", reply_markup=app_kb("Obunani tanlash", view="subs"))
    await deliver(m.chat.id, mv)
    await db.x("INSERT INTO hist(uid,code,ts) VALUES(?,?,?) ON CONFLICT(uid,code) DO UPDATE SET ts=excluded.ts",
               (m.from_user.id, code, db.now()))


# ---------- admin ----------
class Add(StatesGroup):
    video = State()
    poster = State()

USAGE = ("Format:\n/addmovie Sarlavha | Kategoriya | studiya_id | yil | daqiqa | daraja | tavsif\n"
         f"Kategoriya: {', '.join(config.CATS)}\nDaraja: 0 bepul, 1 Standart, 2 Premium")


@r.message(Command("cancel"), adm)
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.")


@r.message(Command("addstudio"), adm)
async def addstudio(m: Message, command: CommandObject):
    p = [x.strip() for x in (command.args or "").split("|")]
    if len(p) < 3 or not p[0].isalnum():
        return await m.answer("Format: /addstudio id | Nomi | Tavsif")
    await db.x("INSERT OR REPLACE INTO studios VALUES(?,?,?,?)", (p[0].lower(), p[1], p[2], db.hue(p[1])))
    await m.answer("Studiya saqlandi.")


@r.message(Command("addmovie"), adm)
async def addmovie(m: Message, command: CommandObject, state: FSMContext):
    p = [x.strip() for x in (command.args or "").split("|")]
    try:
        title, cat, st, year, mins, lvl = p[0], p[1], p[2].lower(), int(p[3]), int(p[4]), int(p[5])
        desc = " | ".join(p[6:])
        cat = next(c for c in config.CATS if c.lower() == cat.lower())
        assert lvl in (0, 1, 2) and title and await db.one("SELECT 1 FROM studios WHERE id=?", (st,))
    except Exception:
        return await m.answer(USAGE)
    code = await db.next_code()
    await db.x("INSERT INTO movies(code,title,cat,year,minutes,descr,hue,studio,lvl,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
               (code, title, cat, year, mins, desc, db.hue(title), st, lvl, db.now()))
    await state.set_state(Add.video)
    await state.update_data(code=code)
    await m.answer(f"Kod: {code}. Endi videoni fayl qilib yuboring yoki https havola yozing.")


@r.message(Add.video, adm)
async def got_video(m: Message, state: FSMContext):
    code = (await state.get_data())["code"]
    if m.video:
        await db.x("UPDATE movies SET file_id=? WHERE code=?", (m.video.file_id, code))
    elif m.document and (m.document.mime_type or "").startswith("video"):
        await db.x("UPDATE movies SET file_id=? WHERE code=?", (m.document.file_id, code))
    elif m.text and m.text.startswith("https://"):
        await db.x("UPDATE movies SET video_url=? WHERE code=?", (m.text.strip(), code))
    else:
        return await m.answer("Video fayl yoki https havola yuboring (/cancel bekor qiladi).")
    await state.set_state(Add.poster)
    await m.answer("Poster rasmini yuboring yoki /skip.")


@r.message(Add.poster, adm)
async def got_poster(m: Message, state: FSMContext):
    code = (await state.get_data())["code"]
    if m.photo:
        await db.x("UPDATE movies SET poster_id=? WHERE code=?", (m.photo[-1].file_id, code))
    elif not (m.text or "").startswith("/skip"):
        return await m.answer("Rasm yuboring yoki /skip.")
    await db.x("UPDATE movies SET pub=1 WHERE code=?", (code,))
    await state.clear()
    await m.answer(f"Joylandi. Kod: {code}")


@r.message(Command("seturl"), adm)
async def seturl(m: Message, command: CommandObject):
    p = (command.args or "").split()
    if len(p) != 2 or not p[1].startswith("https://"):
        return await m.answer("Format: /seturl kod https://...")
    await db.x("UPDATE movies SET video_url=? WHERE code=?", (p[1], p[0]))
    await m.answer("Saqlandi.")


@r.message(Command("delmovie"), adm)
async def delmovie(m: Message, command: CommandObject):
    code = (command.args or "").strip()
    await db.x("DELETE FROM movies WHERE code=?", (code,))
    await db.x("DELETE FROM fav WHERE code=?", (code,))
    await db.x("DELETE FROM hist WHERE code=?", (code,))
    await m.answer("O'chirildi.")


@r.message(Command("setlevel"), adm)
async def setlevel(m: Message, command: CommandObject):
    p = (command.args or "").split()
    try:
        code, lvl = p[0], int(p[1])
        assert lvl in (0, 1, 2) and await db.one("SELECT 1 FROM movies WHERE code=?", (code,))
    except Exception:
        return await m.answer("Format: /setlevel kod 0|1|2  (0 bepul, 1 Standart, 2 Premium)")
    await db.x("UPDATE movies SET lvl=? WHERE code=?", (lvl, code))
    await m.answer("Daraja o'zgardi.")


@r.message(Command("importfree"), adm)
async def importfree(m: Message):
    n = await catalog.import_free()
    await m.answer(f"Bepul katalogdan qo'shildi: {n} ta film. Darajani /setlevel bilan o'zgartiring.")


@r.message(Command("help"), adm)
async def admin_help(m: Message):
    await m.answer("Admin buyruqlari:\n/addstudio, /addmovie, /seturl, /setlevel, /delmovie, /movies\n"
                   "/importfree, /grant, /stats, /apps, /broadcast, /cancel")


@r.message(Command("movies"), adm)
async def movies(m: Message):
    rows = await db.q("SELECT code,title,lvl,pub FROM movies ORDER BY created DESC LIMIT 40")
    await m.answer("\n".join(f"{x['code']}  {x['title']}  daraja {x['lvl']}{'' if x['pub'] else '  (yashirin)'}" for x in rows) or "Bo'sh")


@r.message(Command("grant"), adm)
async def grant(m: Message, command: CommandObject):
    p = (command.args or "").split()
    try:
        uid, plan, days = int(p[0]), p[1], int(p[2])
        assert plan in config.PLANS
    except Exception:
        return await m.answer("Format: /grant user_id standard|premium kun")
    await db.activate(uid, plan, days)
    await m.answer("Obuna berildi.")


@r.message(Command("stats"), adm)
async def stats(m: Message):
    n = (await db.one("SELECT COUNT(*) c FROM users"))["c"]
    s = (await db.one("SELECT COUNT(*) c FROM users WHERE sub!='free' AND exp>?", (db.now(),)))["c"]
    mv = (await db.one("SELECT COUNT(*) c FROM movies WHERE pub=1"))["c"]
    rev = (await db.one("SELECT COALESCE(SUM(amount),0) c FROM pay"))["c"]
    await m.answer(f"Foydalanuvchilar: {n}\nFaol obuna: {s}\nKinolar: {mv}\nDaromad: {rev:,} so'm")


@r.message(Command("apps"), adm)
async def apps(m: Message):
    rows = await db.q("SELECT * FROM apps ORDER BY ts DESC LIMIT 10")
    await m.answer("\n\n".join(f"{x['name']}\n{x['contact']}\n{x['about']}" for x in rows) or "Arizalar yo'q")


@r.message(Command("broadcast"), adm)
async def broadcast(m: Message, command: CommandObject):
    if not command.args:
        return await m.answer("Format: /broadcast matn")
    ok = 0
    for u in await db.q("SELECT id FROM users"):
        try:
            await bot.send_message(u["id"], command.args)
            ok += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"Yuborildi: {ok}")


# ---------- to'lov ----------
@r.pre_checkout_query()
async def pre(q: PreCheckoutQuery):
    await q.answer(ok=True)


@r.message(F.successful_payment)
async def paid(m: Message):
    sp = m.successful_payment
    try:
        _, plan, uid = sp.invoice_payload.split(":")
        assert plan in config.PLANS and int(uid) == m.from_user.id
    except Exception:
        return log.error("Noto'g'ri to'lov payload: %s", sp.invoice_payload)
    if await db.one("SELECT 1 FROM pay WHERE charge=?", (sp.telegram_payment_charge_id,)):
        return
    await db.x("INSERT INTO pay(uid,plan,amount,charge,ts) VALUES(?,?,?,?,?)",
               (m.from_user.id, plan, sp.total_amount // 100, sp.telegram_payment_charge_id, db.now()))
    await db.activate(m.from_user.id, plan)
    await m.answer(f"To'lov qabul qilindi. {config.PLANS[plan]['name']} obunasi {config.DAYS} kunga faollashdi.", reply_markup=app_kb())


# ---------- foydalanuvchi ----------
@r.message(CommandStart())
async def start(m: Message, command: CommandObject):
    await db.upsert_user(m.from_user.id, m.from_user.first_name)
    if not await is_member(m.from_user.id):
        return await m.answer("Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=sub_kb())
    code = (command.args or "").strip()
    if code.isdigit():
        return await send_code(m, code)
    await m.answer("Kinoxonaga xush kelibsiz!\nKino kodini yuboring yoki Web ilovani oching.", reply_markup=app_kb())


@r.callback_query(F.data == "chk")
async def chk(c: CallbackQuery):
    if await is_member(c.from_user.id):
        await c.message.edit_text("Rahmat! Kino kodini yuboring yoki Web ilovani oching.", reply_markup=app_kb())
    else:
        await c.answer("Hali obuna bo'lmadingiz", show_alert=True)


@r.message(F.text.regexp(r"^\d{3,8}$"))
async def by_code(m: Message):
    if not await is_member(m.from_user.id):
        return await m.answer("Avval kanallarga obuna bo'ling:", reply_markup=sub_kb())
    await send_code(m, m.text)


@r.message(F.text)
async def fallback(m: Message):
    await m.answer("Kino kodini yuboring (masalan 1002) yoki Web ilovani oching.", reply_markup=app_kb())


async def run():
    if not bot:
        return log.warning("BOT_TOKEN yo'q: bot ishga tushmadi, faqat API ishlaydi")
    try:
        if config.WEBAPP_URL:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Kinoxona", web_app=WebAppInfo(url=config.WEBAPP_URL)))
        await bot.delete_webhook()
        await dp.start_polling(bot, handle_signals=False)
    except asyncio.CancelledError:
        raise
    except Exception:
        log.exception("Bot to'xtadi")
