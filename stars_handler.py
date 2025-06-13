from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

# Этапы диалога
WAITING_FOR_STAR_AMOUNT, CONFIRMING_PAYMENT = range(2)

# Временное хранилище звёзд
pending_star_inputs = {}

async def start_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        "💫 Пополнение звездами.
Мы берём комиссию 3%.
Введите количество звёзд, которое хотите зачислить:"
    )
    return WAITING_FOR_STAR_AMOUNT

async def receive_star_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("Введите корректное положительное число.")
        return WAITING_FOR_STAR_AMOUNT

    pending_star_inputs[user_id] = int(text)

    keyboard = [
        [InlineKeyboardButton("✅ Оплатить", callback_data="confirm_payment")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    await update.message.reply_text(
        f"Вы указали {text} звёзд.
Нажмите «Оплатить», чтобы передать звёзды боту.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMING_PAYMENT

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = pending_star_inputs.get(user_id)

    if not amount:
        await update.callback_query.message.edit_text("Ошибка: нет данных о пополнении.")
        return ConversationHandler.END

    # Рассчитываем комиссию
    received = int(amount * 0.97)
    fee = amount - received

    await update.callback_query.answer()

    # Замените @YOUR_BOT_USERNAME на фактическое имя бота
    bot_username = context.bot.username
    deep_link = f"https://t.me/{bot_username}?start={user_id}_topup_{amount}"

    await update.callback_query.message.edit_text(
        f"💫 Отправьте {amount} звёзд, используя кнопку ниже.
"
        f"Мы зачислим {received} звёзд, а {fee} пойдут в комиссию.

"
        f"🔗 [Отправить звёзды боту]({deep_link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text("Действие отменено.")
    return ConversationHandler.END

def get_star_topup_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_topup, pattern="^topup$")],
        states={
            WAITING_FOR_STAR_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_star_amount)],
            CONFIRMING_PAYMENT: [CallbackQueryHandler(confirm_payment, pattern="^confirm_payment$"),
                                 CallbackQueryHandler(cancel, pattern="^back_to_main$")]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^back_to_main$")]
    )
