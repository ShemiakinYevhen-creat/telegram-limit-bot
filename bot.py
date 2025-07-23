from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === Налаштування ===
TOKEN = "8066278704:AAG759JUSEUzZ8-fNdepY_Y7d6IFvnX9zw4"  # твій токен
SUPERPAPA_ID = 84807467
SUPERMAMA_ID = 163952863

limit = 0
expenses = {SUPERPAPA_ID: 0, SUPERMAMA_ID: 0}

# === Клавіатура ===
keyboard = ReplyKeyboardMarkup([["Витрати", "Ліміт", "Залишок"]], resize_keyboard=True)

# === Команди ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот для обліку витрат запущений!", reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global limit, expenses
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "Ліміт":
        await update.message.reply_text("Введи новий ліміт (числом):")
        context.user_data["awaiting_limit"] = True
    elif text == "Витрати":
        await update.message.reply_text("Введи суму витрат (числом):")
        context.user_data["awaiting_expense"] = True
    elif text == "Залишок":
        total_expenses = sum(expenses.values())
        balance = limit - total_expenses
        response = (f"Ліміт: {limit} грн\n"
                    f"Витрати Суперпапа: {expenses[SUPERPAPA_ID]} грн\n"
                    f"Витрати Супермама: {expenses[SUPERMAMA_ID]} грн\n"
                    f"Залишок: {balance} грн")
        await update.message.reply_text(response)
    elif context.user_data.get("awaiting_limit"):
        try:
            limit = int(text)
            await update.message.reply_text(f"Новий ліміт: {limit} грн")
        except ValueError:
            await update.message.reply_text("Введи число!")
        context.user_data["awaiting_limit"] = False
    elif context.user_data.get("awaiting_expense"):
        try:
            amount = int(text)
            if user_id in expenses:
                expenses[user_id] += amount
                await update.message.reply_text(f"Додано витрати: {amount} грн")
            else:
                await update.message.reply_text("Ти не маєш доступу для внесення витрат.")
        except ValueError:
            await update.message.reply_text("Введи число!")
        context.user_data["awaiting_expense"] = False
    else:
        await update.message.reply_text("Вибери дію з кнопок.", reply_markup=keyboard)

# === Запуск ===
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
