import json
import os
import threading
import time
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "data.json"
PING_URL = os.getenv("PING_URL", "https://telegram-limit-bot.onrender.com")

# ===== Збереження даних =====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"limit": 40000, "balance": 40000, "expenses": [], "incomes": [], "archive": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ===== Кнопки =====
MAIN_MENU = ReplyKeyboardMarkup(
    [["Витрати", "Дохід"], ["Звіт", "Видалити витрату"]],
    resize_keyboard=True
)

# ===== Логіка =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Відправ суму або обери дію:", reply_markup=MAIN_MENU)

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи суму витрати:")
    return 1

async def save_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        data["expenses"].append({"amount": amount, "date": str(datetime.now())})
        data["balance"] -= amount
        save_data(data)
        await update.message.reply_text(f"Додано витрату: {amount} грн\nБаланс: {data['balance']} грн", reply_markup=MAIN_MENU)
    except:
        await update.message.reply_text("Невірний формат. Введи число.")
    return ConversationHandler.END

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи суму доходу:")
    return 2

async def save_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        data["incomes"].append({"amount": amount, "date": str(datetime.now())})
        save_data(data)
        await update.message.reply_text(f"Додано дохід: {amount} грн", reply_markup=MAIN_MENU)
    except:
        await update.message.reply_text("Невірний формат. Введи число.")
    return ConversationHandler.END

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_exp = sum(x["amount"] for x in data["expenses"])
    total_inc = sum(x["amount"] for x in data["incomes"])
    await update.message.reply_text(
        f"📊 Звіт за поточний місяць:\n"
        f"Дохід: {total_inc} грн\n"
        f"Витрати: {total_exp} грн\n"
        f"Баланс: {data['balance']} грн",
        reply_markup=MAIN_MENU
    )

async def delete_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if data["expenses"]:
        last = data["expenses"].pop()
        data["balance"] += last["amount"]
        save_data(data)
        await update.message.reply_text(f"Видалено витрату {last['amount']} грн.\nБаланс: {data['balance']} грн", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("Немає витрат для видалення.", reply_markup=MAIN_MENU)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# ===== Пінг Render =====
def ping():
    import requests
    while True:
        try:
            requests.get(PING_URL)
        except:
            pass
        time.sleep(300)  # кожні 5 хвилин

# ===== Flask для вебхука =====
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    threading.Thread(target=ping, daemon=True).start()

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Витрати$"), add_expense),
            MessageHandler(filters.Regex("^Дохід$"), add_income)
        ],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_expense)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_income)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^Звіт$"), report))
    application.add_handler(MessageHandler(filters.Regex("^Видалити витрату$"), delete_last))
    application.add_handler(conv_handler)

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=TOKEN,
        webhook_url=f"{PING_URL}/{TOKEN}"
    )
