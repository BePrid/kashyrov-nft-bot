import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import aiosqlite

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.getenv("TOKEN")


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
    await query.edit_message_text(f"Вы нажали: {query.data}")


async def main():
    print("🚀 Бот запускается...")
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.run_polling()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
