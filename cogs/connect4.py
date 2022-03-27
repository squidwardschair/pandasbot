from __future__ import annotations
import discord
from discord.ext import commands
import asyncio
import functools
import itertools
import random
from utils.gameutils import request_game, get_other_player
from typing import TYPE_CHECKING, Union, List

if TYPE_CHECKING:
    from main import PandasBot

"""
1. Refactor the hot mess of connect 4
2. Finish revising fun commands, add more reddit stories and the overall reddit story command (random subreddit use paginator generate like 10 stories)
3. Slash???
"""
# TODO THIS


class ConnectBoard:
    def __init__(self, players: List[discord.Member], ctx: commands.Context):
        self.board = [[':white_circle:' for _ in range(7)] for _ in range(6)]
        self.players = random.sample(players, 2)
        self.colors: List[discord.Member] = {
            players[0]: ':red_circle:', players[1]: ':yellow_circle:'}
        self.curplayer = self.players[0]
        self.view: Union[None, ConnectButtons] = None
        self.ctx = ctx
        self.gamemsg: Union[None, discord.Message] = None
        self.embed = None

    async def start_game(self):
        print(self.players[0])
        self.view = ConnectButtons(self.players[0], self.get_columns())
        await self.create_embed()
        self.gamemsg = await self.ctx.send(embed=self.embed, view=self.view)

    def get_rows(self, i):
        return self.board[i]

    def get_columns(self):
        col = []
        for i in range(7):
            cols = [x[i] for x in self.board]
            col.append(cols)
        return col

    def get_diagnols(self):
        diags = []
        for x, v in enumerate(self.board):
            if x > 2:
                continue
            for j in range(len(v)):
                if j > 3:
                    continue
                otherd = [self.board[x+(z+1)][j+(z+1)] for z in range(3)]
                currentd = [self.board[x][j], *otherd]
                diags.append(currentd)
            for a in reversed(range(len(v))):
                if a < 3:
                    continue
                revd = [self.board[x+(z+1)][a-(z+1)] for z in range(3)]
                revcur = [self.board[x][a], *revd]
                diags.append(revcur)
        return diags

    def check_win(self):
        diags = self.get_diagnols()
        checkw = [[':red_circle:', ':red_circle:', ':red_circle:', ':red_circle:'], [
            ':yellow_circle:', ':yellow_circle:', ':yellow_circle:', ':yellow_circle:']]
        cols = self.get_columns()
        for x, i in itertools.product(self.board, range(4)):
            if x[i:i+4] in checkw:
                return True
        return next(
            (
                True
                for c, i in itertools.product(cols, range(3))
                if c[i: i + 4] in checkw
            ),
            any(d in checkw for d in diags),
        )

    def place_piece(self):
        done = False
        for c, x in enumerate(self.board):
            if x[self.view.result] == ':white_circle:':
                continue
            self.board[c-1][self.view.result] = self.colors[self.curplayer]
            done = True
            break
        if not done:
            self.board[-1][self.view.result] = self.colors[self.curplayer]

    async def get_win(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.check_win)
        result = await loop.run_in_executor(None, thing)
        return result

    async def create_embed(self):
        description = ""
        for x in range(len(self.board)):
            description = f"{description} {' '.join([str(elem) for elem in self.board[x]])} \n"
        description = f'{description}:regional_indicator_a:  :regional_indicator_b:  :regional_indicator_c:  :regional_indicator_d:  :regional_indicator_e:  :regional_indicator_f:  :regional_indicator_g:'
        embed = discord.Embed(title="Connect 4", description=description)
        embed.set_author(icon_url=self.curplayer.display_avatar.url,
                         name=f"{self.curplayer}'s turn - 60 seconds to move")
        embed.set_footer(text=f"{self.players[0]} 🔴 vs. {self.players[1]} 🟡")
        self.embed = embed

    async def ending_embed(self, alertmsg: discord.Message, endmsg: str):
        print(self.embed)
        self.embed.set_author(name=endmsg)
        self.embed.set_footer(text="Game over")
        await self.gamemsg.edit(embed=self.embed, view=None)
        await alertmsg.delete()

    async def check_endings(self, alertmsg: discord.Message):
        print(self.embed)
        if await self.get_win() is True:
            await self.create_embed()
            await self.ending_embed(alertmsg, f"{self.curplayer} won!")
            await self.gamemsg.reply(f"{self.curplayer.mention} won Connect 4!")
            return True
        for a in self.board:
            if ':white_circle:' in a:
                break
            await self.create_embed()
            await self.ending_embed(alertmsg, "Tie - all spaces full")
            await self.gamemsg.reply("Tie game - all spots full")
            return True
        return False

    async def run_guess(self):
        print(self.curplayer)
        alertmsg = await self.ctx.send(f"{self.curplayer.mention} Your move!")
        await self.view.wait()
        if self.view.result is None:
            await self.ending_embed(alertmsg, f"{self.curplayer} went afk on a move :(")
            return False
        self.place_piece()
        ending = await self.check_endings(alertmsg)
        if ending:
            return False
        self.curplayer = get_other_player(self.curplayer, self.players)
        await self.create_embed()
        self.view = ConnectButtons(self.curplayer, self.get_columns())
        await self.gamemsg.edit(embed=self.embed, view=self.view)
        await alertmsg.delete()


class ConnectButtons(discord.ui.View):
    def __init__(self, initiator, cols):
        super().__init__(timeout=60)
        self.result = None
        self.initiator = initiator
        self.cols = cols
        self.names = ["A", "B", "C", "D", "E", "F", "G"]

    @discord.ui.button(label="A", style=discord.ButtonStyle.green, custom_id="A")
    async def blue(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 0
        self.stop()

    @discord.ui.button(label="B", style=discord.ButtonStyle.green, custom_id="B")
    async def yellow(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 1
        self.stop()

    @discord.ui.button(label="C", style=discord.ButtonStyle.green, custom_id="C")
    async def green(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 2
        self.stop()

    @discord.ui.button(label="D", style=discord.ButtonStyle.green, custom_id="D")
    async def red(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 3
        self.stop()

    @discord.ui.button(label="E", style=discord.ButtonStyle.green, custom_id="E")
    async def sdfg(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 4
        self.stop()

    @discord.ui.button(label="F", style=discord.ButtonStyle.green, custom_id="F")
    async def fdsa(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 5
        self.stop()

    @discord.ui.button(label="G", style=discord.ButtonStyle.green, custom_id="G")
    async def gsdfg(self, button: discord.ui.Button, interaction=discord.Interaction):
        await interaction.response.defer()
        self.result = 6
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("It isn't your move/this isn't your game!", ephemeral=True)
            return False
        if ':white_circle:' not in self.cols[self.names.index(interaction.data['custom_id'])]:
            await interaction.response.send_message("This column is full!", ephemeral=True)
            return False
        return True


class Connect4(commands.Cog, name="Connect 4", description="This fun board game has been recreated on Discord! Alternate between dropping red and yellow pieces down on a board to try and form 4 in a row."):

    def __init__(self, bot):
        self.bot:PandasBot = bot

    async def check_db(self, ctx: commands.Context, opponent: discord.Member):
        if await self.bot.db.fetchval("SELECT member1 FROM connect WHERE ((member1 = $1 OR member1 = $2) OR (member2 = $1 OR member2 = $2)) AND channel = $3", ctx.author.id, opponent.id, ctx.channel.id):
            await ctx.send("You're already in a game in this channel!")
            return False
        return True

    async def game_check(self, ctx: commands.Context, opponent: discord.Member):
        if ctx.author.bot or opponent.bot or ctx.author == opponent:
            await ctx.send("You can't play Connect 4 with bots or yourself!")
            return False
        dbcheck = await self.check_db(ctx, opponent)
        return dbcheck is not False

    @commands.command(name="connect4", aliases=["c4"], help="Play Connect 4 with another member; first to four in a row wins! If you don't know the rules, read them up [here](https://www.youtube.com/watch?v=utXzIFEVPjA)", brief="Play Connect 4 with another member")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def connect4(self, ctx: commands.Context, opponent: discord.Member = None):
        if opponent is None:
            await ctx.send("Provide me someone to play Connect 4 with!")
            return
        gamecheck=await self.game_check(ctx, opponent)
        if gamecheck is False:
            return
        checkopponent = await request_game(ctx, f"{ctx.author} is challenging you to a game of Connect 4. You have 2 minutes to respond or the game will be automatically declined.", opponent)
        if checkopponent is False:
            return
        await self.bot.db.execute("INSERT INTO connect VALUES ($1, $2, $3);", ctx.author.id, opponent.id, ctx.channel.id)
        board = ConnectBoard([ctx.author, opponent], ctx)
        await board.start_game()
        while True:
            guess = await board.run_guess()
            if guess is False:
                break
        await self.bot.db.execute("DELETE FROM connect WHERE member1 = $1 AND member2 = $2 AND channel = $3;", ctx.author.id, opponent.id, ctx.channel.id)


async def setup(bot: PandasBot):
    await bot.add_cog(Connect4(bot))
