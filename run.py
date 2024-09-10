import os, dotenv

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ( ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters)

from src.llm import LLMProcessor
from src.tts import TTSProcessor
from src.asr import ASRProcessor
  
# load global variables from local .env file
dotenv.load_dotenv()
llm, tts, asr = None, None, None

# globally accessed objects
def init_processors():
    global llm, tts, asr
    llm = LLMProcessor(os.environ.get("PROMPT_PATH"), os.environ.get("RAG_PATH"))
    tts = TTSProcessor(os.environ.get("AUDIO_PATH"))
    asr = ASRProcessor()

output_mode = "voice"
markup = ReplyKeyboardMarkup( [["audio", "text", "voice"]], one_time_keyboard=True)

def get_name(update: Update):
    user_name = update.message.from_user.first_name
    if len(user_name) == 0:
        user_name = update.message.from_user.username
    if len(user_name) == 0:
        user_name = "Дорогой друг!"
    return user_name

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = get_name(update)
    llm.set_engine(user_name)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Здравствуйте, {user_name}. ")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = get_name(update)
    llm.set_engine(user_name, reset=True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Здравствуйте, {user_name}. ")

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = get_name(update)
    llm.save_context(user_name)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Контекст для {user_name} сохранён.")

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE, override_message=None):
    global output_mode
    answer = llm.process_prompt(override_message if override_message is not None else update.message.text, get_name(update))
    
    if output_mode == "text":
        await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    else:
        audio_name = tts.get_audio(answer, format=".wav" if output_mode == "audio" else ".ogg")
        if output_mode == "audio":
            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_name, 'rb'))
        else:
            await context.bot.send_voice(chat_id=update.effective_chat.id, voice=open(audio_name, 'rb'))
        os.remove(audio_name)

async def audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global output_mode
    print(f"Entered audio, got message {update.message}")
     # get basic info about the voice note file and prepare it for downloading
    if update.message.voice is not None:
        file_to_process = f"voice_note.ogg"
        file_id = update.message.voice.file_id
    elif update.message.audio is not None:
        file_to_process = f"voice_note.mp3"
        file_id = update.message.audio.file_id
    elif update.message.document is not None:
        if update.message.document.mime_type == 'audio/x-wav':
            file_to_process = f"voice_note.wav"
            file_id = update.message.document.file_id

    print(f"Loading {file_id} to {file_to_process}")
    new_file = await context.bot.get_file(file_id)
    await new_file.download_to_drive(file_to_process)
    print(f"Loaded {file_id} to {file_to_process}")
    # decode audio message using whisper and pass it to llm
    user_message = asr.get_text(file_to_process)
    os.remove(file_to_process)
    
    if len(user_message) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Прошу прощения, не расслышал.")
        return
    # await context.bot.send_message(chat_id=update.effective_chat.id, text="Расшифровал сообщение:" + user_message)
    print("Расшифровал сообщение:" + user_message)

    await message(update, context, user_message)


async def set_output(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начvало разговора, просьба ввести данные."""
    await update.message.reply_text("Задай значение переменной", reply_markup=markup)
    return 0

async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос информации о выбранном предопределенном выборе."""
    global output_mode
    output_mode = update.message.text
    await update.message.reply_text(f"Изменён тип вывода: {output_mode}", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Done!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get('BOT_TOKEN')).build()

    init_processors()
    
    start_handler = CommandHandler('start', start)
    reset_handler = CommandHandler('reset', reset)
    save_handler = CommandHandler('save', save)
  
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), message)
    voice_handler = MessageHandler(filters.VOICE, audio)
    audio_handler = MessageHandler(filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE | filters.ATTACHMENT, audio)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_output", set_output)],
        states={0: [MessageHandler(filters.Regex("^(audio|text|voice)$"), regular_choice),],},
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(reset_handler)
    application.add_handler(save_handler)
    application.add_handler(message_handler)
    application.add_handler(voice_handler)
    application.add_handler(audio_handler)

    application.run_polling()
