"""
Telegram-бот AI-компаньона.

Флоу:
1. /start -> мастер настройки персонажа (имя, возраст, пол/тип, характер, голос, аватар)
2. После настройки — обычный диалог: пользователь пишет текст, бот отвечает
   текстом + голосовым сообщением (TTS)
3. /reset — начать настройку заново
4. /profile — посмотреть текущие настройки персонажа

Персонаж — полностью вымышленный, не имитирует реальных людей (см. ai.py).
"""

import asyncio
import logging
import os
import tempfile

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

import database
import ai

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class SetupStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_personality = State()
    waiting_voice = State()
    waiting_avatar = State()


# ---------- Клавиатуры ----------

def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Парень", callback_data="gender:парень")],
        [InlineKeyboardButton(text="Девушка", callback_data="gender:девушка")],
        [InlineKeyboardButton(text="Энергичный блогер-вайб", callback_data="gender:блогер-вайб")],
        [InlineKeyboardButton(text="Спокойный стример-вайб", callback_data="gender:стример-вайб")],
    ])


def personality_keyboard() -> InlineKeyboardMarkup:
    options = [
        ("Заботливый(ая)", "заботливый, поддерживающий, внимательный"),
        ("Дерзкий(ая)", "дерзкий, ироничный, с подколками"),
        ("Энергичный(ая)", "энергичный, эмоциональный, много восклицаний"),
        ("Спокойный(ая)", "спокойный, рассудительный, немногословный"),
        ("Саркастичный(ая)", "саркастичный, остроумный, с чёрным юмором"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"personality:{value}")]
        for label, value in options
    ])


def voice_keyboard() -> InlineKeyboardMarkup:
    options = [
        ("Мужской спокойный", "male_calm"),
        ("Мужской энергичный", "male_energetic"),
        ("Женский спокойный", "female_calm"),
        ("Женский энергичный", "female_energetic"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"voice:{value}")]
        for label, value in options
    ])


# ---------- Мастер настройки ----------

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    persona = database.get_persona(message.from_user.id)
    if persona and persona["setup_complete"]:
        await message.answer(
            f"С возвращением! Твой собеседник {persona['name']} на месте 🙂\n"
            "Пиши что угодно — отвечу текстом и голосом.\n"
            "Команда /reset — настроить персонажа заново."
        )
        return

    await state.set_state(SetupStates.waiting_name)
    await message.answer(
        "Привет! Давай настроим твоего собеседника.\n\n"
        "Как его/её зовут?"
    )


@dp.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    await state.set_state(SetupStates.waiting_name)
    await message.answer("Настраиваем персонажа заново. Как его/её зовут?")


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    persona = database.get_persona(message.from_user.id)
    if not persona or not persona["setup_complete"]:
        await message.answer("Персонаж ещё не настроен. Напиши /start.")
        return
    await message.answer(
        f"Имя: {persona['name']}\n"
        f"Возраст: {persona['age']}\n"
        f"Тип: {persona['gender']}\n"
        f"Характер: {persona['personality']}\n"
        f"Голос: {persona['voice']}"
    )


@dp.message(SetupStates.waiting_name)
async def set_name(message: Message, state: FSMContext):
    database.upsert_persona(message.from_user.id, name=message.text.strip())
    await state.set_state(SetupStates.waiting_age)
    await message.answer("Сколько лет персонажу? (укажи число, 18+)")


@dp.message(SetupStates.waiting_age)
async def set_age(message: Message, state: FSMContext):
    age_text = message.text.strip()
    if not age_text.isdigit() or int(age_text) < 18:
        await message.answer("Укажи возраст числом, 18 или больше.")
        return
    database.upsert_persona(message.from_user.id, age=age_text)
    await state.set_state(SetupStates.waiting_gender)
    await message.answer("Выбери тип персонажа:", reply_markup=gender_keyboard())


@dp.callback_query(F.data.startswith("gender:"))
async def set_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split(":", 1)[1]
    database.upsert_persona(callback.from_user.id, gender=gender)
    await state.set_state(SetupStates.waiting_personality)
    await callback.message.answer("Какой характер?", reply_markup=personality_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("personality:"))
async def set_personality(callback: CallbackQuery, state: FSMContext):
    personality = callback.data.split(":", 1)[1]
    database.upsert_persona(callback.from_user.id, personality=personality)
    await state.set_state(SetupStates.waiting_voice)
    await callback.message.answer("Выбери голос для голосовых ответов:", reply_markup=voice_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("voice:"))
async def set_voice(callback: CallbackQuery, state: FSMContext):
    voice = callback.data.split(":", 1)[1]
    database.upsert_persona(callback.from_user.id, voice=voice)
    await state.set_state(SetupStates.waiting_avatar)
    await callback.message.answer(
        "Последний шаг — пришли картинку для аватарки персонажа "
        "(или напиши /skip, чтобы пропустить)."
    )
    await callback.answer()


@dp.message(SetupStates.waiting_avatar, F.photo)
async def set_avatar(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    database.upsert_persona(
        message.from_user.id, avatar_file_id=file_id, setup_complete=1
    )
    await state.clear()
    persona = database.get_persona(message.from_user.id)
    await message.answer(
        f"Готово! {persona['name']} настроен(а) и готов(а) общаться 🙂\n"
        "Просто пиши сообщения."
    )


@dp.message(SetupStates.waiting_avatar, Command("skip"))
async def skip_avatar(message: Message, state: FSMContext):
    database.upsert_persona(message.from_user.id, setup_complete=1)
    await state.clear()
    persona = database.get_persona(message.from_user.id)
    await message.answer(
        f"Готово! {persona['name']} настроен(а) и готов(а) общаться 🙂\n"
        "Просто пиши сообщения."
    )


# ---------- Основной диалог ----------

@dp.message(F.text)
async def chat_handler(message: Message, state: FSMContext):
    # Если пользователь ещё в процессе настройки — эти сообщения обработают
    # хендлеры выше по стейту, сюда попадает только "обычный" диалог
    current_state = await state.get_state()
    if current_state is not None:
        return

    persona = database.get_persona(message.from_user.id)
    if not persona or not persona["setup_complete"]:
        await message.answer("Сначала настрой персонажа: /start")
        return

    await bot.send_chat_action(message.chat.id, "typing")

    history = database.get_recent_history(message.from_user.id)
    reply_text = ai.generate_reply(persona, history, message.text)

    database.save_message(message.from_user.id, "user", message.text)
    database.save_message(message.from_user.id, "assistant", reply_text)

    await message.answer(reply_text)

    # Генерируем голосовое сообщение
    await bot.send_chat_action(message.chat.id, "record_voice")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        voice_path = tmp.name
    try:
        await ai.synthesize_voice(reply_text, persona["voice"], voice_path)
        await message.answer_voice(FSInputFile(voice_path))
    except Exception as e:
        logging.error(f"TTS error: {e}")
    finally:
        if os.path.exists(voice_path):
            os.remove(voice_path)


async def main():
    database.init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
