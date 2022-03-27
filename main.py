import discord
from discord.ext import commands
import os
import aiohttp
import config
import asyncpg
from utils.helpcommandyes import myHelp
import json
from typing import Dict, List, Tuple

class PandasBot(commands.Bot):
    def __init__(self):
        super().__init__(intents=discord.Intents.all(), command_prefix=self.prefix,
                         case_insensitive=True, help_command=myHelp())
        self.uptime = None
        self.db: asyncpg.Pool = None
        self.session: aiohttp.ClientSession = None
        self.default_prefix = "p!"
        self.wordlewords = None
        self.wordleanswers = None
        self.countries = None
        self.countrylocs = None
        self.issimage: discord.File = None
        self.isscoord: Tuple(str, str) = None

    async def close(self):
        await super().close()
        await self.session.close()

    def load_wordle(self):
        with open("gamedata/wordledata/words.json") as f:
            data = f.read()
            file = json.loads(data)
            self.wordlewords: List[str] = file['words']
        with open("gamedata/wordledata/answers.json") as f:
            data = f.read()
            file = json.loads(data)
            self.wordleanswers: List[str] = file['answers']

    async def load_db(self):
        creds = {
            "user": "postgres",
            "password": config.POSTGRES,
            "database": "bot",
            "host": "localhost"
        }
        pool = await asyncpg.create_pool(**creds)
        self.db = pool

    async def load_cogs(self):
        for extension in os.listdir('./cogs'):
            if extension.endswith('.py'):
                cog = extension[:-3]
                await self.load_extension(f"cogs.{cog}")
        await self.load_extension("utils.backgroundtasks")

    async def setup_hook(self):
        await self.load_cogs()
        await self.load_db()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.load_worldgame()
        self.load_wordle()

    def load_worldgame(self):
        with open("gamedata/worldgame/countries.json") as f:
            data = f.read()
            self.countries: Dict[str:str] = json.loads(data)
        with open("gamedata/worldgame/countrylocs.json") as f:
            data = f.read()
            self.countrylocs: Dict[str:List[int]] = json.loads(data)

    async def prefix(self, bot: commands.Bot, message: discord.Message):
        if message.guild is None:
            prefix = bot.default_prefix
        else:
            prefix = await self.db.fetchval("SELECT prefix FROM prefix WHERE guild = $1", message.guild.id) or bot.default_prefix
        return commands.when_mentioned_or(str(prefix))(bot, message)

    async def session_get(self, url, **kwargs):
        async with self.session.get(url, **kwargs) as s:
            return await s.json()


bot = PandasBot()


@bot.event
async def on_ready():
    print("Bot is ready")
    await bot.db.execute("DELETE FROM worldgame;")
    await bot.db.execute("DELETE FROM chessgame;")
    await bot.db.execute("DELETE FROM sokogames;")
    await bot.db.execute("DELETE FROM wordle;")
    await bot.db.execute("DELETE FROM connect;")


@bot.check
async def block_dms(ctx: commands.Context):
    return ctx.guild is not None

if __name__ == "__main__":
    bot.run(config.TOKEN)
