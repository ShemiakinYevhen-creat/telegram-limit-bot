import os
import json
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

DATA_FILE = "data.json"
BASE_LIMIT = 40000
ALLOWED_USERS = [84807467, 163952863]
DAD_ID = 84807467
MOM_ID = 163952863

user_data = {
    'limit': BASE_LIMIT,
    'dad_spent': 0,
    'mom_spent': 0,
    'income': 0,
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

keyboard = [["➖ Витрати", "➕ Дохід", "↩️ Видалити витрату"],
            ["💰 Баланс"],
            ["📊 Звіт за місяць", "📚 Архів місяців"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def check_access(update: Update):
    if update.message.from_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ У вас немає доступу до цього бота.")
        return False
    return True

def check_new_month():
    now = datetime.datetime.now()
    if now.month != user_data['month']:
        total_spent = user_data['dad_spent'] + user_data['mom_spent']
        carry = user_data['limit'] - total_spent
        user_data['archive'][f"{user_data['month']}-{now.year}"] = {
            "limit": user_data['limit'],
            "dad_spent": user_data['dad_spent'],
            "mom_spent": user_data['mom_spent'],
            "income": user_data['income'],
            "carry": carry
        }
        user_data['limit'] = BASE_LIMIT
        user_data['dad_spent'] = 0
        user_data['mom_spent'] = 0
        user_data['income'] = 0
        user_data['history'] = {"dad": [], "mom": []}
        user_data['month'] = now.month
        save_data()
        return carry
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    carry = check_new_month()
    if carry is not None:
        sign = "+" if carry >= 0 else "-"
        await update.message.reply_text(
            f"Новий місяць!\nБазовий ліміт: {BASE_LIMIT} грн\nПеренесено з минулого: {sign}{abs(carry)} грн"
        )
    await update.message.reply_text("👋 Привіт! Оберіть дію:", reply_markup=markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    text = update.message.text
    if text == "➖ Витрати":
        await update.message.reply_text("Введи суму витрати:")
        context.user_data['action'] = 'spend'
    elif text == "➕ Дохід":
        await update.message.reply_text("Введи суму доходу:")
        context.user_data['action'] = 'income'
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
    elif text == "💰 Баланс":
        dad, mom, limit, income = user_data['dad_spent'], user_data['mom_spent'], user_data['limit'], user_data['income']
        balance = limit - dad - mom
        await update.message.reply_text(
            f"🎯 Ліміт: {limit} грн\n"
            f"➕ Дохід: {income} грн\n"
            f"🧔‍♂️ Витрати Суперпапа: {dad} грн\n"
            f"👩‍🍼 Витрати Супермама: {mom} грн\n"
            f"💚 Залишок: {balance} грн"
        )
    elif text == "📊 Звіт за місяць":
        month_key = f"{user_data['month']}-{datetime.datetime.now().year}"
        dad, mom, limit, income = user_data['dad_spent'], user_data['mom_spent'], user_data['limit'], user_data['income']
        spent = dad + mom
        balance = limit - spent
        await update.message.reply_text(
            f"📊 Звіт за {month_key}:\n"
            f"Бюджет: {limit} грн\n"
            f"Дохід: {income} грн\n"
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
            text += (f"{month}: Ліміт {data['limit']} грн, Дохід {data['income']} грн, "
                     f"Витрати {spent} грн, Залишок {sign}{abs(balance)} грн\n")
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
    if action == 'income':
        user_data['income'] += amount
        save_data()
        await update.message.reply_text(f"➕ Додано дохід: {amount} грн")
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

if __name__ == "__main__":
    load_data()
    token = "8066278704:AAG759JUSEUzZ8-fNdepY_Y7d6IFvnX9zw4"
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^[^\d]+$"), handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+(\.\d+)?$"), handle_numbers))
    app.run_polling()
