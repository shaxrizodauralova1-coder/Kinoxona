"""Namunaviy kontent katalogi: faqat qonuniy BEPUL filmlar.

Nima kiritilgan:
  - Blender Foundation ochiq filmlari (Creative Commons Attribution, tijorat uchun ham ruxsat, muallif ko'rsatilsa).
  - Mualliflik muddati tugagan (public domain) klassik filmlar.

Videolar Internet Archive (archive.org) dan to'g'ridan-to'g'ri MP4 sifatida beriladi.
Aniq fayl nomi qo'lda yozilmaydi: ijro paytida archive.org metadata API orqali eng mos
H.264 MP4 topiladi va bazaga saqlanadi. Shu sababli havola o'zgarsa ham katalog buzilmaydi.

Litsenziya tafsilotlari: CATALOG.md
"""
import logging
from urllib.parse import quote

import aiohttp

import db

log = logging.getLogger("catalog")
IA = "https://archive.org"

# Format ustuvorligi: kichik raqam yaxshiroq. Hammasi brauzerda ochiladigan H.264 MP4.
PRIORITY = {"h.264": 0, "h.264 ia": 1, "mpeg4": 2, "512kb mpeg4": 3}
MAX_BYTES = 700 * 1024 * 1024  # mobil internet uchun juda katta fayllarni chetlab o'tamiz

STUDIOS = [
    ("blender", "Blender Studio",
     "Blender Foundation ochiq animatsiya va VFX filmlari. Creative Commons Attribution litsenziyasi."),
    ("klassika", "Jahon klassikasi",
     "Mualliflik muddati tugagan klassik filmlar: Meliyes, Murnau."),
]

# lvl: 0 bepul, 1 Standart, 2 Premium (demo uchun aralash; /setlevel bilan o'zgartiriladi)
# ia: "identifier" yoki "identifier|fayl nomidan parcha"
FILMS = [
    dict(title="Elephants Dream", cat="Multfilm", year=2006, minutes=11, studio="blender", lvl=0,
         ia="Sintel_201709|Elephants Dream", poster=None,
         descr="Emo va Proog ismli ikki g'alati personaj ulkan mexanik olamni kashf qiladi. "
               "Blenderda yaratilgan birinchi ochiq film.\n\nLitsenziya: CC BY 2.5, © Blender Foundation | orange.blender.org"),
    dict(title="Big Buck Bunny", cat="Multfilm", year=2008, minutes=10, studio="blender", lvl=0,
         ia="BigBuckBunny_328", poster=f"{IA}/services/img/BigBuckBunny_328",
         descr="Mehribon yirik quyon o'zini bezovta qilgan uchta kemiruvchidan kulgili tarzda o'ch oladi.\n\n"
               "Litsenziya: CC BY 3.0, © Blender Foundation | peach.blender.org"),
    dict(title="Sintel", cat="Multfilm", year=2010, minutes=15, studio="blender", lvl=1,
         ia="Sintel", poster=f"{IA}/services/img/Sintel",
         descr="Yolg'iz jangchi qiz o'zining yosh ajdarhosini izlab uzoq va xavfli safarga chiqadi.\n\n"
               "Litsenziya: CC BY 3.0, © Blender Foundation | durian.blender.org"),
    dict(title="Cosmos Laundromat", cat="Multfilm", year=2015, minutes=12, studio="blender", lvl=2,
         ia="Sintel_201709|Cosmos Laundromat", poster=None,
         descr="Hayotdan charchagan qo'y Frank'ga sirli sotuvchi turli hayotlarni taklif qiladi.\n\n"
               "Litsenziya: Creative Commons Attribution (CC BY), © Blender Foundation | gooseberry.blender.org"),
    dict(title="Oyga sayohat", cat="Kino", year=1902, minutes=14, studio="klassika", lvl=0,
         ia="le-voyage-dans-la-lune-1902-georges-melies", poster=f"{IA}/services/img/le-voyage-dans-la-lune-1902-georges-melies",
         descr="Jorj Meliyesning mashhur ilmiy-fantastik filmi (A Trip to the Moon): olimlar Oyga to'pdan otilib uchadi. "
               "Jahon kinosining eng birinchi fantastikalaridan biri.\n\nLitsenziya: public domain"),
    dict(title="Nosferatu", cat="Kino", year=1922, minutes=93, studio="klassika", lvl=2,
         ia="PhantasmagoriaTheater-Nosferatu1922909", poster=f"{IA}/services/img/PhantasmagoriaTheater-Nosferatu1922909",
         descr="F. V. Murnauning jim kino davridagi klassik dahshat filmi: graf Orlok va Vizborg shahri qissasi.\n\n"
               "Litsenziya: public domain"),
    dict(title="Tears of Steel", cat="Kino", year=2012, minutes=12, studio="blender", lvl=1,
         ia="Sintel_201709|Tears of Steel", poster=None,
         descr="Amsterdamda yaqin kelajak: jangchilar guruhi robotlarga qarshi oxirgi urinishga chiqadi. "
               "Jonli aktyorlar va kompyuter grafikasi aralash ilmiy-fantastik film.\n\n"
               "Litsenziya: CC BY 3.0, © Blender Foundation | mango.blender.org"),
]


def pick(files, hint=""):
    """archive.org fayllar ro'yxatidan eng mos MP4 nomini tanlaydi (yoki None)."""
    hint = hint.lower()

    def cands(strict):
        out = []
        for f in files:
            n = f.get("name", "")
            if not n.lower().endswith(".mp4") or "/" in n:
                continue
            if hint and hint not in n.lower():
                continue
            fmt = (f.get("format") or "").lower()
            if strict and fmt not in PRIORITY:
                continue
            try:
                size = int(f.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            out.append((PRIORITY.get(fmt, 9), size, n))
        return out

    c = cands(True) or cands(False)
    if not c:
        return None
    small = [x for x in c if 0 < x[1] <= MAX_BYTES] or c
    best = min(x[0] for x in small)
    # eng yaxshi formatlar ichida eng kattasi (ya'ni eng yuqori sifat, lekin MAX_BYTES gacha)
    return max((x for x in small if x[0] == best), key=lambda x: x[1])[2]


async def resolve(ia: str):
    """'identifier|hint' -> to'g'ridan-to'g'ri MP4 havola yoki None."""
    ident, _, hint = ia.partition("|")
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.get(f"{IA}/metadata/{quote(ident)}") as r:
                if r.status != 200:
                    log.warning("archive.org %s: HTTP %s", ident, r.status)
                    return None
                data = await r.json(content_type=None)
    except Exception as e:
        log.warning("archive.org %s: %s", ident, e)
        return None
    name = pick(data.get("files", []), hint)
    if not name:
        log.warning("archive.org %s: mos MP4 topilmadi", ident)
        return None
    return f"{IA}/download/{quote(ident)}/{quote(name)}"


async def import_free():
    """Bepul katalogni bazaga qo'shadi. Takroran chaqirsa, mavjudlarini o'tkazib yuboradi."""
    for sid, name, about in STUDIOS:
        await db.x("INSERT OR IGNORE INTO studios VALUES(?,?,?,?)", (sid, name, about, db.hue(name)))
    added = 0
    for i, f in enumerate(FILMS):
        if await db.one("SELECT 1 FROM movies WHERE ia=?", (f["ia"],)):
            continue
        code = await db.next_code()
        await db.x(
            "INSERT INTO movies(code,title,cat,year,minutes,descr,hue,studio,lvl,poster_url,ia,pub,created) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?)",
            (code, f["title"], f["cat"], f["year"], f["minutes"], f["descr"], db.hue(f["title"]),
             f["studio"], f["lvl"], f["poster"], f["ia"], db.now() + i))
        added += 1
    return added
