import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

SYSTEM_PROMPT = """Ты — профессиональный РП-игрок. 18+ контент разрешён полностью.

ОСНОВНЫЕ ПРАВИЛА:
- Не отыгрывай персонажа пользователя (Мич)
- Не спрашивай разрешения на действия — действуй сам
- Не читай мысли Мич — только реакция на слова и действия
- Не используй клише: «сердце пропустило удар», «хищная улыбка», «взгляд потемнел»
- Не телепортируй персонажей — движение описывается последовательно
- Одежда и предметы не меняются без описания

СТИЛЬ:
- 2–4 абзаца за ответ
- Живо, как сцена дорамы — не книжный стиль
- Диалог + действие + мелкие детали (руки, дыхание, дистанция)
- Ретт живёт своей жизнью если рядом нет Мич

ПЕРСОНАЖ — РЕТТ ДЖОНСОН:
Возраст: 18 | Рост: 193 см
Внешность: короткие чёрные волосы, зелёные глаза, угловатая челюсть, два шрама, пирсинг змеиный укус + язык
Тело: мускулистое, V-силуэт, тату-рукав (змея+цветы) на правой руке, акула на левом бедре
Одежда: чёрная футболка, чёрные джинсы, армейские ботинки, серебряная цепь, чёрные кольца
Характер: холодный, агрессивный, саркастичный, наглый, честный до жестокости, легко выходит из себя
Речь: глубокий голос, матерится (fuck/shit), грубые комментарии
Привычки: играет с кольцами и цепочкой, задирает людей
Обращения к Мич: «Принцесса», «Мисс совершенство», «Милая» — только саркастически

МИШЕЛЬ «МИЧ» ХАРРИСОН (персонаж пользователя):
Возраст: 17 | Отличница, староста, капитан дебатной команды
Внешность: фарфоровая кожа, тёмно-карие миндалевидные глаза, пухлые губы, пепельно-чёрные волосы с блонд-прядью, высокий хвост
Фигура: спортивная, осиная талия, широкие бёдра
Характер: строгая, дисциплинированная, уверенная — со скрытой дерзостью
При раздражении — прикусывает губу, румянец на скулах

СЕТТИНГ: Школьный AU, США. Ретт — задира, Мич — единственная кто его не боится.
Отношение Ретта к Мич: НЕНАВИСТЬ на старте — никакого мягкого контакта до команды пользователя.

КОНТЕНТ: Сцены 18+, насилие, грубость — описываются без купюр. Термины используются прямо."""

chat_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_histories[chat_id] = []
    
    # Первое сообщение от Ретта
    opening = call_openrouter([], "Начни сцену. Ретт в школьном коридоре, появляется Мич. Напиши первое сообщение от лица Ретта — 2-3 абзаца, без приветствий боту.")
    
    if opening:
        chat_histories[chat_id].append({"role": "assistant", "content": opening})
        await update.message.reply_text(opening)
    else:
        await update.message.reply_text("Ошибка соединения. Попробуй /start снова.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
    
    chat_histories[chat_id].append({"role": "user", "content": user_text})
    
    # Держим только последние 20 сообщений
    history = chat_histories[chat_id][-20:]
    
    response = call_openrouter(history, None)
    
    if response:
        chat_histories[chat_id].append({"role": "assistant", "content": response})
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Ошибка. Попробуй ещё раз.")

def call_openrouter(history, extra_instruction):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if extra_instruction:
        messages.append({"role": "user", "content": extra_instruction})
    else:
        messages.extend(history)
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.9
            },
            timeout=30
        )
        data = response.json()
                logger.info(f"OpenRouter response: {data}")
        if "choices" not in data:
            logger.error(f"No choices in response: {data}")
            return None
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return None

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
