import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
QOBUZ_TOKEN = os.getenv("QOBUZ_TOKEN")
# Local API is required for 24-bit files over 50MB
BASE_URL = os.getenv("LOCAL_API_URL", "https://api.telegram.org/bot")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
DOWNLOAD_PATH = "downloads"
DB_URL = "sqlite:///hifi_bot.db"
