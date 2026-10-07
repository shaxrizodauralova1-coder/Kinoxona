import os, sys, tempfile

_tmp = tempfile.mkdtemp()
os.environ.update(DEV="1", DEMO_PAYMENTS="1", SEED_DEMO="1", BOT_TOKEN="", ADMIN_IDS="1",
                  WEBAPP_URL="", CHANNELS="", PROVIDER_TOKEN="", DB_PATH=os.path.join(_tmp, "test.db"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
