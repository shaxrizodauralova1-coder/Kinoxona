# Namunaviy kontent: manbalar va litsenziyalar

Loyiha bilan birga kelgan filmlar faqat **qonuniy bepul** manbalardan. Pirat filmlar kiritilmagan.
Videolar Internet Archive (archive.org) orqali beriladi, havola ijroda avtomatik topiladi (`catalog.py`).

| Kod | Film | Yil | Litsenziya | Eslatma |
|---|---|---|---|---|
| 1001 | Elephants Dream | 2006 | CC BY 2.5, Blender Foundation | orange.blender.org |
| 1002 | Big Buck Bunny | 2008 | CC BY 3.0, Blender Foundation | peach.blender.org |
| 1003 | Sintel | 2010 | CC BY 3.0, Blender Foundation | durian.blender.org |
| 1004 | Cosmos Laundromat | 2015 | CC BY, Blender Foundation | gooseberry.blender.org |
| 1005 | Oyga sayohat (A Trip to the Moon) | 1902 | Public domain | Georges Méliès |
| 1006 | Nosferatu | 1922 | Public domain | F. W. Murnau |
| 1007 | Tears of Steel | 2012 | CC BY 3.0, Blender Foundation | mango.blender.org |

## Muhim qoidalar
- **CC BY**: tijorat uchun ham mumkin, lekin muallifni ko'rsatish shart (bu loyihada tavsif matnida ko'rsatilgan, o'chirmang).
  Filmni qayta tarqatganda krediti (credits) saqlanishi kerak.
- **Public domain**: filmning o'zi erkin, lekin archive.org dagi ayrim nusxalarda keyin qo'shilgan musiqa yoki restavratsiya
  alohida mualliflik huquqiga ega bo'lishi mumkin. Pullik (production) ishlatishdan oldin tanlagan nusxangizni tekshiring.
- Qaysi film qaysi nusxadan olinishi `catalog.py` dagi `ia` maydonida. Boshqa nusxaga o'tish uchun identifikatorni almashtiring.
- O'zbekistonda mualliflik huquqi odatda muallif vafotidan 70 yil. Shuning uchun masalan Chaplin filmlari (AQShda public domain,
  lekin bu yerda himoyalangan) ataylab kiritilmadi. O'z kontentingizni qo'shishdan oldin huquqlarini tekshiring.
- Havolalar ishlashini tekshirish: `python scripts/check_catalog.py` (internet kerak).

## O'z kontentingizni qo'shish
Admin sifatida botda `/addstudio` va `/addmovie` (README ga qarang). Bepul katalogni keyinroq qo'shish: `/importfree`.
Darajani o'zgartirish: `/setlevel KOD 0|1|2`.
