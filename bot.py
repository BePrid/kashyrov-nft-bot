import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import aiosqlite
from stars_handler import get_star_topup_handler

logging.basicConfig(level=logging.INFO)
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
                balance REAL DEFAULT 0,
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "balance":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (query.from_user.id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(
            f"💰 Ваш баланс: {balance:.2f} ⭐️",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

    elif data == "settings":
        await query.edit_message_text("⚙️ Настройки:", reply_markup=get_settings_menu())

    elif data == "back_to_main":
        await query.edit_message_text("🏠 Главное меню:", reply_markup=get_main_menu())

    elif data == "profile":
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (query.from_user.id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
        await query.edit_message_text(
            f"👤 Ваш профиль:\nID: {query.from_user.id}\nБаланс: {balance:.2f} ⭐️\nРейтинг: скоро будет",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

    elif data == "deposit":
        await query.edit_message_text(
            "💫 Пополнение звёздами\n⚠️ Комиссия на пополнение — 3%\nВведите количество звёзд, которые хотите зачислить:",
        )
        context.user_data["awaiting_deposit"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_deposit"):
        try:
            amount = float(update.message.text)
            if amount <= 0:
                raise ValueError
            context.user_data["deposit_amount"] = amount
            context.user_data["awaiting_deposit"] = False
            keyboard = [
                [InlineKeyboardButton("✅ Оплатить", callback_data="confirm_deposit")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            await update.message.reply_text(
                f"🔔 Подтвердите отправку {amount:.0f} звёзд.\n"
                "После нажатия «Оплатить» передайте боту нужное количество звёзд в Telegram-подарке.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("❌ Введите корректное число.")
    else:
        await update.message.reply_text("Используйте кнопки ниже.")

async def main():
    print("🚀 Бот запускается...")
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(get_star_topup_handler())
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
