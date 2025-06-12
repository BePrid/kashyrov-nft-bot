import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import aiosqlite
import nest_asyncio

nest_asyncio.apply()

TOKEN = os.getenv("TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

user_states = {}

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Баланс", callback_data="balance")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("🤖 Автопокупка: вкл", callback_data="toggle_autobuy")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🔽 Мин. цена", callback_data="set_min_price")],
        [InlineKeyboardButton("🔼 Макс. цена", callback_data="set_max_price")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance REAL DEFAULT 0,
                min_price INTEGER DEFAULT 5,
                max_price INTEGER DEFAULT 50,
                auto_buy INTEGER DEFAULT 1
            )
            """
        )
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
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state == "awaiting_deposit":
        try:
            stars = float(update.message.text)
            deposit = stars * 0.97
            async with aiosqlite.connect("users.db") as db:
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (deposit, user_id)
                )
                await db.commit()
            await update.message.reply_text(f"🎉 Баланс успешно пополнен на {deposit:.2f} звёзд!", reply_markup=get_main_menu())
        except ValueError:
            await update.message.reply_text("Введите корректное число звёзд.", reply_markup=get_back_button())
        finally:
            user_states.pop(user_id, None)
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки ниже.", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    await query.answer()

    if query.data == "balance":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(f"💳 Ваш баланс: {balance:.2f} звёзд", reply_markup=get_back_button())

    elif query.data == "settings":
        await query.edit_message_text("⚙️ Настройки", reply_markup=get_settings_menu())

    elif query.data == "deposit":
        user_states[user_id] = "awaiting_deposit"
        await query.edit_message_text("⚠️ Комиссия на пополнение — 3%\n\nВведите количество звёзд, которое вы хотите зачислить:", reply_markup=get_back_button())

    elif query.data == "toggle_autobuy":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT auto_buy FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                current = row[0] if row else 1
            new_state = 0 if current else 1
            await db.execute("UPDATE users SET auto_buy = ? WHERE user_id = ?", (new_state, user_id))
            await db.commit()
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

    elif query.data == "profile":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(f"👤 Ваш профиль\nID: {user_id}\nБаланс: {balance:.2f} звёзд", reply_markup=get_back_button())

    elif query.data == "back_to_main":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

async def main():
    print("🚀 Бот запускается...")
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
