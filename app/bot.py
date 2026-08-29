import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.answers import answer_question
from app.config import Settings
from app.search import search

logger = logging.getLogger(__name__)
router = Router()

MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Найти норму"), KeyboardButton(text="📚 О базе")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)

WELCOME = (
    "Здравствуйте! Я «СтройНорм РФ» — справочник по строительным СП и ГОСТам России.\n\n"
    "Задайте вопрос обычным сообщением. Я найду релевантные нормы в загруженной базе и укажу источники."
)


def create_dispatcher(settings: Settings) -> Dispatcher:
    dispatcher = Dispatcher(settings=settings)
    dispatcher.include_router(router)
    return dispatcher


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=MENU)


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def help_message(message: Message) -> None:
    await message.answer(
        "Сформулируйте вопрос и добавьте контекст: тип здания, назначение помещения, этажность и нужный параметр. "
        "Например: «Минимальная ширина эвакуационного выхода из офисного помещения на 80 человек»."
    )


@router.message(F.text == "🔎 Найти норму")
async def find_prompt(message: Message) -> None:
    await message.answer("Напишите, какую строительную норму нужно найти.")


@router.message(F.text == "📚 О базе")
async def about_database(message: Message, settings: Settings) -> None:
    hits = search(settings.database_path, "строительство", limit=1)
    status = "База подключена." if hits else "Нормативные документы пока не загружены."
    await message.answer(f"{status}\nОтветы формируются только по проиндексированным документам.")


@router.message(F.text)
async def question(message: Message, settings: Settings) -> None:
    text = (message.text or "").strip()
    if len(text) < 8:
        await message.answer("Пожалуйста, сформулируйте вопрос подробнее.")
        return
    waiting = await message.answer("Ищу норму в базе…")
    try:
        hits = await asyncio.to_thread(search, settings.database_path, text)
        response = await answer_question(settings.openai_api_key, settings.openai_model, text, hits)
        await waiting.edit_text(response)
    except Exception:
        logger.exception("Failed to answer question")
        await waiting.edit_text("Не удалось обработать запрос. Попробуйте ещё раз немного позже.")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Отправьте вопрос текстовым сообщением.")
