import os
import asyncio
import logging
import nest_asyncio
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

nest_asyncio.apply()
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

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance INTEGER DEFAULT 0
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
    if context.user_data.get("awaiting_deposit"):
        try:
            amount = int(update.message.text)
            if amount <= 0:
                raise ValueError
            net = int(amount * 0.97)
            fee = amount - net
            context.user_data["deposit_amount"] = net
            context.user_data["fee_amount"] = fee
            context.user_data["awaiting_deposit"] = False

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_deposit")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ])

            await update.message.reply_text(
                f"💫 Вы указали {amount} звёзд\n"
                f"✅ Будет зачислено: {net} звёзд\n"
                f"💸 Комиссия: {fee} звёзд\n\n"
                f"Подтвердите пополнение:",
                reply_markup=keyboard
            )
        except:
            await update.message.reply_text("Введите корректное целое число звёзд.")
        return

    await update.message.reply_text("Используйте кнопки ниже.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "deposit":
        context.user_data["awaiting_deposit"] = True
        await query.message.reply_text("💫 Введите количество звёзд, которое вы хотите зачислить (комиссия 3%)")
    elif query.data == "confirm_deposit":
        user_id = query.from_user.id
        amount = context.user_data.get("deposit_amount", 0)
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()
        await query.message.edit_text(f"🎉 Баланс успешно пополнен на {amount} звёзд!")
        context.user_data.clear()
    elif query.data == "balance":
        user_id = query.from_user.id
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
        await query.message.edit_text(f"💰 Ваш текущий баланс: {row[0]} звёзд", reply_markup=get_main_menu())
    elif query.data == "profile":
        user = query.from_user
        await query.message.edit_text(f"👤 Профиль\nИмя: {user.first_name}\nID: {user.id}", reply_markup=get_main_menu())
    elif query.data == "back_to_main":
        context.user_data.clear()
        await query.message.edit_text("↩️ Главное меню", reply_markup=get_main_menu())
    else:
        await query.message.edit_text(f"Вы нажали: {query.data}", reply_markup=get_main_menu())

async def main():
    print("🚀 Бот запускается...")
    await init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
