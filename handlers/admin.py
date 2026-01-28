from database.models import Session, FileCache
from config import ADMIN_ID

async def stats_handler(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    session = Session()
    total_cached = session.query(FileCache).count()
    session.close()

    await update.message.reply_text(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"Total Hi-Res Tracks Cached: {total_cached}\n"
        f"Server Status: Online ✅",
        parse_mode="HTML"
    )
