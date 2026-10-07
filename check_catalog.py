"""Katalogdagi har bir film uchun archive.org dan MP4 havola topiladimi va ochiladimi, tekshiradi.

Ishga tushirish (internet kerak):  python scripts/check_catalog.py
"""
import asyncio, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aiohttp
import catalog


async def main():
    bad = 0
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
        for f in catalog.FILMS:
            url = await catalog.resolve(f["ia"])
            if not url:
                print(f"XATO   {f['title']}: MP4 topilmadi ({f['ia']})")
                bad += 1
                continue
            try:
                async with s.get(url, headers={"Range": "bytes=0-1023"}) as r:
                    ok = r.status in (200, 206)
                    print(f"{'OK    ' if ok else 'XATO  '} {f['title']}: HTTP {r.status} {url}")
                    bad += not ok
            except Exception as e:
                print(f"XATO   {f['title']}: {e}")
                bad += 1
    sys.exit(1 if bad else 0)


asyncio.run(main())
