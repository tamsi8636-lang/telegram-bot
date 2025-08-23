import os
import sys
import time
import threading
import logging
from flask import Flask
import telebot
from telebot.apihelper import ApiTelegramException
import pandas as pd
import atexit
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

# === FLASK SETUP ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

@app.route('/health')
def health_check():
    return "✅ OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"🚀 Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

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

# === INSTANCE LOCK ===
LOCK_FILE = "/tmp/delima_bot_render.lock"

def acquire_instance_lock():
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(fd, f"{os.getpid()},{time.time()}".encode())
            os.close(fd)
            logging.info("🔒 Instance lock acquired")
            return True
        except (IOError, BlockingIOError):
            os.close(fd)
            logging.error("⚠️ Another instance is running. Exiting.")
            return False
    except OSError as e:
        logging.error(f"❌ Lock file error: {e}")
        return False

def release_instance_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logging.info("🔓 Instance lock released")
    except Exception as e:
        logging.error(f"❌ Error releasing lock: {e}")

atexit.register(release_instance_lock)

# === HANDLERS (ASAL TAK USIK) ===
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

# === CONTINUOUS POLLING DENGAN “SELANG SELI” HEARTBEAT ===
def polling_with_sleep():
    if not acquire_instance_lock():
        logging.error("⚠️ Cannot acquire lock. Exiting.")
        sys.exit(1)

    try:
        logging.info("🚀 Starting continuous polling with sleep simulation")

        while True:
            try:
                # Polling continuous dengan timeout 5s
                bot.polling(none_stop=True, skip_pending=True, timeout=5)
            except ApiTelegramException as e:
                logging.error(f"💥 Telegram API error: {e}. Sleeping 5s before retry...")
                time.sleep(5)
            except Exception as e:
                logging.error(f"💥 General error: {e}. Sleeping 5s before retry...")
                time.sleep(5)

    finally:
        release_instance_lock()

# === HEARTBEAT LOG THREAD (CPU rendah) ===
def heartbeat_log():
    while True:
        logging.info("💓 Bot heartbeat - polling active...")
        time.sleep(10)  # adjustable interval untuk log saja, CPU rendah

# === MAIN FUNCTION ===
if __name__ == "__main__":
    START_TIME = time.time()
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Heartbeat log thread
    heartbeat_thread = threading.Thread(target=heartbeat_log, daemon=True)
    heartbeat_thread.start()
    
    logging.info("⏳ Waiting 10s for Flask to be ready...")
    time.sleep(10)
    
    # Start polling continuous
    polling_with_sleep()
