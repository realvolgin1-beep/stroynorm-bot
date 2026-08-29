import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.answers import answer_question
from app.catalog import (
    catalog_overview,
    catalog_sources,
    catalog_summary,
    documents,
    format_catalog_hits,
    format_no_results,
    search_catalog,
)
from app.config import Settings
from app.search import search

logger = logging.getLogger(__name__)
router = Router()

MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Найти норму"), KeyboardButton(text="📚 Документы")],
        [KeyboardButton(text="🌉 Мосты"), KeyboardButton(text="🛣 Дороги и знаки")],
        [KeyboardButton(text="📐 Допуски и контроль"), KeyboardButton(text="🧱 Покрытия")],
        [KeyboardButton(text="🏗 Общестрой"), KeyboardButton(text="🔥 Пожарные нормы")],
        [KeyboardButton(text="🔧 Инженерные системы"), KeyboardButton(text="🔗 Источники")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)

WELCOME = (
    "Здравствуйте! Я «СтройНорм РФ» — справочник по СП, ГОСТам и документам Росавтодора.\n\n"
    "Приоритетные темы: дороги, мосты и общестроительные нормы. "
    "Бесплатный гибридный поиск понимает обычные вопросы, склонения и частые опечатки."
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
        "Укажите объект, вид работ и нужный параметр. Например:\n"
        "• допустимое отклонение пролётного строения;\n"
        "• требования к опорным частям моста;\n"
        "• высота и боковое расстояние дорожного знака;\n"
        "• контроль ровности и поперечного уклона дороги;\n"
        "• устройство монолитных железобетонных конструкций;\n"
        "• ширина эвакуационного выхода.\n\n"
        "Ответ содержит документ, пункт и страницу, если они есть в загруженном официальном тексте."
    )


@router.message(F.text == "🔎 Найти норму")
@router.message(Command("search"))
async def find_prompt(message: Message) -> None:
    await message.answer(
        "Напишите обозначение или вопрос — платный API для поиска не нужен. Например:\n"
        "• СП 35.13330\n• ГОСТ по обследованию мостов\n"
        "• допустимое отклонение поперечного уклона дороги\n"
        "• установка временных знаков при ремонте"
    )


@router.message(Command("documents"))
@router.message(F.text == "📚 Документы")
async def about_database(message: Message) -> None:
    await message.answer(catalog_overview())


@router.message(Command("sources"))
@router.message(F.text == "🔗 Источники")
async def sources(message: Message) -> None:
    await message.answer(catalog_sources())


@router.message(Command("stats"))
async def stats(message: Message) -> None:
    await message.answer(
        f"В проверенном реестре: {len(documents())} документов. "
        "Поиск: бесплатный локальный гибридный — ключ OpenAI не требуется."
    )


@router.message(F.text == "🌉 Мосты")
async def bridges(message: Message) -> None:
    await message.answer(catalog_summary("bridges"))


@router.message(F.text == "🛣 Дороги и знаки")
async def roads(message: Message) -> None:
    await message.answer(catalog_summary("roads") + "\n\n" + catalog_summary("traffic"))


@router.message(F.text == "📐 Допуски и контроль")
async def measurements(message: Message) -> None:
    await message.answer(catalog_summary("measurements") + "\n\n" + catalog_summary("acceptance"))


@router.message(F.text == "🧱 Покрытия")
async def pavement(message: Message) -> None:
    await message.answer(catalog_summary("pavement"))


@router.message(F.text == "🏗 Общестрой")
async def general_construction(message: Message) -> None:
    await message.answer(catalog_summary("organization"))
    await message.answer(catalog_summary("structures"))
    await message.answer(catalog_summary("geotechnics"))


@router.message(F.text == "🔥 Пожарные нормы")
async def fire_safety(message: Message) -> None:
    await message.answer(catalog_summary("fire"))


@router.message(F.text == "🔧 Инженерные системы")
async def engineering(message: Message) -> None:
    await message.answer(catalog_summary("engineering"))


@router.message(F.text)
async def question(message: Message, settings: Settings) -> None:
    text = (message.text or "").strip()
    catalog_hits = search_catalog(text)
    if len(text) < 8 and catalog_hits:
        await message.answer(format_catalog_hits(catalog_hits))
        return
    if len(text) < 4:
        await message.answer("Введите обозначение документа или более подробный вопрос.")
        return
    waiting = await message.answer("Ищу по словам, смысловым темам и обозначениям документов…")
    try:
        hits = await asyncio.to_thread(search, settings.database_path, text)
        if not hits:
            response = format_catalog_hits(catalog_hits) if catalog_hits else format_no_results(text)
        else:
            response = await answer_question(settings.openai_api_key, settings.openai_model, text, hits)
        await waiting.edit_text(response)
    except Exception:
        logger.exception("Failed to answer question")
        await waiting.edit_text("Не удалось обработать запрос. Попробуйте ещё раз немного позже.")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Отправьте вопрос текстовым сообщением.")
