from __future__ import annotations
import asyncio
from math import atan2, pi, radians, degrees, sin, cos
from geopy import distance
from difflib import get_close_matches
import discord
from discord.ext import commands
from typing import List, Dict, Tuple, TYPE_CHECKING
import random
from utils.voteutils import random_vote
if TYPE_CHECKING:
    from main import PandasBot


class Submit(discord.ui.Modal):
    answer = discord.ui.TextInput(
        label="Worldle Guess", placeholder="Country, territory...", style=discord.TextStyle.short)

    def __init__(self, countries: Dict[str]):
        super().__init__(title="Worldle Guess Menu")
        self.wait = asyncio.Future()
        self.countries = countries

    async def on_submit(self, interaction: discord.Interaction):
        if matches := get_close_matches(self.children[0].value.title(), list(self.countries)):
            guessview = GuessView(matches, interaction.user)
            await interaction.response.send_message("Make your guess", view=guessview, ephemeral=True)
            await guessview.wait()
            if guessview.result is None:
                self.wait.set_result(False)
                return
            self.wait.set_result(guessview.result)
        else:
            await interaction.response.send_message("Not a valid country!", ephemeral=True)
            self.wait.set_result(False)


class WorldleView(discord.ui.View):
    def __init__(self, countries: Dict[str], initiator: discord.Member):
        super().__init__(timeout=360)
        self.countries = countries
        self.initiator = initiator
        self.guess = None
        self.cancel = False

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.green)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = Submit(self.countries)
        await interaction.response.send_modal(modal)
        try:
            guess = await asyncio.wait_for(modal.wait, timeout=60)
        except asyncio.TimeoutError:
            self.stop()
            return
        if guess is False:
            return
        self.guess = guess
        self.stop()

    @discord.ui.button(emoji="🛑", style=discord.ButtonStyle.grey)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        rv = random_vote()
        if rv:
            await interaction.response.send_message("Game cancelled. P.S register to vote today!", embed=rv[0], view=rv[1], ephemeral=True)
        else:
            await interaction.response.send_message("Game cancelled.", ephemeral=True)
        self.cancel = True
        self.stop()

    @discord.ui.button(emoji="❓")
    async def ask(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("https://i.gyazo.com/ca92c09a446236b9b3c2f1726badcf06.jpg", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.initiator.id:
            return True
        await interaction.response.send_message(
            "This isn't your Worldle game!", ephemeral=True
        )
        return False


class WorldleGame:
    def __init__(self, countries: Dict[str], countrycords: Dict[str]):
        self.countryname = random.choice(list(countries))
        self.country = countries[self.countryname]
        self.countryimg = None
        self.countries = countries
        self.countrycoords = countrycords
        self.guesses = []
        self.emojis = []
        self.thecountrycord = (
            self.countrycoords[self.country][0], self.countrycoords[self.country][1])

    def get_country_cord(self, country: str):
        return (self.countrycoords[country][0], self.countrycoords[country][1])

    def get_distance(self, guess: str):
        return round(distance.distance(self.thecountrycord, self.get_country_cord(guess)).miles)

    def get_direction(self, guess: str):
        cords = self.get_country_cord(guess)
        lat1 = radians(cords[0])
        lat2 = radians(self.thecountrycord[0])
        longdiff = radians(self.thecountrycord[1]-cords[1])
        x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(longdiff)
        y = sin(longdiff) * cos(lat2)
        radbearing = atan2(y, x)
        bearing = degrees(radbearing)
        degree = round(bearing/45)
        compassdirs = ['⬆️', '↗️', '➡️', '↘️', '⬇️', '↙️', '⬅️', '↖️', '⬆️']
        direction = degree+8 if degree < 0 else degree
        return compassdirs[direction]

    def guess_emoji(self, compass: str, dist: int, guess: str):
        percent = int(100-round(dist/12430*100))
        greens = round(percent/20)
        if greens == 5 and guess != self.country:
            greens -= 1
        emojis = ""
        for i in range(5):
            if i+1 <= greens:
                emojis += "🟩"
            else:
                emojis += "🟨" if greens == 4 else "⬛"
        emojis += "🎉" if guess == self.country else compass
        self.emojis.append(emojis)

    def run_guess(self, guess: str):
        abrvguess = self.countries[guess]
        compass = self.get_direction(abrvguess)
        dist = self.get_distance(abrvguess)
        self.guess_emoji(compass, dist, abrvguess)
        self.guesses.append({'country': guess, 'distance': dist,
                            'emoji': compass, 'percent': int(100-round(dist/12430*100))})

    def create_guess_text(self):
        return "\n".join(
            f"**{guess['country']}** {guess['distance']}mi {'🎉' if guess['country']==self.countryname else guess['emoji']} __{guess['percent']}%__"
            for guess in self.guesses
        )

    def create_emoji_text(self):
        desc = f"> Worldle {len(self.emojis) if len(self.emojis)!=6 else 'X'}/6\n"
        for eline in self.emojis:
            desc += f"> {eline}\n"
        return desc

    def create_desc(self, win=None):
        guess = self.create_guess_text()
        emoji = self.create_emoji_text()
        winmsg = "Amazing 🌎✨Worldling✨🌎" if win is True else f"Awww. The correct country/territory was {self.countryname}"
        return (
            f"Guess the WORLDLE in 6 tries\n\n{emoji}\n{guess}\n{winmsg if win is not None else ''}"
            if self.guesses
            else "Guess the WORLDLE in 6 tries"
        )

    async def create_embed(self, ctx: commands.Context, win=None):
        embed = discord.Embed(title="🌎WORLDLE🌎", description=self.create_desc(
            win=win), color=discord.Color.dark_purple())
        embed.set_footer(
            text=f"{ctx.author}'s Worldle • Credit to Regis Freyd for the country images")
        img = discord.File(
            f'gamedata/countryimgs/{self.country.lower()}.png', filename="image.png")
        embed.set_image(url="attachment://image.png")
        return embed, img


class GuessView(discord.ui.View):
    def __init__(self, guesses: List[str], initiator: discord.Member):
        super().__init__(timeout=360)
        self.initiator = initiator
        self.result = None
        self.add_item(GuessSelect(guesses))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.initiator.id:
            return True

        await interaction.response.send_message(
            "This isn't your WORLDLE game!", ephemeral=True
        )
        return False


class GuessSelect(discord.ui.Select):
    def __init__(self, guesses: List[str]):
        options = [discord.SelectOption(label=guess) for guess in guesses]
        super().__init__(custom_id="guess", placeholder="Select country, territory...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="Answer submitted.", view=None)
        view: GuessView = self.view
        view.result = interaction.data['values'][0]
        view.stop()


class Worldle(commands.Cog, name="Worldle", description="Worldle! A fun variation on the game Wordle (which this bot has, by the way), you have 6 tries to guess the right country or territory based on the image of its outline that's shown. Each guess, you'll be shown the distance your guess is from the correct answer, and the direction that the correct guess from your guess. For more information about how to play, use the help button on the game menu when you run the command. Happy worldling!"):
    def __init__(self, bot):
        self.bot: PandasBot = bot

    async def check_db(self, ctx: commands.Context):
        if await self.bot.db.fetchval("SELECT * FROM worldgame WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id):
            await ctx.send("You're already playing WORLDLE in this channel!")
            return False
        return True

    async def wait_for_guess(self, ctx: commands.Context, embed: discord.Embed, img: discord.File):
        view = WorldleView(self.bot.countries, ctx.author)
        message: discord.Message = await ctx.reply(embed=embed, file=img, view=view)
        await view.wait()
        await message.delete()
        if view.cancel is True:
            await ctx.reply("Worldle cancelled.")
            await self.bot.db.execute("DELETE FROM worldgame WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id)
            return False
        if view.guess is False or view.guess is None:
            await ctx.reply("Worldle timed out.")
            await self.bot.db.execute("DELETE FROM worldgame WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id)
            return False
        return view.guess

    @commands.command(
        name="worldle",
        help="Worldle! A fun variation on the game Wordle (which this bot has, by the way), you have 6 tries to guess the right country or territory based on the image of its outline that's shown. Each guess, you'll be shown the distance your guess is from the correct answer, and the direction that the correct guess from your guess. Wordle-style emojis will also be shown to indicate how close you are from guessing the target country. For more information about how to play, use the help button on the game menu when you run the command. Happy worldling!",
        brief="Plays a game of 🌎Worldle🌎",
    )
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def wordle(self, ctx: commands.Context):
        if await self.check_db(ctx) is False:
            return
        await self.bot.db.execute("INSERT INTO worldgame VALUES($1, $2);", ctx.author.id, ctx.channel.id)
        world = WorldleGame(self.bot.countries, self.bot.countrylocs)
        guess = None
        for i in range(6):
            if guess == world.countryname or i == 6:
                break
            embed, img = await world.create_embed(ctx)
            guess = await self.wait_for_guess(ctx, embed, img)
            if guess is False:
                return
            world.run_guess(guess)
        eembed, eimg = await world.create_embed(ctx, win=guess == world.countryname)
        await ctx.reply(embed=eembed, file=eimg)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])
        await self.bot.db.execute("DELETE FROM worldgame WHERE member=$1 AND channel=$2;", ctx.author.id, ctx.channel.id)


async def setup(bot: PandasBot):
    await bot.add_cog(Worldle(bot))
