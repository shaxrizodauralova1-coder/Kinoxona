# Kinoxona: Telegram bot + Mini App platforma

Bitta Python jarayon: **FastAPI** (API va Mini App) + **aiogram 3** (bot) + **SQLite**.
Obuna (Standart/Premium), majburiy kanal obunasi, sevimlilar, studiyalar, hamkorlik arizasi, admin buyruqlari.
Namunaviy kontent: qonuniy bepul filmlar (Blender open movies, public domain klassika), [CATALOG.md](CATALOG.md).

## 1. Lokal sinov (Telegramsiz, 2 daqiqa)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # Windows: copy .env.example .env
```
`.env` ichida `DEV=1`, `DEMO_PAYMENTS=1`, `SEED_DEMO=1` qiling, so'ng:
```bash
uvicorn main:app --reload
```
Brauzerda http://localhost:8000 oching. 7 ta film yuklanadi, ijro, obuna (demo), sevimlilar, studiyalar ishlaydi.
Telegram yo'q bo'lgani uchun bot yoqilmaydi, bu normal.

Testlar: `pip install -r requirements-dev.txt && pytest -q`

## 2. Haqiqiy ishga tushirish
1. @BotFather: `/newbot`, tokenni `.env` dagi `BOT_TOKEN` ga yozing.
2. Serverga joylang (Render, Railway, Fly.io yoki VPS). **HTTPS domen shart.**
   Docker: `docker compose up -d --build` (ma'lumotlar `./data` papkasida saqlanadi).
   Faqat **1 nusxa** ishlasin, SQLite uchun doimiy disk (volume) ulang, `DB_PATH` ni shu diskka qo'ying.
3. `.env` (productionda): `BOT_TOKEN`, `ADMIN_IDS` (Telegram ID, @userinfobot dan oling), `WEBAPP_URL` (https domen),
   `CHANNELS` (majburiy obuna kanallari), `PROVIDER_TOKEN`.
   `DEV`, `DEMO_PAYMENTS` ni **0** qiling. `DEMO_PAYMENTS=1` bo'lsa hamma obunani bepul oladi!
   Bepul filmlar kerak bo'lsa, botda admin sifatida `/importfree` yozing (SEED_DEMO shart emas).
4. Majburiy obuna: botni har bir kanalga ADMIN qilib qo'shing.
5. To'lov (so'm): BotFather, `/mybots`, botingiz, Payments, Payme yoki Click. Bergan provider tokenni `PROVIDER_TOKEN` ga yozing. Avval test tokenda sinang.

## 3. Admin buyruqlari (botda)
| Buyruq | Vazifasi |
|---|---|
| `/addstudio id \| Nomi \| Tavsif` | Studiya qo'shish |
| `/addmovie Sarlavha \| Kategoriya \| studiya_id \| yil \| daqiqa \| daraja \| tavsif` | Kino qo'shish, keyin bot video (fayl yoki https havola) va poster so'raydi |
| `/seturl KOD https://...` | Mini App uchun video havola (MP4 yoki HLS .m3u8) |
| `/setlevel KOD 0\|1\|2` | Daraja: 0 bepul, 1 Standart, 2 Premium |
| `/importfree` | Bepul filmlar katalogini qo'shish |
| `/movies`, `/delmovie KOD` | Ro'yxat, o'chirish |
| `/grant USER_ID standard\|premium KUN` | Naqd to'lov uchun qo'lda obuna |
| `/stats`, `/apps`, `/broadcast MATN`, `/cancel`, `/help` | Statistika, arizalar, xabar yuborish |

Kategoriyalar: Kino, Multfilm, Serial, Shaxsiy ijod.

**Video haqida:** fayl sifatida yuborilsa, Telegram orqali bot chatida ochiladi (`protect_content` bilan).
Mini App ichida ijro uchun https havola kerak (Cloudflare R2, Bunny Stream va h.k.). To'liq himoya uchun imzolangan (muddatli) havolalar ishlating.

## 4. Foydalanuvchi uchun
- Botga kino kodi yozilsa (masalan 1002) kino keladi, obunasi yetmasa obuna tugmasi chiqadi.
- "Kinoxona" menyu tugmasi Mini Appni ochadi.
- Ijodkorlar Mini Appdagi "Hamkor bo'lish" formasi orqali ariza yuboradi, adminlarga xabar keladi.

## 5. Tuzilma
```
main.py      FastAPI + bot ishga tushirish     catalog.py  bepul filmlar katalogi + archive.org
api.py       Mini App API                      db.py       SQLite
bot.py       aiogram bot va admin buyruqlari   static/     Mini App (index.html)
tests/       pytest                            scripts/    check_catalog.py
```

## Litsenziya
Kod: MIT ([LICENSE](LICENSE)). Filmlar o'z litsenziyalari bilan: [CATALOG.md](CATALOG.md).
