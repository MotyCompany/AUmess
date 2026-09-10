"""
Telegram-бот: уведомляет о всплеске онлайна на сервере SCP:SL.

Источник данных: публичный API gamemonitoring.ru
https://api.gamemonitoring.ru/servers/{SERVER_ID}

Логика: проверяет кол-во игроков раз в CHECK_INTERVAL секунд.
Уведомление отправляется один раз при ПЕРЕХОДЕ через порог
(было меньше PLAYER_THRESHOLD -> стало больше или равно), чтобы
бот не спамил одним и тем же сообщением на каждой проверке.
"""

import asyncio
import logging

import aiohttp
from telegram import Bot
from telegram.error import TelegramError

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"        # получить у @BotFather
CHAT_ID = "ВАШ_CHAT_ID"              # куда слать уведомления (id чата/канала/себя)
SERVER_ID = 13962969                 # id сервера на gamemonitoring.ru
API_URL = f"https://api.gamemonitoring.ru/servers/{SERVER_ID}"
CHECK_INTERVAL = 300                 # 5 минут
PLAYER_THRESHOLD = 3                 # уведомлять, если игроков >= 3 (то есть "более 2х")
# =====================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scpsl-notifier")


async def fetch_server_info(session: aiohttp.ClientSession):
    try:
        async with session.get(API_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("response")
    except Exception as e:
        log.warning("Не удалось получить данные с API: %s", e)
        return None


def format_message(info: dict) -> str:
    name = info.get("name") or "SCP:SL сервер"
    players = info.get("numplayers", "?")
    max_players = info.get("maxplayers", "?")
    return (
        f"🚨 На сервере оживление!\n\n"
        f"🖥 {name}\n"
        f"👥 Игроков: {players}/{max_players}"
    )


async def main():
    bot = Bot(token=BOT_TOKEN)
    above_threshold = False  # флаг: уже уведомляли про текущий всплеск или нет

    async with aiohttp.ClientSession() as session:
        log.info("Бот запущен. Проверка каждые %s сек, порог: %s игроков.", CHECK_INTERVAL, PLAYER_THRESHOLD)
        while True:
            info = await fetch_server_info(session)
            if info is not None:
                players = info.get("numplayers", 0) or 0

                if players >= PLAYER_THRESHOLD and not above_threshold:
                    above_threshold = True
                    try:
                        await bot.send_message(chat_id=CHAT_ID, text=format_message(info))
                        log.info("Уведомление отправлено (%s игроков)", players)
                    except TelegramError as e:
                        log.error("Ошибка отправки в Telegram: %s", e)

                elif players < PLAYER_THRESHOLD and above_threshold:
                    above_threshold = False
                    log.info("Игроков стало меньше порога (%s)", players)

            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
