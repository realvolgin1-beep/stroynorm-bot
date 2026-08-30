import logging
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from app.bot import create_dispatcher
from app.catalog import catalog_scope_count, documents
from app.config import get_settings
from app.requirements import requirement_values_count

logging.basicConfig(level=logging.INFO)
settings = get_settings()
bot = Bot(token=settings.telegram_bot_token)
dispatcher = create_dispatcher(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.effective_public_url:
        webhook_url = f"{settings.effective_public_url.rstrip('/')}/telegram/webhook"
        await bot.set_webhook(webhook_url, secret_token=settings.webhook_secret or None)
    yield
    await bot.session.close()


app = FastAPI(title="СтройНорм РФ", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "documents": len(documents()),
        "searchable_scopes": catalog_scope_count(),
        "requirements": requirement_values_count(),
        "search": "local-hybrid-grounded",
        "answer_model": settings.openai_model,
        "release": "2026-08-30-luna",
    }


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dispatcher.feed_update(bot, update)
    return {"ok": True}
