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

# === FLASK SETUP UNTUK RENDER ===
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

# === RENDER-COMPATIBLE INSTANCE LOCK ===
def acquire_instance_lock():
    """Lock mechanism yang compatible dengan Render"""
    lock_file = "/tmp/delima_bot_render.lock"
    
    try:
        # Try to create and lock the file
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
        try:
            # Try to acquire exclusive lock
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write process info
            os.write(fd, f"{os.getpid()},{time.time()}".encode())
            os.close(fd)
            return True
            
        except (IOError, BlockingIOError):
            os.close(fd)
            # Check if lock file is stale (older than 1 minute)
            try:
                with open(lock_file, 'r') as f:
                    data = f.read().split(',')
                    if len(data) == 2:
                        pid, timestamp = data
                        if time.time() - float(timestamp) > 60:  # 1 minute
                            os.remove(lock_file)
                            return acquire_instance_lock()
            except:
                pass
            return False
            
    except OSError as e:
        logging.error(f"❌ Lock file error: {e}")
        return False

def release_instance_lock():
    """Remove the lock file when the bot stops"""
    lock_file = "/tmp/delima_bot_render.lock"
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logging.info("🔓 Instance lock released")
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

# === RENDER-OPTIMIZED POLLING CYCLE ===
def polling_cycle():
    # Wait untuk pastikan previous instance completely shutdown
    logging.info("⏳ Waiting for previous instance to shutdown...")
    time.sleep(10)
    
    # Check instance lock dengan strict validation
    if not acquire_instance_lock():
        logging.error("❌ Multiple instance detected. EXITING IMMEDIATELY.")
        logging.error("💥 Telegram API error: A request to the Telegram API was unsuccessful. Error code: 409. Description: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running.")
        sys.exit(1)
    
    logging.info("✅ Acquired instance lock, starting bot...")
    
    error_count = 0
    max_errors = 2  # Lower threshold untuk Render
    
    while error_count < max_errors:
        try:
            # Stop any existing polling first
            try:
                bot.stop_polling()
                time.sleep(3)
            except:
                pass
            
            logging.info("🚀 Starting polling (15-second active cycle)...")
            
            # Start polling dengan timeout
            bot.polling(none_stop=True, skip_pending=True, timeout=15, interval=1)
            
            # Successful polling
            logging.info("⏸️  Polling completed, entering 60s sleep...")
            time.sleep(60)
            error_count = 0  # Reset error count
            
        except ApiTelegramException as e:
            error_count += 1
            if "409" in str(e):
                logging.error(f"💥 API Error 409. Sleep 60s... (Error {error_count}/{max_errors})")
                if error_count >= max_errors:
                    logging.error("🛑 Max errors reached. Exiting gracefully...")
                    break
                time.sleep(60)
            else:
                logging.error(f"💥 Other API error: {e}")
                time.sleep(30)
                
        except Exception as e:
            error_count += 1
            logging.error(f"💥 General error: {e}. Sleep 30s... (Error {error_count}/{max_errors})")
            if error_count >= max_errors:
                logging.error("🛑 Max errors reached. Exiting gracefully...")
                break
            time.sleep(30)
    
    # Clean exit untuk allow Render restart properly
    logging.info("🔄 Shutting down gracefully for Render restart...")
    release_instance_lock()
    time.sleep(3)
    sys.exit(0)

# === MAIN FUNCTION ===
if __name__ == "__main__":
    START_TIME = time.time()
    
    # Start Flask dalam thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Wait untuk Flask start sepenuhnya
    logging.info("⏳ Waiting for Flask to start...")
    time.sleep(15)
    
    # Start polling cycle
    polling_cycle()
