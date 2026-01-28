from telegram.constants import ChatAction
from utils.search_api import get_hifi_results

async def search_handler(update, context):
    query = update.message.text
    # Instant Animation
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Non-blocking async search
    results = await get_hifi_results(query) 
    
    # Build complex keyboard with Pagination
    keyboard = build_paginated_keyboard(results, page=1)
    await update.message.reply_text(f"Found {len(results)} Master Tracks:", reply_markup=keyboard)
