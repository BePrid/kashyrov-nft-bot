import os
import asyncio
import logging
import aiosqlite
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.getenv("TOKEN")

# ================= Кнопки ====================

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Баланс", callback_data="balance"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit"),
         InlineKeyboardButton("🤖 Автопокупка: вкл", callback_data="toggle_autobuy")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🔽 Мин. лимит", callback_data="set_min_limit")],
        [InlineKeyboardButton("🔼 Макс. лимит", callback_data="set_max_limit")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deposit_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Оплатить", callback_data="confirm_deposit")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(keyboard)

# ================ База данных ===================

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                auto_buy INTEGER DEFAULT 1
            )
        """)
        await db.commit()

# ================ Хендлеры ===================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user.id, user.first_name))
        await db.commit()
    await update.message.reply_text("Добро пожаловать!", reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with aiosqlite.connect("users.db") as db:
        if query.data == "balance":
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
            await query.edit_message_text(f"💰 Ваш баланс: {balance} звёзд", reply_markup=get_back_menu())

        elif query.data == "settings":
            await query.edit_message_text("⚙️ Настройки:", reply_markup=get_settings_menu())

        elif query.data == "deposit":
            await query.edit_message_text("⚠️ Комиссия на пополнение — 3%
Хотите продолжить?", reply_markup=get_deposit_menu())

        elif query.data == "profile":
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                balance = row[0] if row else 0
            await query.edit_message_text(
                f"👤 Ваш ID: {user_id}
💫 Баланс: {balance} звёзд
🏆 Рейтинг: скоро",
                reply_markup=get_back_menu()
            )

        elif query.data == "toggle_autobuy":
            await db.execute("UPDATE users SET auto_buy = 1 - auto_buy WHERE user_id = ?", (user_id,))
            await db.commit()
            async with db.execute("SELECT auto_buy FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                status = "вкл" if row[0] else "выкл"
            await query.edit_message_text("Главное меню", reply_markup=get_main_menu())

        elif query.data == "back_to_main":
            await query.edit_message_text("Главное меню", reply_markup=get_main_menu())

        elif query.data in ["set_min_limit", "set_max_limit", "confirm_deposit"]:
            await query.edit_message_text("⏳ Функция пока в разработке", reply_markup=get_back_menu())

# ================ Запуск ===================

async def main():
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
