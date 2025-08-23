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

# === LOAD EXCEL ===
EXCEL_FILE = "ID DELIMA - DATA FEED CHATBOT.xlsx"
try:
    df = pd.read_excel(EXCEL_FILE)
    df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
    logging.info("✅ Excel loaded successfully")
except FileNotFoundError:
    logging.error("❌ Excel file not found. Make sure it's in the same folder.")
    df = pd.DataFrame()

# === HANDLERS (TAK USIK SIKIT PUN) ===
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

# === FIXED POLLING LOOP (STABIL) ===
def polling_cycle():
    while True:
        try:
            logging.info("🚀 Starting polling...")
            bot.polling(none_stop=True, skip_pending=True, long_polling_timeout=30)
        except ApiTelegramException as e:
            logging.error(f"💥 Telegram API error: {e}. Restarting in 15s...")
            time.sleep(15)
        except Exception as e:
            logging.error(f"💥 Bot crash/error: {e}. Restarting in 15s...")
            time.sleep(15)

# === MAIN START ===
if __name__ == "__main__":
    START_TIME = time.time()
    keep_alive()
    polling_cycle()
