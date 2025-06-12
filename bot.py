import os
import logging
import aiosqlite
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN")

main_keyboard = ReplyKeyboardMarkup([
    ["💳 Баланс", "⚙️ Настройки"],
    ["💰 Пополнить", "🤖 Автопокупка: вкл"],
    ["👤 Профиль"]
], resize_keyboard=True)

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "user_id INTEGER PRIMARY KEY,"
            "first_name TEXT,"
            "balance INTEGER DEFAULT 0,"
            "min_price INTEGER DEFAULT 5,"
            "max_price INTEGER DEFAULT 50,"
            "auto_buy INTEGER DEFAULT 1)"
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
    await update.message.reply_text("Добро пожаловать!", reply_markup=main_keyboard)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💳 Баланс":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                balance = (await cursor.fetchone())[0]
        await update.message.reply_text(f"💰 Ваш баланс: {balance} звёзд", reply_markup=main_keyboard)

    elif text == "⚙️ Настройки":
        keyboard = [
            [InlineKeyboardButton("🔽 Мин. лимит", callback_data="set_min_price")],
            [InlineKeyboardButton("🔼 Макс. лимит", callback_data="set_max_price")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        await update.message.reply_text("Настройки:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif text == "💰 Пополнить":
        keyboard = [
            [InlineKeyboardButton("✅ Оплатить", callback_data="pay_stars")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        await update.message.reply_text("⚠️ Комиссия на пополнение — 3%\nХотите продолжить?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif text.startswith("🤖 Автопокупка"):
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT auto_buy FROM users WHERE user_id = ?", (user_id,)) as cursor:
                current = (await cursor.fetchone())[0]
            new = 0 if current else 1
            await db.execute("UPDATE users SET auto_buy = ? WHERE user_id = ?", (new, user_id))
            await db.commit()
        label = "🤖 Автопокупка: вкл" if new else "🤖 Автопокупка: выкл"
        main_keyboard.keyboard[1][1] = label
        await update.message.reply_text(f"{label}", reply_markup=main_keyboard)

    elif text == "👤 Профиль":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                balance = (await cursor.fetchone())[0]
        await update.message.reply_text(
            f"👤 Ваш ID: {user_id}\n💫 Баланс: {balance} звёзд\n🏆 Рейтинг: скоро",
            reply_markup=main_keyboard
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "back_to_main":
        await query.edit_message_text("Главное меню", reply_markup=main_keyboard)

async def main():
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(main())
