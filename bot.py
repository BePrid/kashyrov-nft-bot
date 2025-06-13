import os
import asyncio
import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.getenv("TOKEN")
user_states = {}

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Баланс", callback_data="balance")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("🤖 Автопокупка: вкл", callback_data="toggle_autobuy")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🔽 Мин. цена", callback_data="set_min_price")],
        [InlineKeyboardButton("🔼 Макс. цена", callback_data="set_max_price")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                commission INTEGER DEFAULT 0,
                min_price INTEGER DEFAULT 5,
                max_price INTEGER DEFAULT 50,
                max_per_drop INTEGER DEFAULT 3,
                min_drop_size INTEGER DEFAULT 20,
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

async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = "awaiting_deposit_amount"
    await query.edit_message_text(
        "💫 Введите количество звёзд, которое вы хотите пополнить.\n⚠️ Комиссия составит 3%.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ])
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_states.get(user_id) == "awaiting_deposit_amount":
        if text.isdigit():
            amount = int(text)
            commission = round(amount * 0.03)
            credited = amount - commission
            async with aiosqlite.connect("users.db") as db:
                await db.execute("UPDATE users SET balance = balance + ?, commission = commission + ? WHERE user_id = ?", (credited, commission, user_id))
                await db.commit()
            user_states[user_id] = None
            await update.message.reply_text(
                f"🎉 Баланс успешно пополнен на {credited} звёзд!\n💸 Комиссия: {commission} звёзд.",
                reply_markup=get_main_menu()
            )
        else:
            await update.message.reply_text("Введите число — количество звёзд.")
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки ниже.", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "balance":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (query.from_user.id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(f"💳 Ваш баланс: {balance} звёзд.", reply_markup=get_main_menu())

    elif data == "deposit":
        await deposit_start(update, context)

    elif data == "back_to_main":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())

    else:
        await query.edit_message_text(f"Вы нажали: {data}", reply_markup=get_main_menu())

async def main():
    print("🚀 Бот запускается...")
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
