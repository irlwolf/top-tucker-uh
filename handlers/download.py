import os
from telegram.constants import ChatAction
from database.models import Session, FileCache
from utils.converter import convert_to_24bit
from mutagen.flac import FLAC, Picture
import asyncio

async def download_handler(update, context):
    query = update.callback_query
    track_id = query.data.split("_")[1] # e.g., "dl_12345"
    await query.answer()

    session = Session()
    # 1. DATABASE CHECK (Caching)
    cached_file = session.query(FileCache).filter_by(track_id=track_id).first()
    
    if cached_file:
        await query.message.reply_text("⚡ Fast-loading from cache...")
        await context.bot.send_audio(
            chat_id=query.message.chat_id,
            audio=cached_file.file_id, # Instant send using Telegram's ID
            caption="✅ Quality: 24-bit (Cached)"
        )
        session.close()
        return

    # 2. NEW DOWNLOAD LOGIC
    await query.edit_message_text("📥 Downloading Studio Master (24-bit)...")
    await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.UPLOAD_VOICE)

    # Placeholder: Use your qobuz-dl or tidal-dl logic here
    # raw_file = await your_music_api.download(track_id)
    raw_file = "downloads/temp_track.flac" 

    # 3. TAGGING (Mutagen)
    audio = FLAC(raw_file)
    audio["title"] = "Track Title"
    audio["artist"] = "Artist Name"
    audio["comment"] = "Downloaded via HiFiAudioBot"
    audio.save()

    # 4. SEND & SAVE TO DB
    sent_msg = await context.bot.send_audio(
        chat_id=query.message.chat_id,
        audio=open(raw_file, 'rb'),
        title="Track Title",
        performer="Artist Name",
        caption="✅ Quality: 24-bit / 96kHz"
    )

    # Save the new file_id to the database for next time
    new_cache = FileCache(track_id=track_id, file_id=sent_msg.audio.file_id, quality="24bit")
    session.add(new_cache)
    session.commit()
    session.close()

    # Cleanup local file to save server space
    if os.path.exists(raw_file):
        os.remove(raw_file)
