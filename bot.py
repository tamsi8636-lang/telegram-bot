import os
import sys
import time
import threading
import logging
from flask import Flask
import telebot
from telebot.apihelper import ApiTelegramException
import pandas as pd

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# === TELEGRAM BOT SETUP ===
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"

def keep_alive():
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

# === LOGGING UTIL ===
def log_command(message, cmd_name):
    user = message.from_user.username or "UnknownUser"
    user_id = message.from_user.id
    logging.info(f"📩 Command {cmd_name} diterima dari {user} (id={user_id})")

def log_message(message):
    user = message.from_user.username or "UnknownUser"
    user_id = message.from_user.id
    logging.info(f"💬 Mesej biasa dari {user} (id={user_id}): {message.text}")

# === LOAD EXCEL ===
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"
try:
    df = pd.read_excel(EXCEL_FILE)
    df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
    logging.info("✅ Excel loaded successfully")
except FileNotFoundError:
    logging.error("❌ Excel file not found. Make sure it's in the same folder.")
    df = pd.DataFrame()

# === HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    log_command(message, "/start")
    bot.reply_to(
        message,
        "👋 Selamat datang ke sistem bantuan *DELIMa KPM*.\n\n"
        "Sila isi *nama penuh murid* dan hantar.\n"
        "⚠️ Pastikan tiada kesalahan ejaan pada nama.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    log_command(message, "/help")
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
    log_command(message, "/delima")
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 Buka DELIMa", url="https://d2.delima.edu.my/"))
    bot.reply_to(message, "🌐 Akses laman rasmi DELIMa KPM di pautan berikut:", reply_markup=markup)

@bot.message_handler(commands=['ains'])
def send_ains_link(message):
    log_command(message, "/ains")
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
    log_command(message, "/resetpassword")
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
    log_command(message, "/status")
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
    log_message(message)
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

# === POLLING SELANG 15 SAAT ON / 1 MIN OFF (SAFE) ===
def polling_cycle():
    while True:
        try:
            logging.info("🚀 Polling bot ON selama 15 saat...")
            try:
                bot.polling(timeout=15, long_polling_timeout=15, skip_pending=True, none_stop=True)
            except ApiTelegramException as e:
                if "409" in str(e):
                    logging.error(f"💥 Telegram API error 409 (Conflict): {e}. Stop polling dan restart...")
                    bot.stop_polling()
                    time.sleep(20)
                else:
                    logging.error(f"💥 Telegram API error: {e}. Restarting...")
                    os.execv(sys.executable, ['python'] + sys.argv)
            except Exception as e:
                logging.error(f"💥 Bot crash/disconnect/error: {e}. Restarting...")
                os.execv(sys.executable, ['python'] + sys.argv)
        finally:
            logging.info("⏸ Polling bot OFF selama 1 minit...")
            bot.stop_polling()
            time.sleep(60)

# === SELF-CHECK 2X SEHARI ===
def self_check():
    while True:
        for _ in range(2):  # dua kali sehari
            time.sleep(43200)  # 12 jam
            try:
                bot.get_me()
                logging.info("✅ Self-check: Bot responsive.")
            except Exception as e:
                logging.error(f"💥 Self-check detect bot hang: {e}. Restarting...")
                os.execv(sys.executable, ['python'] + sys.argv)

# === CPU USAGE LOG HARIAN ===
def cpu_usage_logger():
    while True:
        # anggaran masa polling aktif
        polling_seconds = 15 * 48  # 15s * 48 cycles = 12 min / hr
        logging.info(f"🖥 Anggaran CPU active hari ini: ~{polling_seconds/3600:.2f} jam")
        time.sleep(86400)

# === MAIN START ===
if __name__ == "__main__":
    START_TIME = time.time()
    keep_alive()
    threading.Thread(target=self_check, daemon=True).start()
    threading.Thread(target=cpu_usage_logger, daemon=True).start()
    polling_cycle()
