import asyncio, logging, os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
import db, api
import bot as tb

logging.basicConfig(level=logging.INFO)
BASE = os.path.dirname(os.path.abspath(__file__))


@asynccontextmanager
async def life(app):
    await db.init()
    await db.seed()
    task = asyncio.create_task(tb.run())
    yield
    task.cancel()
    if tb.bot:
        await tb.bot.session.close()
    await db.close()


app = FastAPI(lifespan=life, docs_url=None, redoc_url=None)
app.include_router(api.r)


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE, "static", "index.html"), headers={"Cache-Control": "no-cache"})


@app.get("/health")
async def health():
    return {"ok": True}
