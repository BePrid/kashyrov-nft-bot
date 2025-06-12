import os
import logging
import asyncio
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("TOKEN")

# Главное меню
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Баланс", callback_data="balance"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit"),
         InlineKeyboardButton("🤖 Автопокупка: вкл", callback_data="toggle_autobuy")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Настройки
def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🔽 Мин. лимит", callback_data="set_min_limit")],
        [InlineKeyboardButton("🔼 Макс. лимит", callback_data="set_max_limit")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Пополнение
def get_deposit_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Оплатить", callback_data="confirm_deposit")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance REAL DEFAULT 0,
                auto_buy INTEGER DEFAULT 1
            )
        """)
        await db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)",
            (user.id, user.first_name)
        )
        await db.commit()
    await update.message.reply_text("Добро пожаловать!", reply_markup=get_main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, используйте кнопки ниже.", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "balance":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(f"💳 Ваш баланс: {balance:.2f} звёзд", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]))

    elif data == "settings":
        await query.edit_message_text("Настройки:", reply_markup=get_settings_menu())

    elif data == "deposit":
        await query.edit_message_text("⚠️ Комиссия на пополнение — 3%\nХотите продолжить?", reply_markup=get_deposit_menu())

    elif data == "confirm_deposit":
        await query.edit_message_text("💫 Введите количество звёзд, которое вы хотите зачислить:")

    elif data == "toggle_autobuy":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT auto_buy FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                status = not bool(row[0]) if row else True
            await db.execute("UPDATE users SET auto_buy = ? WHERE user_id = ?", (int(status), user_id))
            await db.commit()
        text = "🤖 Автопокупка: вкл" if status else "🤖 Автопокупка: выкл"
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

    elif data == "profile":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance, auto_buy FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
                auto = "Вкл" if row[1] else "Выкл"
        await query.edit_message_text(
            f"👤 Ваш профиль:\nID: {user_id}\nБаланс: {balance:.2f} звёзд\nАвтопокупка: {auto}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

    elif data == "back_to_main":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

    else:
        await query.edit_message_text(f"Вы нажали: {data}", reply_markup=get_main_menu())

async def main():
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Бот запускается...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
