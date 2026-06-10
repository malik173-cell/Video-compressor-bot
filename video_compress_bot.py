import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CallbackQueryHandler,
    CommandHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ==========================================
BOT_TOKEN = "8665532440:AAGBG1_l74T0oTmYLCzuIdFy8SJKNV-wC8Q"
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

user_videos = {}
user_state = {}  # Track karo user kahan hai

# Resolution Options
RESOLUTION_OPTIONS = {
    "original": {"scale": None,        "label": "📺 Original Resolution"},
    "1080p":    {"scale": "1920:1080", "label": "🔵 1080p Full HD"},
    "720p":     {"scale": "1280:720",  "label": "🟢 720p HD"},
    "480p":     {"scale": "854:480",   "label": "🟡 480p SD"},
    "360p":     {"scale": "640:360",   "label": "🟠 360p Low"},
    "240p":     {"scale": "426:240",   "label": "🔴 240p Very Low"},
}

# CRF (Quality) Options
QUALITY_OPTIONS = {
    "best":   {"crf": "18", "label": "💎 Best Quality"},
    "good":   {"crf": "23", "label": "✅ Good Quality"},
    "normal": {"crf": "28", "label": "⚡ Normal Quality"},
    "small":  {"crf": "34", "label": "📦 Small Size"},
    "tiny":   {"crf": "40", "label": "🪄 Tiny Size"},
}


# ─── /start ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Welcome to Pro Video Compressor Bot!*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Features:*\n"
        "✅ Multiple Resolutions (240p → 1080p)\n"
        "✅ Custom Quality (Best → Tiny)\n"
        "✅ Fast Compression (FFmpeg)\n"
        "✅ Auto File Size Info\n"
        "✅ Multiple Users Support\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 *Shuru karne ke liye video bhejo!*",
        parse_mode=ParseMode.MARKDOWN
    )


# ─── /help ───────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help Guide*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ Bot ko video bhejo\n"
        "2️⃣ Resolution choose karo\n"
        "3️⃣ Quality choose karo\n"
        "4️⃣ Compressed video milegi!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📺 *Resolutions:*\n"
        "• Original — Koi change nahi\n"
        "• 1080p — Full HD\n"
        "• 720p — HD\n"
        "• 480p — Standard\n"
        "• 360p — Low\n"
        "• 240p — Very Low\n\n"
        "💎 *Quality (CRF):*\n"
        "• Best (18) — Sabse acha, bada size\n"
        "• Good (23) — Balanced\n"
        "• Normal (28) — Theek\n"
        "• Small (34) — Chhota\n"
        "• Tiny (40) — Bahut chhota\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN
    )


# ─── Video Receive ─────────────────────────────────────────
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    video = message.video or message.document

    if not video:
        await message.reply_text("❌ Sirf video files bhejo!")
        return

    file_size_mb = (video.file_size or 0) / (1024 * 1024)

    if file_size_mb > 1900:
        await message.reply_text("❌ File bahut badi hai! 1.9GB se chhoti video bhejo.")
        return

    user_videos[user_id] = {
        "file_id": video.file_id,
        "file_size": file_size_mb,
        "chat_id": message.chat_id,
        "resolution": None,
        "quality": None
    }

    # Step 1: Resolution choose karo
    keyboard = [
        [InlineKeyboardButton("📺 Original Resolution", callback_data=f"res_original_{user_id}")],
        [
            InlineKeyboardButton("🔵 1080p", callback_data=f"res_1080p_{user_id}"),
            InlineKeyboardButton("🟢 720p",  callback_data=f"res_720p_{user_id}"),
        ],
        [
            InlineKeyboardButton("🟡 480p",  callback_data=f"res_480p_{user_id}"),
            InlineKeyboardButton("🟠 360p",  callback_data=f"res_360p_{user_id}"),
            InlineKeyboardButton("🔴 240p",  callback_data=f"res_240p_{user_id}"),
        ],
    ]

    await message.reply_text(
        f"🎬 *Video Receive Ho Gayi!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 Size: `{file_size_mb:.1f} MB`\n\n"
        f"*Step 1️⃣: Resolution choose karo 👇*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


# ─── Resolution Callback ───────────────────────────────────
async def resolution_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    res_key = parts[1]
    user_id = int(parts[2])

    if user_id not in user_videos:
        await query.edit_message_text("❌ Session khatam! Dobara video bhejo.")
        return

    user_videos[user_id]["resolution"] = res_key
    res_label = RESOLUTION_OPTIONS[res_key]["label"]

    # Step 2: Quality choose karo
    keyboard = [
        [InlineKeyboardButton("💎 Best Quality",   callback_data=f"qual_best_{user_id}")],
        [InlineKeyboardButton("✅ Good Quality",   callback_data=f"qual_good_{user_id}")],
        [InlineKeyboardButton("⚡ Normal Quality", callback_data=f"qual_normal_{user_id}")],
        [InlineKeyboardButton("📦 Small Size",     callback_data=f"qual_small_{user_id}")],
        [InlineKeyboardButton("🪄 Tiny Size",      callback_data=f"qual_tiny_{user_id}")],
    ]

    await query.edit_message_text(
        f"✅ *Resolution:* {res_label}\n\n"
        f"*Step 2️⃣: Quality choose karo 👇*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


# ─── Quality Callback + Compress ──────────────────────────
async def quality_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    qual_key = parts[1]
    user_id = int(parts[2])

    if user_id not in user_videos:
        await query.edit_message_text("❌ Session khatam! Dobara video bhejo.")
        return

    user_videos[user_id]["quality"] = qual_key

    video_info = user_videos[user_id]
    res_key = video_info["resolution"]
    crf = QUALITY_OPTIONS[qual_key]["crf"]
    scale = RESOLUTION_OPTIONS[res_key]["scale"]
    res_label = RESOLUTION_OPTIONS[res_key]["label"]
    qual_label = QUALITY_OPTIONS[qual_key]["label"]

    await query.edit_message_text(
        f"⏳ *Compression shuru ho gayi...*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 Resolution: {res_label}\n"
        f"💎 Quality: {qual_label}\n\n"
        f"Thoda wait karo... ☕",
        parse_mode=ParseMode.MARKDOWN
    )

    input_path  = f"input_{user_id}.mp4"
    output_path = f"compressed_{user_id}.mp4"

    try:
        file = await context.bot.get_file(video_info["file_id"])
        await file.download_to_drive(input_path)
        original_size = os.path.getsize(input_path) / (1024 * 1024)

        # FFmpeg command build karo
        vf_filters = []
        if scale:
            vf_filters.append(f"scale={scale}:force_original_aspect_ratio=decrease")

        command = ["ffmpeg", "-i", input_path]
        if vf_filters:
            command += ["-vf", ",".join(vf_filters)]
        command += [
            "-vcodec", "libx264",
            "-crf", crf,
            "-preset", "veryfast",
            "-acodec", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-threads", "0",
            output_path, "-y"
        ]

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

        compressed_size = os.path.getsize(output_path) / (1024 * 1024)
        saved = original_size - compressed_size
        saved_pct = (saved / original_size * 100) if original_size > 0 else 0

        caption = (
            f"✅ *Compression Complete!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 Original:   `{original_size:.1f} MB`\n"
            f"✅ Compressed: `{compressed_size:.1f} MB`\n"
            f"💾 Saved:      `{saved:.1f} MB ({saved_pct:.0f}%)`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 Resolution: {res_label}\n"
            f"💎 Quality:    {qual_label}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 @YourBotUsername"
        )

        with open(output_path, "rb") as f:
            if compressed_size < 49:
                await context.bot.send_video(
                    chat_id=video_info["chat_id"],
                    video=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True
                )
            else:
                await context.bot.send_document(
                    chat_id=video_info["chat_id"],
                    document=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )

        await query.edit_message_text(
            f"✅ *Done! Video bhej di gayi!*\n"
            f"💾 `{original_size:.1f} MB → {compressed_size:.1f} MB ({saved_pct:.0f}% saved)`",
            parse_mode=ParseMode.MARKDOWN
        )

    except TelegramError as e:
        logging.error(f"Telegram error: {e}")
        await query.edit_message_text(f"❌ Telegram error: {str(e)}\nDobara try karo.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await query.edit_message_text("❌ Error aaya! Dobara video bhejo.")
    finally:
        if os.path.exists(input_path):  os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        user_videos.pop(user_id, None)


# ─── Main ─────────────────────────────────────────────────
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .connect_timeout(30)
        .read_timeout(300)
        .write_timeout(300)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(resolution_chosen, pattern=r"^res_"))
    app.add_handler(CallbackQueryHandler(quality_chosen,    pattern=r"^qual_"))

    print("✅ Pro Bot chal raha hai! 🚀")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
