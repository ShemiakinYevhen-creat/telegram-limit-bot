import os, json, time, threading, requests, pickle
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# ======= CONFIG =======
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PING_URL = os.getenv("PING_URL")
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
DATA_FILE = "data.pkl"
MONTHLY_LIMIT = 40000
# ======================

# ======= GOOGLE DRIVE CLIENT =======
def upload_backup():
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS)
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': f'backup_{int(time.time())}.pkl', 'parents': [GOOGLE_DRIVE_FOLDER_ID]}
    media = MediaFileUpload(DATA_FILE, mimetype='application/octet-stream')
    service.files().create(body=file_metadata, media_body=media).execute()
# ===================================

# ======= DATA STORAGE =======
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as f:
        data = pickle.load(f)
else:
    data = {"expenses": [], "income": [], "balance": MONTHLY_LIMIT}

def save_data():
    with open(DATA_FILE, "wb") as f:
        pickle.dump(data, f)
    upload_backup()
# ============================

# ======= PING FUNCTION =======
def ping_self():
    while True:
        try:
            if PING_URL:
                requests.get(PING_URL)
        except Exception as e:
            print(f"Ping error: {e}")
        time.sleep(300)
threading.Thread(target=ping_self, daemon=True).start()
# =============================

# ======= TELEGRAM BOT =======
app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Додати витрату", callback_data="add_expense")],
        [InlineKeyboardButton("Додати дохід", callback_data="add_income")],
        [InlineKeyboardButton("Подивитись баланс", callback_data="check_balance")]
    ]
    await update.message.reply_text("Що хочеш зробити?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "add_expense":
        await query.edit_message_text("Введи суму витрати:")
        context.user_data["action"] = "add_expense"
    elif query.data == "add_income":
        await query.edit_message_text("Введи суму доходу:")
        context.user_data["action"] = "add_income"
    elif query.data == "check_balance":
        await query.edit_message_text(f"Поточний баланс: {data['balance']} грн")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("action")
    if action == "add_expense":
        try:
            amount = float(update.message.text)
            data["expenses"].append({"amount": amount, "date": str(datetime.now())})
            data["balance"] -= amount
            save_data()
            await update.message.reply_text(f"Витрата {amount} грн додана. Баланс: {data['balance']} грн")
        except:
            await update.message.reply_text("Некоректне число!")
        context.user_data.pop("action")
    elif action == "add_income":
        try:
            amount = float(update.message.text)
            data["income"].append({"amount": amount, "date": str(datetime.now())})
            save_data()
            await update.message.reply_text(f"Дохід {amount} грн доданий.")
        except:
            await update.message.reply_text("Некоректне число!")
        context.user_data.pop("action")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
# ============================

# ======= FLASK WEBHOOK =======
@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running!"
# =============================

if __name__ == "__main__":
    import asyncio
    from telegram.ext import Application
    from googleapiclient.http import MediaFileUpload
    asyncio.get_event_loop().run_until_complete(bot_app.bot.set_webhook(f"{PING_URL}/webhook"))
    app.run(host="0.0.0.0", port=10000)
