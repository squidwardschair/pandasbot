from __future__ import annotations
import random
import discord
from discord.ext import commands
from PIL import Image
import functools
from io import BytesIO
import asyncio
import datetime
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from main import SquidwardBot


class Submit(discord.ui.Modal):
    answer = discord.ui.TextInput(
        label="Wordle Guess Menu", placeholder="Valid 5 letter word...", style=discord.TextStyle.short)

    def __init__(self, words: List[str]):
        super().__init__(title="Wordle Guess")
        self.wait = asyncio.Future()
        self.words = words

    async def on_submit(self, interaction: discord.Interaction):
        if len(self.children[0].value) == 5 and self.children[0].value.lower() in self.words:
            await interaction.response.defer()
            self.wait.set_result(self.children[0].value)
        else:
            await interaction.response.send_message("Not a valid word!", ephemeral=True)
            self.wait.set_result(False)


class WordleView(discord.ui.View):
    def __init__(self, initiator: discord.Member, words: List[str]):
        super().__init__(timeout=365)
        self.initiator = initiator
        self.words = words
        self.result = None
        self.content = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.initiator.id:
            return True

        await interaction.response.send_message(
            "This isn't your Wordle game!", ephemeral=True
        )
        return False

    async def on_timeout(self):
        self.stop()

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.green)
    async def open_modal(self, button: discord.Button, interaction: discord.Interaction):
        modal = Submit(self.words)
        await interaction.response.send_modal(modal)
        try:
            guess = await asyncio.wait_for(modal.wait, timeout=365)
        except asyncio.TimeoutError:
            self.stop()
            return
        if guess is False:
            return
        self.result = guess
        self.stop()

    @discord.ui.button(emoji="🛑", style=discord.ButtonStyle.grey)
    async def deny(self, button: discord.Button, interaction=discord.Interaction):
        self.result = False
        self.stop()

    @discord.ui.button(emoji="❓")
    async def ask(self, button: discord.Button, interaction: discord.Interaction = discord.Interaction):
        await interaction.response.send_message("https://i.gyazo.com/056333baacef7643aadd8189260dde9c.png", ephemeral=True)


class Wordle(commands.Cog, name="Wordle", description="Wordle! Guess the 5 letter word in 6 tries, using the hints given to you :). A random Wordle from the past (not todays), will be selected for you to solve. Type your guess into the chat, but make sure its a valid 5 letter word. Use the help button if you don't know how to play. Happy wordling!"):
    def __init__(self, bot):
        self.bot: SquidwardBot = bot

    def do_word(self, words: List[str], checkword: str, board: Image.Image):
        if not words:
            return board
        for wi, word in enumerate(words):
            y = 30+(92*wi)
            yellows = []
            greens = []
            for ci, c in enumerate(word):
                x = 20+(95*ci)
                if c == checkword[ci]:
                    color = 'green'
                    yellows.append(c)
                    greens.append(ci)
                    img = Image.open(f'gamedata/wordleimgs/{color}-{c}.png')
                    board.paste(img, (x, y))
            for yi, yel in enumerate(word):
                x = 20+(95*yi)
                if yi in greens:
                    continue
                if yel in checkword and yellows.count(yel) < checkword.count(yel):
                    yellows.append(yel)
                    color = 'yellow'
                else:
                    color = "grey"
                img = Image.open(f'gamedata/wordleimgs/{color}-{yel}.png')
                board.paste(img, (x, y))
        return board

    async def wordle_word(self, word: str, checkword: str, board: Image.Image):
        thing = functools.partial(self.do_word, word, checkword, board)
        some_stuff = await self.bot.loop.run_in_executor(None, thing)

        return some_stuff

    def word_emoji(self, word: str, checkword: str):
        line = [None, None, None, None, None]
        yellows = []
        greens = []
        for ci, c in enumerate(word):
            if c == checkword[ci]:
                yellows.append(c)
                greens.append(ci)
                line[ci] = "🟩"
        for yi, yel in enumerate(word):
            if yi in greens:
                continue
            if yel in checkword and yellows.count(yel) < checkword.count(yel):
                yellows.append(yel)
                line[yi] = "🟨"
            else:
                line[yi] = "⬛"
        return "> "+"".join(line)

    def all_emoji(self, lines: List[str], date: int, win=None):
        if not lines:
            return None
        boxes = "\n".join(lines)
        return f"> Wordle {date+1} {'X' if len(lines)==6 and win==False else len(lines)}/6\n> \n{boxes}\n\n"

    def create_keyboard(self, usedletters: list):
        qwerty = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
        emojis = ""
        for i, row in enumerate(qwerty):
            if i == 2:
                emojis += "⬛"
            for l in row:
                emojis += "⬛" if l in usedletters else f":regional_indicator_{l}:"
            if i == 2:
                emojis += "⬛"
            emojis += "\n"
        return emojis

    async def create_embed(self, ctx: commands.Context, board: Image.Image, emojis: str, theword: str, keyboard: str, win=None):
        buffer = BytesIO()
        board.save(buffer, "PNG")
        buffer.seek(0)
        embedimage = discord.File(fp=buffer, filename="image.png")
        winmsg = ":white_check_mark: Awesome wordling." if win is True else f":x: Awww. The correct word was **{theword}**."
        if win is None:
            winmsg = "Make sure your guess is a valid 5 letter word!"
        embed = discord.Embed(title="Wordle (discord bot edition)",
                              description=f"Guess the Wordle in 6 tries.\n\n{keyboard}\n{emojis if emojis is not None else ''}{winmsg}", color=discord.Color.dark_blue())
        embed.set_image(url="attachment://image.png")
        embed.set_footer(text=f"{ctx.author}'s Wordle")
        return embed, embedimage

    async def wait_for_word(self, ctx: commands.Context, view: WordleView):
        await view.wait()
        if view.result is not False and view.result is not None:
            return view.result
        await ctx.reply(f"Wordle {'cancelled' if view.result is False else 'timed out'}.")
        await self.bot.db.execute("DELETE FROM wordle WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id)
        return False

    def get_wordle_date(self):
        today = datetime.date.today()
        thatdate = datetime.date(2021, 6, 21)
        delta: datetime.timedelta = today-thatdate
        return delta.days

    async def check_db(self, ctx: commands.Context):
        if await self.bot.db.fetchval("SELECT * FROM wordle WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id):
            await ctx.send("You're already playing Wordle in this channel!")
            return False
        return True

    @commands.command(
        name="wordle",
        help="Starts a game of Wordle with a random word being selected each time.",
        brief="Starts a game of Wordle",
    )
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def wordle(self, ctx: commands.Context):
        if await self.check_db(ctx) is False:
            return
        await self.bot.db.execute("INSERT INTO wordle VALUES($1, $2);", ctx.author.id, ctx.channel.id)
        wordledate = self.get_wordle_date()
        rand = random.randrange(0, wordledate)
        theword = self.bot.wordleanswers[rand]
        board = Image.open("gamedata/wordleimgs/board.png")
        words = []
        emojilines = []
        letters = []
        guess = None
        for i in range(7):
            board = await self.wordle_word(words, theword, board)
            emoji = self.all_emoji(emojilines, rand, win=guess == theword)
            keyboard = self.create_keyboard(letters)
            embed, boardimg = await self.create_embed(ctx, board, emoji, theword, keyboard)
            view = WordleView(ctx.author, self.bot.wordlewords)
            if guess == theword:
                break
            if i == 6:
                break
            message: discord.Message = await ctx.send(embed=embed, file=boardimg, view=view)
            guess = await self.wait_for_word(ctx, view)
            await message.delete()
            if guess is False:
                return
            for l in guess:
                if l not in letters:
                    letters.append(l)
            words.append(guess)
            emojilines.append(self.word_emoji(guess, theword))
        embed, boardimg = await self.create_embed(ctx, board, emoji, theword, keyboard, win=guess == theword)
        await ctx.send(embed=embed, file=boardimg)
        await self.bot.db.execute("DELETE FROM wordle WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id)


async def setup(bot: SquidwardBot):
    await bot.add_cog(Wordle(bot))
