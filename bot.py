import logging
import os  # Penting untuk mengambil token dari server
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Ambil token dari Environment Variable
# Kita akan atur ini di Railway, bukan di dalam kode
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Setup logging dasar
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fungsi untuk membuat tombol menu utama
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("Cari Partner 🚀", callback_data="find_partner")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Fungsi untuk /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Inisialisasi 'queue' dan 'chatting' di bot_data jika belum ada
    context.bot_data.setdefault('queue', [])
    context.bot_data.setdefault('chatting', {})

    # Jika pengguna sedang chat, beritahu dia
    if user_id in context.bot_data['chatting']:
        await update.message.reply_text("Anda sedang dalam obrolan! Ketik /stop untuk berhenti.")
        return

    # Jika pengguna ada di antrian, hapus dulu
    if user_id in context.bot_data['queue']:
        context.bot_data['queue'].remove(user_id)

    await update.message.reply_text(
        "Selamat datang di Bot Anon Chat!\n\n"
        "Klik tombol di bawah untuk mencari teman ngobrol baru.",
        reply_markup=get_main_keyboard()
    )

# Fungsi saat tombol "Cari Partner" ditekan
async def find_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Memberitahu Telegram bahwa tombol sudah diproses
    user_id = query.effective_user.id

    # Inisialisasi jika belum ada (safety check)
    context.bot_data.setdefault('queue', [])
    context.bot_data.setdefault('chatting', {})

    # Cek jika sudah chat
    if user_id in context.bot_data['chatting']:
        await query.edit_message_text("Anda sudah terhubung! Ketik /stop untuk mengakhiri.")
        return

    # Cek jika sudah di antrian
    if user_id in context.bot_data['queue']:
        await query.edit_message_text("Sedang mencari... Mohon tunggu. ⏳")
        return

    # Cek jika ada orang di antrian
    if context.bot_data['queue']:
        # Ambil partner dari antrian (orang pertama yang masuk)
        partner_id = context.bot_data['queue'].pop(0)

        # Pasangkan mereka
        context.bot_data['chatting'][user_id] = partner_id
        context.bot_data['chatting'][partner_id] = user_id

        # Beritahu kedua pengguna
        await query.edit_message_text("Partner ditemukan! Anda terhubung. Selamat mengobrol!\n\nKetik /stop untuk mengakhiri.")
        await context.bot.send_message(
            chat_id=partner_id,
            text="Partner ditemukan! Anda terhubung. Selamat mengobrol!\n\nKetik /stop untuk mengakhiri."
        )
    else:
        # Masukkan ke antrian
        context.bot_data['queue'].append(user_id)
        await query.edit_message_text("Sedang mencari partner... Mohon tunggu. ⏳")

# Fungsi untuk /stop
async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    context.bot_data.setdefault('chatting', {})

    if user_id not in context.bot_data['chatting']:
        await update.message.reply_text("Anda sedang tidak dalam obrolan.", reply_markup=get_main_keyboard())
        return

    # Dapatkan ID partner
    partner_id = context.bot_data['chatting'][user_id]

    # Hapus pasangan dari data 'chatting'
    del context.bot_data['chatting'][user_id]
    if partner_id in context.bot_data['chatting']:
        del context.bot_data['chatting'][partner_id]

    # Beritahu kedua pengguna
    await update.message.reply_text("Anda telah mengakhiri obrolan.", reply_markup=get_main_keyboard())
    await context.bot.send_message(
        chat_id=partner_id,
        text="Partner Anda telah mengakhiri obrolan.",
        reply_markup=get_main_keyboard()
    )

# Fungsi untuk menangani semua pesan chat (teks, stiker, foto, dll)
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    context.bot_data.setdefault('chatting', {})

    if user_id in context.bot_data['chatting']:
        partner_id = context.bot_data['chatting'][user_id]
        
        # Meneruskan pesan menggunakan copy_message agar tetap anonim
        # Ini akan menangani teks, stiker, foto, video, dll.
        await context.bot.copy_message(
            chat_id=partner_id,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )
    else:
        await update.message.reply_text("Anda sedang tidak dalam obrolan.", reply_markup=get_main_keyboard())

# Fungsi 'main' untuk menjalankan bot
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN tidak ditemukan! Harap atur di environment variable.")
        return

    logger.info("Memulai bot...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Tambahkan command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop_chat))

    # Tambahkan callback query handler (untuk tombol)
    application.add_handler(CallbackQueryHandler(find_partner, pattern="^find_partner$"))

    # Tambahkan message handler (untuk chat)
    # Ini akan menangani semua pesan non-perintah
    application.add_handler(MessageHandler(filters.COMMAND, start)) # Tangani jika user ketik /start saat chat
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_chat))

    logger.info("Bot sedang berjalan...")
    # Mulai bot
    application.run_polling()

if __name__ == "__main__":
    main()