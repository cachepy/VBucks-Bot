import asyncio
import os

from tortoise import Tortoise
from lib.bot import ErrorBot
import logging
import config

formatter = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


async def main():
    try:
        bot = ErrorBot()
        bot._load_extensions("lib.cogs")
        await bot.db_init()
        await bot.start(config.TOKEN, reconnect=True)

    except KeyboardInterrupt:
        await Tortoise.close_connections()
        await asyncio.sleep(1)
        os._exit(0)
    
    except Exception as e:
        logging.error(e)
        await Tortoise.close_connections()
        await asyncio.sleep(1)
        os._exit(0)
    
    finally:
        await Tortoise.close_connections()
        await asyncio.sleep(1)
        os._exit(0)

asyncio.run(main())
