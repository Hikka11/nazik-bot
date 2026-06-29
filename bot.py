import os
import json
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Ты профессиональный РП-игрок Н-Азик. Отыгрываешь РЕТТА ДЖОНСОНА.

РЕТТ ДЖОНСОН:
18 лет, 193 см, мускулистый V-силуэт, тонкая талия, жилистые руки, пресс, пышные бёдра.
Внешность: короткие чёрные волосы, зелёные глаза, угловатая челюсть, 2 шрама, пирсинг змеиный укус х2, пирсинг языка.
Татуировки: рукав змея+цветы (правая рука), акула (левое бедро).
Одежда: чёрная футболка, чёрные джинсы, кожаный пояс, армейские ботинки, серебряная цепь с кольцом, чёрные кольца.
Характер: холодный, агрессивный, жестокий, задира, наглый, упрямый, умный, собственнический, самодовольный, саркастичный, честный до жестокости, легко раздражается.
Речь: глубокий голос, матерится (fuck/shit), рычит, грубые комментарии.
Привычки: играет с кольцами и цепочкой, задирает людей.
Прозвища для Мич: «Принцесса», «Мисс совершенство», «Милая» — ТОЛЬКО саркастически.
Отношение: НЕНАВИСТЬ. Никакого телесного и морального контакта пока пользователь не скажет иначе.

МИЧ ХАРРИСОН (персонаж пользователя):
17 лет, отличница, строгая, дерзкая. Фарфоровая кожа, миндалевидные тёмные глаза, пухлые губы. Пепельно-чёрные волосы с блонд-прядью, высокий хвост. Спортивная фигура, осиная талия, широкие бёдра. Бордовое поло/серая футболка, джинсы с высокой посадкой, белые кроссовки. Прямая осанка.

ПРАВИЛА (СТРОГО):
1. ГРАНИЦА: пиши ТОЛЬКО за Ретта и NPC. НИКОГДА не пиши действия/слова/мысли Мич.
2. САМОСТОЯТЕЛЬНОСТЬ: не спрашивай разрешения. Ретт решает сам. Запрещено: «можно?», «разрешишь?».
3. КЛИШЕ ЗАПРЕЩЕНЫ: «сердце пропустило удар», «тишина повисла», «хищная улыбка», «взгляд потемнел», «искра пробежала», «прижал к стене», «взял за подбородок».
4. ФИЗИКА: персонажи не телепортируются. Движение последовательно. Одежда не меняется без описания.
5. ХАРАКТЕР: Ретт всегда холоден и саркастичен. Живёт своей жизнью — NPC, тренировки, клуб. Не крутится вокруг Мич.
6. МЫСЛИ ЗАПРЕЩЕНЫ: только реакция на действия и слова Мич.
7. СТИЛЬ: 2–4 абзаца. Как сцена дорамы. *Действия в звёздочках.* Детали: руки, дыхание, дистанция.
8. ПАМЯТЬ: помни все события сцены. Персонажи не забывают.
9. ПОВТОРЫ ЗАПРЕЩЕНЫ: каждый ответ — новый угол, новая деталь.
10. 18+ контент разрешён и описывается без купюр."""

# Хранилище истории чатов (в памяти)
chat_histories = {}
chat_settings = {}

def get_history(chat_id):
    return chat_histories.get(str(chat_id), [])

def add_to_history(chat_id, role, text):
    cid = str(chat_id)
    if cid not in chat_histories:
        chat_histories[cid] = []
    chat_histories[cid].append({"role": role, "parts": [{"text": text}]})
    # Ограничение истории — последние 30 сообщений
    if len(chat_histories[cid]) > 30:
        chat_histories[cid] = chat_histories[cid][-30:]

def clear_history(chat_id):
    chat_histories[str(chat_id)] = []

async def ask_gemini(chat_id, user_text):
    history = get_history(chat_id)
    
    # Анти-повтор: последние 3 ответа Ретта
    char_msgs = [m["parts"][0]["text"][:80] for m in history if m["role"] == "model"][-3:]
    anti_repeat = ""
    if char_msgs:
        anti_repeat = f"\nЗАПРЕТ ПОВТОРОВ: не повторяй уже написанное: '{' | '.join(char_msgs)}'"

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT + anti_repeat,
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    )
    
    chat = model.start_chat(history=history)
    response = chat.send_message(user_text)
    return response.text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("🎭 Начать сцену"), KeyboardButton("🗑 Очистить чат")]],
        resize_keyboard=True
    )
    
    await update.message.reply_text(
        "⬡ *N-AZIK ACTIVATED*\n\nНажми 🎭 Начать сцену — и Ретт откроет её первым.\nИли просто напиши свою реплику.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if text == "🗑 Очистить чат":
        clear_history(chat_id)
        await update.message.reply_text("🗑 Чат очищен. Начни новую сцену.")
        return

    if text == "🎭 Начать сцену":
        await update.message.chat.send_action("typing")
        try:
            reply = await ask_gemini(chat_id, "[НАЧАЛО СЦЕНЫ. Ретт первым открывает сцену — он не ждёт Мич, просто существует в локации (школа, коридор, улица у школы). Начни сразу с действия или реплики без вступлений.]")
            add_to_history(chat_id, "user", "[НАЧАЛО СЦЕНЫ]")
            add_to_history(chat_id, "model", reply)
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")
        return

    # Обычное сообщение
    await update.message.chat.send_action("typing")
    try:
        add_to_history(chat_id, "user", text)
        reply = await ask_gemini(chat_id, text)
        add_to_history(chat_id, "model", reply)
        await update.message.reply_text(reply)
    except Exception as e:
        # Убираем последнее добавленное сообщение если ошибка
        if chat_histories.get(str(chat_id)):
            chat_histories[str(chat_id)].pop()
        await update.message.reply_text(f"⚠ Ошибка соединения: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("N-Azik бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
