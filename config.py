import os
from dotenv import load_dotenv
load_dotenv()
def env(k, d=""): return os.getenv(k, d).strip()
BOT_TOKEN = env("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in env("ADMIN_IDS").replace(" ", "").split(",") if x}
WEBAPP_URL = env("WEBAPP_URL").rstrip("/")
CHANNELS = [c.strip() for c in env("CHANNELS").split(",") if c.strip()]
PROVIDER_TOKEN = env("PROVIDER_TOKEN")
DEMO_PAYMENTS = env("DEMO_PAYMENTS") == "1"   # faqat test uchun! Productionda 0
DEV = env("DEV") == "1"                       # faqat lokal test uchun! Productionda 0
SEED_DEMO = env("SEED_DEMO") == "1"
DB_PATH = env("DB_PATH", "data/kinoxona.db")
PLANS = {"standard": {"name": "Standart", "price": 12000, "rank": 1},
         "premium": {"name": "Premium", "price": 30000, "rank": 2}}
DAYS = 30
CATS = ["Kino", "Multfilm", "Serial", "Shaxsiy ijod"]
