import os
import sys
import time
import threading
import logging
from flask import Flask, request
import telebot
from telebot.apihelper import ApiTelegramException
import pandas as pd
import atexit
import tempfile
import fcntl

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# === TELEGRAM BOT SETUP ===
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ BOT_TOKEN not found in environment variables")
    sys.exit(1)
    
bot = telebot.TeleBot(TOKEN)

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

@app.route('/health')
def health_check():
    return "✅ OK", 200

def keep_alive():
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)).start()

# === LOAD EXCEL ===
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"
try:
    df = pd.read_excel(EXCEL_FILE)
    df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
    logging.info("✅ Excel loaded successfully")
except FileNotFoundError:
    logging.error("❌ Excel file not found. Make sure it's in the same folder.")
    df = pd.DataFrame()
except Exception as e:
    logging.error(f"❌ Error loading Excel: {e}")
    df = pd.DataFrame()

# === IMPROVED INSTANCE LOCK MECHANISM ===
def acquire_instance_lock():
    """Create a lock file to ensure only one instance runs"""
    lock_file = os.path.join(tempfile.gettempdir(), f"delima_bot_{hash(TOKEN)}.lock")
    
    try:
        # Try to create and lock the file exclusively
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write the current process ID to the lock file
            os.write(fd, f"{os.getpid()}".encode())
            return True
            
        except (IOError, BlockingIOError):
            # Lock failed, another instance is running
            os.close(fd)
            return False
            
    except OSError as e:
        logging.error(f"❌ Lock file error: {e}")
        return False

def release_instance_lock():
    """Remove the lock file when the bot stops"""
    lock_file = os.path.join(tempfile.gettempdir(), f"delima_bot_{hash(TOKEN)}.lock")
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except Exception as e:
        logging.error(f"❌ Error releasing lock: {e}")

# Register cleanup function
atexit.register(release_instance_lock)

# === HANDLERS (ORIGINAL TAK USIK) ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "👋 Selamat datang ke sistem bantuan *DELIMa KPM*.\n\n"
        "Sila isi *nama penuh murid* dan hantar.\n"
        "⚠️ Pastikan tiada kesalahan ejaan pada nama.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📌 *Senarai arahan tersedia:*\n\n"
        "🚀 /start - Mula gunakan bot\n"
        "📌 /help - Lihat senarai arahan\n"
        "🌐 /delima - Akses laman rasmi DELIMa KPM\n"
        "📖 /ains - Akses sistem NILAM (AINS)\n"
        "🔑 /resetpassword - Panduan reset kata laluan DELIMa\n"
        "📊 /status - Status server & rekod\n\n"
        "✍️ Untuk semakan, sila hantar *nama penuh murid*."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['delima'])
def send_delima_link(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 Buka DELIMa", url="https://d2.delima.edu.my/"))
    bot.reply_to(message, "🌐 Akses laman rasmi DELIMa KPM di pautan berikut:", reply_markup=markup)

@bot.message_handler(commands=['ains'])
def send_ains_link(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📖 Buka AINS", url="https://ains.moe.gov.my/login?returnUrl=/"))
    bot.reply_to(
        message,
        "📖 Akses *Advanced Integrated NILAM System (AINS)* di pautan berikut:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['resetpassword'])
def send_reset_password(message):
    reply_text = (
        "🔑 *Peringatan Reset Kata Laluan DELIMa KPM*\n\n"
        "Untuk menetapkan semula kata laluan, sila hubungi *guru kelas anak anda* "
        "untuk mendapatkan bantuan rasmi.\n\n"
        "📂 Pihak sekolah menasihatkan agar ibu bapa / penjaga menyimpan kata laluan dengan baik "
        "supaya tidak menghadapi masalah akses pada masa hadapan."
    )
    bot.reply_to(message, reply_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def send_status(message):
    total_records = len(df) if not df.empty else 0
    uptime_seconds = int(time.time() - START_TIME)

    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_parts = []
    if days > 0:
        uptime_parts.append(f"{days} hari")
    if hours > 0:
        uptime_parts.append(f"{hours} jam")
    if minutes > 0:
        uptime_parts.append(f"{minutes} minit")
    if seconds > 0:
        uptime_parts.append(f"{seconds} saat")

    uptime_text = " ".join(uptime_parts)

    reply_text = (
        "📊 *Status Server & Bot*\n\n"
        f"🚀 Bot sedang berjalan\n"
        f"👥 Jumlah rekod orang: {total_records}\n"
        f"⏳ Server aktif: {uptime_text}\n\n"
        "🌍 Source code: Github\n"
        "💻 Server: Render\n"
        "📡 Status monitor: UpTimeRobot\n"
        "📊 Status page: https://stats.uptimerobot.com/k6aooeDaUq"
    )
    bot.reply_to(message, reply_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def send_info(message):
    try:
        search_name = message.text.strip().upper()
        if "PASSWORD" in search_name or "KATA LALUAN" in search_name:
            bot.reply_to(
                message,
                "🔑 Untuk isu kata laluan, sila hubungi *guru kelas anak anda* bagi bantuan reset.\n\n"
                "📂 Pihak sekolah mengingatkan agar kata laluan sentiasa disimpan dengan baik.",
                parse_mode="Markdown"
            )
            return

        if df.empty:
            bot.reply_to(message, "❌ Data tidak tersedia sekarang.")
            return

        matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]
        if matches.empty:
            bot.reply_to(message, "⚠️ Maaf, nama tidak dijumpai dalam rekod.")
        else:
            row = matches.iloc[0]
            reply_text = (
                f"👤 Nama Murid: {row['Nama Murid']}\n"
                f"📧 Email: {row.iloc[1]}\n"
                f"🔑 Password: {row.iloc[2]}"
            )
            bot.reply_to(message, reply_text)
    except Exception as e:
        logging.error(f"Error in send_info handler: {e}")
        bot.reply_to(message, "⚠️ Maaf, berlaku ralat dalam sistem.")

# === OPTIMIZED POLLING CYCLE (15s ON, 60s SLEEP) ===
def polling_cycle():
    # Check if another instance is already running
    if not acquire_instance_lock():
        logging.error("❌ Another instance of the bot is already running. Exiting...")
        logging.error("💥 Telegram API error: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running.")
        sys.exit(1)
    
    logging.info("✅ Acquired instance lock, starting bot...")
    
    # Counter untuk avoid infinite error loop
    error_count = 0
    max_errors = 5
    
    while True:
        try:
            logging.info("🚀 Starting polling (15-second active cycle)...")
            
            # Stop any existing polling first
            try:
                bot.stop_polling()
            except:
                pass
            
            # Start polling with timeout 15 seconds
            bot.polling(none_stop=True, skip_pending=True, timeout=15, interval=1)
            
            # Reset error count on success
            error_count = 0
            
            # After 15 seconds, stop polling and sleep
            logging.info("⏸️  Polling cycle completed, entering 60-second sleep mode...")
            time.sleep(60)
            
        except ApiTelegramException as e:
            error_count += 1
            if "409" in str(e):
                logging.error(f"💥 Telegram API error: 409 Conflict. Entering 60s sleep... (Error count: {error_count})")
            else:
                logging.error(f"💥 Telegram API error: {e}. Entering 60s sleep... (Error count: {error_count})")
            
            if error_count >= max_errors:
                logging.error("🛑 Too many errors, exiting to avoid infinite loop...")
                sys.exit(1)
                
            time.sleep(60)
            
        except Exception as e:
            error_count += 1
            logging.error(f"💥 Bot crash/error: {e}. Entering 60s sleep... (Error count: {error_count})")
            
            if error_count >= max_errors:
                logging.error("🛑 Too many errors, exiting to avoid infinite loop...")
                sys.exit(1)
                
            time.sleep(60)

# === MAIN START ===
if __name__ == "__main__":
    START_TIME = time.time()
    
    # Start Flask in background
    keep_alive()
    
    # Allow Flask to start first
    time.sleep(2)
    
    # Start polling cycle
    polling_cycle()
