import os
import json
import asyncio
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

DATA_FILE = "data.json"
BASE_LIMIT = 40000  # Базовий ліміт щомісяця
ALLOWED_USERS = [84807467, 163952863]
DAD_ID = 84807467
MOM_ID = 163952863

# Завантаження/збереження даних
user_data = {
    'limit': BASE_LIMIT,
    'dad_spent': 0,
    'mom_spent': 0,
    'carry_over': 0,
    'month': datetime.datetime.now().month,
    'history': {"dad": [], "mom": []},
    'archive': {}
}

def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            user_data.update(json.load(f))

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f)

# Меню
keyboard = [["➖ Витрати", "↩️ Видалити витрату"], ["🎯 Ліміт", "💰 Баланс"], ["📊 Звіт за місяць", "📚 Архів місяців"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def check_access(update: Update):
    if update.message.from_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ У вас немає доступу до цього бота.")
        return False
    return True

# Автооновлення бюджету 1-го числа
def check_new_month():
    now = datetime.datetime.now()
    if now.month != user_data['month']:
        total_spent = user_data['dad_spent'] + user_data['mom_spent']
        carry = user_data['limit'] - total_spent
        new_limit = BASE_LIMIT + carry
        # Архівування старого місяця
        user_data['archive'][f"{user_data['month']}-{now.year}"] = {
            "limit": user_data['limit'],
            "dad_spent": user_data['dad_spent'],
            "mom_spent": user_data['mom_spent'],
            "carry": carry
        }
        # Оновлення даних
        user_data['limit'] = new_limit
        user_data['dad_spent'] = 0
        user_data['mom_spent'] = 0
        user_data['history'] = {"dad": [], "mom": []}
        user_data['month'] = now.month
        save_data()
        return carry, new_limit
    return None, None

# Команди
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    carry, new_limit = check_new_month()
    if carry is not None:
        sign = "+" if carry >= 0 else "-"
        await update.message.reply_text(
            f"Новий місяць!\nБазовий ліміт: {BASE_LIMIT} грн\nПеренесено з минулого: {sign}{abs(carry)} грн\nНовий бюджет: {new_limit} грн"
        )
    await update.message.reply_text("👋 Привіт! Оберіть дію:", reply_markup=markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    text = update.message.text
    if text == "➖ Витрати":
        await update.message.reply_text("Введи суму витрати:")
        context.user_data['action'] = 'spend'
    elif text == "↩️ Видалити витрату":
        user = update.message.from_user
        key = "dad" if user.id == DAD_ID else "mom"
        if user_data['history'][key]:
            last = user_data['history'][key].pop()
            if key == "dad":
                user_data['dad_spent'] -= last
            else:
                user_data['mom_spent'] -= last
            save_data()
            await update.message.reply_text(f"Останню витрату {last} грн видалено.")
        else:
            await update.message.reply_text("Немає витрат для видалення.")
    elif text == "🎯 Ліміт":
        await update.message.reply_text("Введи новий ліміт на місяць:")
        context.user_data['action'] = 'limit'
    elif text == "💰 Баланс":
        dad, mom, limit = user_data['dad_spent'], user_data['mom_spent'], user_data['limit']
        balance = limit - dad - mom
        await update.message.reply_text(
            f"🎯 Ліміт: {limit} грн\n"
            f"🧔‍♂️ Витрати Суперпапа: {dad} грн\n"
            f"👩‍🍼 Витрати Супермама: {mom} грн\n"
            f"💚 Залишок: {balance} грн"
        )
    elif text == "📊 Звіт за місяць":
        month_key = f"{user_data['month']}-{datetime.datetime.now().year}"
        dad, mom, limit = user_data['dad_spent'], user_data['mom_spent'], user_data['limit']
        spent = dad + mom
        balance = limit - spent
        await update.message.reply_text(
            f"📊 Звіт за {month_key}:\n"
            f"Бюджет: {limit} грн\n"
            f"🧔‍♂️ Суперпапа: {dad} грн\n"
            f"👩‍🍼 Супермама: {mom} грн\n"
            f"Разом витрати: {spent} грн\n"
            f"Залишок: {balance} грн"
        )
    elif text == "📚 Архів місяців":
        if not user_data['archive']:
            await update.message.reply_text("Архів порожній.")
            return
        text = "📚 Архів попередніх місяців:\n"
        for month, data in user_data['archive'].items():
            spent = data['dad_spent'] + data['mom_spent']
            balance = data['limit'] - spent
            sign = "+" if balance >= 0 else "-"
            text += f"{month}: Ліміт {data['limit']} грн, Витрати {spent} грн, Залишок {sign}{abs(balance)} грн\n"
        await update.message.reply_text(text)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    if not user_data['archive']:
        await update.message.reply_text("Архів порожній.")
        return
    text = "📚 Архів попередніх місяців:\n"
    for month, data in user_data['archive'].items():
        spent = data['dad_spent'] + data['mom_spent']
        balance = data['limit'] - spent
        sign = "+" if balance >= 0 else "-"
        text += f"{month}: Ліміт {data['limit']} грн, Витрати {spent} грн, Залишок {sign}{abs(balance)} грн\n"
    await update.message.reply_text(text)

async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Введи правильну суму.")
        return

    user = update.message.from_user
    action = context.user_data.get('action')
    if action == 'limit':
        user_data['limit'] = amount
        save_data()
        await update.message.reply_text(f"🎯 Встановлено новий ліміт: {amount} грн")
    elif action == 'spend':
        key = "dad" if user.id == DAD_ID else "mom"
        user_data['history'][key].append(amount)
        if key == "dad":
            user_data['dad_spent'] += amount
        else:
            user_data['mom_spent'] += amount
        save_data()
        await update.message.reply_text(f"➖ Додано витрату: {amount} грн")
    context.user_data['action'] = None

# Запуск
if __name__ == "__main__":
    load_data()
    token = os.getenv("BOT_TOKEN")
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    path = "webhook"
    webhook_url = f"{render_url}/{path}"

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^[^\d]+$"), handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+(\.\d+)?$"), handle_numbers))

    asyncio.get_event_loop().run_until_complete(app.bot.set_webhook(webhook_url))
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=path,
        webhook_url=webhook_url
    )
