import os
import telebot
import pandas as pd
from flask import Flask, request
from datetime import datetime

# === CONFIG ===
TOKEN = os.environ.get("BOT_TOKEN")  # Token bot dari @BotFather
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# === LOAD DATA EXCEL ===
try:
    df = pd.read_excel("data.xlsx")  # Fail Excel mesti ada dalam server
except Exception as e:
    print("⚠️ Gagal buka Excel:", e)
    df = pd.DataFrame()

# Simpan masa bot mula
start_time = datetime.now()


# === COMMAND HANDLER ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "👋 Hai! Selamat datang ke *Bot Sokongan*.\n\n"
                 "Guna menu atau taip arahan berikut:\n"
                 "/help – Bantuan\n"
                 "/delima – Portal DELIMa KPM\n"
                 "/ains – Advanced Integrated NILAM System (AINS)\n"
                 "/resetpassword – Panduan reset kata laluan\n"
                 "/status – Semak status bot",
                 parse_mode="Markdown")


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message,
                 "ℹ️ *Senarai arahan yang tersedia:*\n\n"
                 "➡️ /start – Mula semula bot\n"
                 "➡️ /help – Senarai arahan\n"
                 "➡️ /delima – Portal DELIMa KPM\n"
                 "➡️ /ains – Advanced Integrated NILAM System (AINS)\n"
                 "➡️ /resetpassword – Panduan reset kata laluan\n"
                 "➡️ /status – Semak status bot",
                 parse_mode="Markdown")


@bot.message_handler(commands=['delima'])
def send_delima(message):
    bot.reply_to(message,
                 "🌐 Klik pautan untuk akses *DELIMa KPM*:\n"
                 "👉 https://idp.iam.moe.gov.my\n",
                 parse_mode="Markdown")


@bot.message_handler(commands=['ains'])
def send_ains(message):
    bot.reply_to(message,
                 "📖 Klik pautan untuk akses *Advanced Integrated NILAM System (AINS)*:\n"
                 "👉 https://ains.moe.gov.my/login?returnUrl=/",
                 parse_mode="Markdown")


@bot.message_handler(commands=['resetpassword'])
def send_reset(message):
    bot.reply_to(message,
                 "🔑 *Panduan Reset Kata Laluan Akaun Google Education (MOE):*\n\n"
                 "1️⃣ Pergi ke pautan reset: https://password.moe.gov.my\n"
                 "2️⃣ Masukkan ID pengguna (contoh: nama@moe-dl.edu.my)\n"
                 "3️⃣ Ikut arahan di skrin untuk tetapkan semula kata laluan\n\n"
                 "⚠️ Ingatkan murid/ibu bapa agar tidak melupakan kata laluan lagi.",
                 parse_mode="Markdown")


@bot.message_handler(commands=['status'])
def send_status(message):
    now = datetime.now()
    jumlah = len(df) if not df.empty else 0
    uptime = now - start_time

    # Format uptime: hari, jam, minit, saat
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
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

    uptime_str = " ".join(uptime_parts) if uptime_parts else "0 saat"

    status_text = (
        "📊 *Maklumat Status Sistem Bot*\n\n"
        f"✅ Status Bot: Aktif & Beroperasi\n"
        f"👥 Jumlah murid dalam rekod: *{jumlah} orang*\n"
        f"🖥️ Server Flask: *Running*\n"
        f"⏱️ Masa semasa: {now.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"⏳ Uptime: {uptime_str}\n\n"
        "🔧 *Maklumat Tambahan:*\n"
        "📂 Source code: *GitHub*\n"
        "💻 Coding language: *Python*\n"
        "☁️ Server: *Render*\n"
        "📡 Status monitor: *UpTimeRobot*\n"
        "🌐 Status page: [Klik di sini](https://stats.uptimerobot.com/k6aooeDaUq)"
    )

    bot.reply_to(message, status_text, parse_mode="Markdown")


# === FLASK WEBHOOK ===
@app.route("/" + TOKEN, methods=['POST'])
def getMessage():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def webhook():
    return "Bot is running with Flask!", 200


# === RUN ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
