#Telegram BOT API - HTTPS API

import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

load_dotenv()


def load_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if token:
        return token.strip()
    raise RuntimeError("Не найден Токен бота, добавьте в .env")


dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {name}! Я учебный бот на aiogram.\n"
        "Напишите любое сообщение - и отвечу. Команда /help покажет подсказку."
    )


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer("Доступные команды:\n/start - начать\n/help - помощь")


@dp.message()
async def echo_handler(message: Message) -> None:
    if message.text:
        await message.answer(f"Получил текст: {message.text}")
    else:
        await message.answer("Пока на чилле, на расслабоне, умею отвечать только текстовые сообщения.")


async def main() -> None:
    bot = Bot(token=load_token())
    async with bot:
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
