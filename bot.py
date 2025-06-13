import os
import asyncio
import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
TOKEN = os.getenv("TOKEN")

DEPOSIT_AMOUNT = 1

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Баланс", callback_data="balance")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("🤖 Автопокупка: вкл", callback_data="toggle_autobuy")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                min_price INTEGER DEFAULT 5,
                max_price INTEGER DEFAULT 50,
                max_per_drop INTEGER DEFAULT 3,
                min_drop_size INTEGER DEFAULT 20,
                auto_buy INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                commission INTEGER,
                net_amount INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
    await update.message.reply_text("Используйте кнопки ниже.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "balance":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (query.from_user.id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(f"💳 Ваш баланс: {balance} звёзд", reply_markup=get_main_menu())

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💫 Введите количество звёзд, которое вы хотите пополнить.

⚠️ Комиссия: 3%"
    )
    return DEPOSIT_AMOUNT

async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = int(update.message.text)
        if amount <= 0:
            raise ValueError

        commission = round(amount * 0.03)
        net = amount - commission

        async with aiosqlite.connect("users.db") as db:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (net, user_id)
            )
            await db.execute(
                "INSERT INTO payments (user_id, amount, commission, net_amount) VALUES (?, ?, ?, ?)",
                (user_id, amount, commission, net)
            )
            await db.commit()

        await update.message.reply_text(
            f"🎉 Баланс успешно пополнен на {net} звёзд!\n(Учтена комиссия {commission} звёзд)"
        )
    except ValueError:
        await update.message.reply_text("❌ Введите корректное число.")
    return ConversationHandler.END

async def main():
    import nest_asyncio
    nest_asyncio.apply()

    print("🚀 Бот запускается...")
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(balance|settings|toggle_autobuy|profile)$"))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(deposit_callback, pattern="^deposit$")],
        states={DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deposit_amount)]},
        fallbacks=[],
    ))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
