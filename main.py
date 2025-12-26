import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode

from config import Config
from scenarios import MEDICAL_SCENARIOS
from trainer import medical_trainer

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

CHOOSING_SCENARIO, IN_TRAINING = range(2)

TRAINING_KEYBOARD = ReplyKeyboardMarkup(
    [['📋 Анализировать диалог', '❌ Завершить тренировку']],
    resize_keyboard=True,
    one_time_keyboard=False
)

def get_scenarios_keyboard():
    buttons = []
    for scenario in MEDICAL_SCENARIOS:
        buttons.append([f"{scenario['id']}. {scenario['name']}"])
    buttons.append(['❓ Помощь', '📊 Моя статистика'])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🏥 **Medical Consultant Trainer Bot**

Я помогу вам отточить навыки медицинского консультирования через реалистичные сценарии.

**Как это работает:**
1. Выберите медицинский сценарий
2. Проведите диалог с виртуальным пациентом
3. Получите детальный анализ вашей работы
4. Улучшайте навыки на основе рекомендаций

**Выберите сценарий для начала тренировки:**
    """

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_scenarios_keyboard()
    )

    return CHOOSING_SCENARIO


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 **Руководство по использованию тренажера**

**1. Выбор сценария**
- Выберите один из предложенных медицинских сценариев
- Каждый сценарий имитирует реального пациента

**2. Проведение консультации**
- Вы выступаете в роли медицинского консультанта
- Пациент отвечает на ваши вопросы и задает свои
- Старайтесь быть профессиональными и эмпатичными

**3. Анализ диалога**
- После 3+ реплик нажмите "Анализировать диалог"
- Получите подробный разбор по критериям:
  • Профессиональная компетентность
  • Коммуникативные навыки
  • Конкретные ошибки и рекомендации

**4. Советы для эффективной тренировки:**
- Говорите с пациентом как с реальным человеком
- Задавайте уточняющие вопросы
- Объясняйте медицинские термины простым языком
- Проявляйте эмпатию и поддержку

**Доступные команды:**
/start - Начать новую тренировку
/help - Это руководство
/stats - Показать статистику
/cancel - Отменить текущую тренировку
    """

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def handle_scenario_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text[0].isdigit() and text[1] == '.':
        try:
            scenario_id = int(text[0])
            scenario = medical_trainer.get_scenario_by_id(scenario_id)

            if not scenario:
                await update.message.reply_text("❌ Сценарий не найден. Попробуйте еще раз.")
                return CHOOSING_SCENARIO

            session = medical_trainer.create_session(user_id, scenario_id)

            if not session:
                await update.message.reply_text("❌ Ошибка создания сессии. Попробуйте еще раз.")
                return CHOOSING_SCENARIO

            scenario_text = f"""
🎯 **Сценарий: {scenario['name']}**

📝 Описание: {scenario['description']}

**Рекомендации для консультанта:**
- Представьтесь и установите контакт
- Активно слушайте пациента
- Задавайте уточняющие вопросы
- Давайте четкие рекомендации
- Проявляйте эмпатию и поддержку

**Начните диалог с приветствия пациенту...**
            """

            await update.message.reply_text(
                scenario_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=TRAINING_KEYBOARD
            )

            await update.message.reply_text("⏳ Пациент заходит в кабинет...")

            patient_response = await medical_trainer.generate_patient_response(user_id)

            await update.message.reply_text(
                f"👤 **Пациент:**\n{patient_response}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=TRAINING_KEYBOARD
            )

            return IN_TRAINING

        except (ValueError, IndexError):
            await update.message.reply_text("❌ Пожалуйста, выберите сценарий из списка.")
            return CHOOSING_SCENARIO

    elif text == '❓ Помощь':
        await help_command(update, context)
        return CHOOSING_SCENARIO

    elif text == '📊 Моя статистика':
        await update.message.reply_text(
            "📊 Функция статистики в разработке. Следите за обновлениями!",
            reply_markup=get_scenarios_keyboard()
        )
        return CHOOSING_SCENARIO

    else:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите сценарий из списка ниже:",
            reply_markup=get_scenarios_keyboard()
        )
        return CHOOSING_SCENARIO


async def handle_training_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == '📋 Анализировать диалог':
        await analyze_dialogue(update, user_id)
        return ConversationHandler.END

    elif text == '❌ Завершить тренировку':
        await cancel_command(update, context)
        return ConversationHandler.END

    if not medical_trainer.is_session_active(user_id):
        await update.message.reply_text(
            "💤 Сессия завершена. Начните новую тренировку с /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if not medical_trainer.add_consultant_message(user_id, text):
        await update.message.reply_text("❌ Ошибка обработки сообщения.")
        return IN_TRAINING

    await update.message.reply_chat_action(action="typing")

    try:
        patient_response = await medical_trainer.generate_patient_response(user_id)

        await update.message.reply_text(
            f"👤 **Пациент:**\n{patient_response}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=TRAINING_KEYBOARD
        )

    except Exception as e:
        logger.error(f"Error generating patient response: {e}")
        await update.message.reply_text(
            "⚠️ Ошибка генерации ответа. Попробуйте еще раз.",
            reply_markup=TRAINING_KEYBOARD
        )

    return IN_TRAINING


async def analyze_dialogue(update: Update, user_id: int):
    await update.message.reply_text(
        "🔍 Анализирую вашу консультацию...",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        analysis_result = await medical_trainer.analyze_session(user_id)

        if "error" in analysis_result:
            await update.message.reply_text(
                f"⚠️ {analysis_result['error']}. Продолжайте диалог.",
                reply_markup=TRAINING_KEYBOARD
            )
            return

        analysis_text = analysis_result["analysis"]
        max_length = 4000

        if len(analysis_text) > max_length:
            parts = [analysis_text[i:i+max_length] for i in range(0, len(analysis_text), max_length)]

            await update.message.reply_text(
                f"📊 **Анализ вашей консультации**\n\n"
                f"📋 Сценарий: {analysis_result['scenario']}\n"
                f"💬 Сообщений: {analysis_result['total_messages']}\n"
                f"⏱️ Длительность: {analysis_result['duration']} мин\n\n"
                f"{parts[0]}",
                parse_mode=ParseMode.MARKDOWN
            )

            for part in parts[1:]:
                await update.message.reply_text(
                    part,
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(
                f"📊 **Анализ вашей консультации**\n\n"
                f"📋 Сценарий: {analysis_result['scenario']}\n"
                f"💬 Сообщений: {analysis_result['total_messages']}\n"
                f"⏱️ Длительность: {analysis_result['duration']} мин\n\n"
                f"{analysis_text}",
                parse_mode=ParseMode.MARKDOWN
            )

        await update.message.reply_text(
            "🎯 Хотите попробовать другой сценарий? Нажмите /start",
            reply_markup=ReplyKeyboardRemove()
        )

    except Exception as e:
        logger.error(f"Error analyzing dialogue: {e}")
        await update.message.reply_text(
            "❌ Ошибка при анализе диалога. Попробуйте еще раз.",
            reply_markup=TRAINING_KEYBOARD
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if medical_trainer.is_session_active(user_id):
        medical_trainer.end_session(user_id)
        await update.message.reply_text(
            "✅ Тренировка отменена. Для начала новой нажмите /start",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "ℹ️ Активной тренировки нет. Для начала нажмите /start",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_text = """
📊 **Статистика тренировок** (в разработке)

В будущих версиях здесь будет:
• Общее количество проведенных консультаций
• Средняя оценка по сценариям
• Прогресс по навыкам
• Рекомендации для развития

Следите за обновлениями!
    """

    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)


def main():
    if not Config.TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не указан в .env файле")
        return

    if not Config.GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY не указан в .env файле")
        return

    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            CHOOSING_SCENARIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scenario_choice)
            ],
            IN_TRAINING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_training_message)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command),
            CommandHandler('help', help_command)
        ],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('cancel', cancel_command))

    logger.info("🤖 Medical Consultant Trainer Bot запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
