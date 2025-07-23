import os
import json
import logging
from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константи
TOKEN = os.getenv("BOT_TOKEN")  # Додаєш у Render → Environment
USERS = [84807467, 163952863]  # Дозволені користувачі
DATA_FILE = "data.json"
MONTHLY_LIMIT = 40000

# Ініціалізація
app_telegram = Application.builder().token(TOKEN).build()
flask_app = Flask(__name__)

# Дані
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"expenses": [], "incomes": [], "balance": MONTHLY_LIMIT, "last_month": ""}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Команди
async def start(update: Update, context: CallbackContext):
    if update.effective_user.id not in USERS:
        return await update.message.reply_text("⛔ Доступ заборонено!")
    await update.message.reply_text("👋 Привіт! Бот для ведення витрат.\nКоманди:\n- Додай число для витрати\n- /доход + число\n- /баланс")

async def add_expense(update: Update, context: CallbackContext):
    if update.effective_user.id not in USERS:
        return await update.message.reply_text("⛔ Доступ заборонено!")
    try:
        amount = float(update.message.text)
        data["expenses"].append({"amount": amount, "user": update.effective_user.id, "date": datetime.now().isoformat()})
        data["balance"] -= amount
        save_data()
        await update.message.reply_text(f"✅ Витрата додана: {amount} грн\nБаланс: {data['balance']} грн")
    except:
        await update.message.reply_text("Введи число!")

async def add_income(update: Update, context: CallbackContext):
    if update.effective_user.id not in USERS:
        return await update.message.reply_text("⛔ Доступ заборонено!")
    try:
        amount = float(context.args[0])
        data["incomes"].append({"amount": amount, "date": datetime.now().isoformat()})
        save_data()
        await update.message.reply_text(f"💰 Дохід додано: {amount} грн")
    except:
        await update.message.reply_text("Формат: /доход 1000")

async def balance(update: Update, context: CallbackContext):
    if update.effective_user.id not in USERS:
        return await update.message.reply_text("⛔ Доступ заборонено!")
    await update.message.reply_text(f"🎯 Баланс: {data['balance']} грн")

# Реєстрація команд
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("доход", add_income))
app_telegram.add_handler(CommandHandler("баланс", balance))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))

# Flask — маршрут для Telegram
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_telegram.bot)
    app_telegram.update_queue.put_nowait(update)
    return "ok"

@flask_app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    url = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-limit-bot.onrender.com") + "/webhook"
    import asyncio
    asyncio.get_event_loop().run_until_complete(app_telegram.bot.set_webhook(url))
    flask_app.run(host="0.0.0.0", port=10000)
