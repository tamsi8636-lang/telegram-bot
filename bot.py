import os
import sys
import time
import threading
import logging
from flask import Flask
import telebot
from telebot.apihelper import ApiTelegramException

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# === TELEGRAM BOT SETUP ===
TOKEN = os.environ.get("BOT_TOKEN")  # Token simpan di Render Environment
bot = telebot.TeleBot(TOKEN)

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def keep_alive():
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

# === UTIL: AUTO LOG SEMUA COMMAND & MESEJ ===
def log_command(message, cmd_name):
    user = message.from_user.username or "UnknownUser"
    user_id = message.from_user.id
    logging.info(f"📩 Command {cmd_name} diterima dari {user} (id={user_id})")

def log_message(message):
    user = message.from_user.username or "UnknownUser"
    user_id = message.from_user.id
    logging.info(f"💬 Mesej biasa dari {user} (id={user_id}): {message.text}")

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
    bot.reply_to(
        message,
        "📌 Senarai arahan:\n"
        "/start - Mula semula bot\n"
        "/help - Bantuan\n"
        "/delima - Pautan ke portal DELIMa\n"
        "/ains - Pautan ke AINS\n"
        "/resetpassword - Panduan reset kata laluan\n"
        "/status - Status server",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['delima'])
def send_delima(message):
    log_command(message, "/delima")
    bot.reply_to(message, "🌐 Sila layari portal DELIMa KPM: https://idp1.moe.gov.my")

@bot.message_handler(commands=['ains'])
def send_ains(message):
    log_command(message, "/ains")
    bot.reply_to(message, "📝 AINS (Advanced Integrated NILAM System): https://ains.moe.gov.my/login?returnUrl=/")

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
    uptime_seconds = int(time.time() - START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    bot.reply_to(
        message,
        f"✅ Server aktif.\n"
        f"⏱ Uptime: {days} hari, {hours} jam, {minutes} minit, {seconds} saat."
    )

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    log_message(message)
    bot.reply_to(
        message,
        f"🔍 Nama '{message.text}' diterima. "
        f"Sila tunggu proses semakan (demo sahaja)."
    )

# === AUTO RESTART SETIAP 15 MINIT ===
def auto_restart():
    while True:
        time.sleep(900)  # 15 minit = 900s
        logging.info("♻️ [Scheduled Restart] Restarting bot automatically (every 15 minutes)...")
        os.execv(sys.executable, ['python'] + sys.argv)

# === START BOT (TAHAN LASAK) ===
def run_bot():
    while True:
        try:
            logging.info("🚀 Bot polling dimulakan...")
            bot.polling(skip_pending=True, none_stop=True)
        except ApiTelegramException as e:
            if "409" in str(e):
                # Conflict, tunggu 20 saat sebelum restart
                logging.error(f"💥 Telegram API error 409 (Conflict): {e}. Restarting in 20s...")
                time.sleep(20)
            else:
                logging.error(f"💥 Telegram API error: {e}. Restarting immediately...")
                os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logging.error(f"💥 Bot crash/disconnect/error: {e}. Restarting immediately...")
            os.execv(sys.executable, ['python'] + sys.argv)

# === MAIN START ===
if __name__ == "__main__":
    START_TIME = time.time()
    keep_alive()
    threading.Thread(target=auto_restart, daemon=True).start()
    run_bot()
