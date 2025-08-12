import os
import telebot
import pandas as pd
from flask import Flask, request

# === CONFIG ===
TOKEN = "8201238992:AAGZeU59gksGe6y6EE3ljETNim-RpjZjCCg"  # new token
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, "ID DELIMA - DATA FEED CHATBOT.xlsx")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# === LOAD EXCEL ===
try:
    df = pd.read_excel(EXCEL_FILE)
    df['Nama Murid'] = df['Nama Murid'].astype(str).str.strip().str.upper()
except Exception as e:
    print(f"Error loading Excel file: {e}")
    exit()

# === BOT HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Sila isi nama penuh murid dan hantar, pastikan tiada kesalahan ejaan pada nama."
    )

@bot.message_handler(func=lambda message: True)
def send_info(message):
    search_name = message.text.strip().upper()
    matches = df[df['Nama Murid'].str.contains(search_name, case=False, na=False)]

    if matches.empty:
        bot.reply_to(message, "Maaf, nama tidak dijumpai.")
    else:
        row = matches.iloc[0]
        reply_text = (
            f"Nama Murid: {row['Nama Murid']}\n"
            f"Email: {row.iloc[1]}\n"
            f"Password: {row.iloc[2]}"
        )
        bot.reply_to(message, reply_text)

# === FLASK ROUTES FOR WEBHOOK ===
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_URL')}/{TOKEN}")
    return "Webhook set!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
