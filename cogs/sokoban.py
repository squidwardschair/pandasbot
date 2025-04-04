from __future__ import annotations
import discord
from discord.ext import commands
import asyncio
import random
import functools
import numpy
from utils.factoryparts import FactoryParts
from typing import TYPE_CHECKING
from utils.voteutils import random_vote 

if TYPE_CHECKING:
    from main import PandasBot

levels = FactoryParts.levels

levelsayings = FactoryParts.levelsayings

quotes = FactoryParts.quotes

numemojis = FactoryParts.numemojis


class Board():
    def __init__(self, level: int):
        self.boardtext = levels[level]
        self.boardarray = None
        self.goals = None
        self.char = None

    def makearray(self):
        charcode = {"#": '⬛', '/': '🟩', '*': '🔸', '-': '👷', '?': '📦'}
        board = []
        boardlist = self.boardtext.splitlines()
        for b in boardlist:
            listb = list(b)
            for i, l in enumerate(listb):
                listb[i] = charcode[l]
            board.append(listb)
        return numpy.array(board)

    async def make_array(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.makearray)
        result = await loop.run_in_executor(None, thing)
        return result

    def getgoals(self):
        goals = numpy.where(self.boardarray == "🔸")
        print([(goals[0][i], goals[1][i]) for i in range(len(goals[0]))])
        print(goals[0])
        return [(goals[0][i], goals[1][i]) for i in range(len(goals[0]))]

    async def get_boxes(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.getgoals)
        result = await loop.run_in_executor(None, thing)
        return result

    def move_player(self, direction):
        directions = {"w": -1, "a": -1, "s": 1, "d": 1}
        rowcol = 0 if direction in ["w", "s"] else 1
        playercoord = numpy.where(self.boardarray == '👷')
        allbox = numpy.where(self.boardarray == '📦')
        allbox = [(allbox[0][i], allbox[1][i]) for i in range(len(allbox[0]))]
        newcoord = [playercoord[0][0], playercoord[1][0]]
        playercoord = [playercoord[0][0], playercoord[1][0]]
        boxcords = []
        newcoord[rowcol] = playercoord[rowcol]+directions[direction]
        newcoord = list(newcoord)
        if tuple(newcoord) in allbox:
            boxcorda = list(allbox[allbox.index(tuple(newcoord))])
            boxcorda[rowcol] = boxcorda[rowcol]+directions[direction]
            boxcorda = tuple(boxcorda)
            boxcords.append(boxcorda)
            try:
                if self.boardarray[boxcorda[0], boxcorda[1]] == "🟩":
                    return False
                if any(t < 0 for t in boxcorda):
                    return False
            except:
                return False
            while True:
                try:
                    if any(t < 0 for t in boxcords[-1]):
                        return False
                    if self.boardarray[boxcords[-1]] != '📦':
                        break
                except:
                    return False
                boxcorda = list(boxcorda)
                boxcorda[rowcol] = boxcorda[rowcol]+directions[direction]
                boxcords.append(tuple(boxcorda))
        try:
            if self.boardarray[newcoord[0], newcoord[1]] == "🟩":
                return False
            if any(t < 0 for t in newcoord):
                return False
        except:
            return False
        if boxcords:
            for lbox in boxcords:
                self.boardarray[lbox[0], lbox[1]] = "📦"
        self.boardarray[newcoord[0], newcoord[1]] = "👷"
        self.boardarray[playercoord[0], playercoord[1]] = "🔸" if tuple(
            playercoord) in self.goals else "⬛"
        return self.boardarray

    async def move(self, direction):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.move_player)
        result = await loop.run_in_executor(None, thing, direction)
        return result

    def checkwin(self):
        findboxes = numpy.where(self.boardarray == '📦')
        findboxes = [(findboxes[0][i], findboxes[1][i])
                     for i in range(len(findboxes[0]))]
        return findboxes == self.goals

    async def check_win(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.checkwin)
        result = await loop.run_in_executor(None, thing)
        return result

    def prettyboard(self):
        text = ""
        for bo in self.boardarray:
            for l in bo:
                text += l
            text += "\n"
        return text

    async def pretty_board(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.prettyboard)
        result = await loop.run_in_executor(None, thing)
        return result


class MoveButtons(discord.ui.View):
    def __init__(self, board: Board, embed: discord.Embed, member: discord.Member):
        super().__init__(timeout=300)
        self.board = board
        self.embed = embed
        self.result = None
        self.member = member

    async def move(self, direction: str, interaction: discord.Interaction):
        move = await self.board.move(direction)
        if move is False:
            return
        self.embed.description = await self.board.pretty_board()
        await interaction.response.edit_message(embed=self.embed)
        if await self.board.check_win() is True:
            self.result = "win"
            self.stop()

    @discord.ui.button(emoji="🔸", style=discord.ButtonStyle.gray, row=0, disabled=True)
    async def nonea(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="⬆️", style=discord.ButtonStyle.blurple, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move("w", interaction)

    @discord.ui.button(emoji="🔸", style=discord.ButtonStyle.gray, row=0, disabled=True)
    async def noneaa(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.blurple, row=1)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move("a", interaction)

    @discord.ui.button(emoji="⬇️", style=discord.ButtonStyle.blurple, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move("s", interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.blurple, row=1)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move("d", interaction)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red, row=2)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        rv = random_vote()
        if rv:
            await interaction.response.send_message("Game cancelled. P.S register to vote today!", embed=rv[0], view=rv[1], ephemeral=True)
        else:
            await interaction.response.send_message("Game cancelled.", ephemeral=True)
        self.result = False
        self.stop()

    @discord.ui.button(label="Return to Menu", style=discord.ButtonStyle.red, row=2)
    async def menureturn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "return"
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.member.id:
            return True
        await interaction.response.send_message("This isn't your Sokoban game!", ephemeral=True)
        return False


class ContinueButtons(discord.ui.View):
    def __init__(self, member: discord.Member, maxm):
        super().__init__(timeout=300)
        self.result = None
        self.member = member
        self.maxm = maxm
        if self.maxm is False:
            self.add_item(ContinueButton())

    @discord.ui.button(label="Return to Menu", style=discord.ButtonStyle.gray)
    async def menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "return"
        self.stop()

    @discord.ui.button(label="Cancel Game", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        rv = random_vote()
        if rv:
            await interaction.response.send_message("Game cancelled. P.S register to vote today!", embed=rv[0], view=rv[1], ephemeral=True)
        else:
            await interaction.response.send_message("Game cancelled.", ephemeral=True)
        self.result = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.member.id:
            return True
        await interaction.response.send_message("This isn't your Sokoban game!", ephemeral=True)
        return False


class LevelSelect(discord.ui.Select):
    def __init__(self, toplevel):
        super().__init__(placeholder="Select a level")
        self.toplevel = toplevel
        for i, option in enumerate(levels):
            if i > self.toplevel:
                self.add_option(label=f"Level {i+1} - Locked", emoji='🔒')
            else:
                self.add_option(
                    label=f"Level {i+1}", emoji=numemojis[i], description=levelsayings[i])

    async def callback(self, interaction: discord.Interaction = discord.Interaction):
        if interaction.data['values'][0].endswith("Locked") is True:
            await interaction.response.send_message("This level is locked!", ephemeral=True)
            return
        else:
            await interaction.response.defer()
            try:
                selected = int(interaction.data['values'][0][-2:])
            except:
                selected = int(interaction.data['values'][0][-1])
            self.view.level = selected-1
            self.view.stop()


class ContinueButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Continue")

    async def callback(self, interaction=discord.Interaction):
        self.view.result = True
        self.view.stop()


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Cancel")

    async def callback(self, interaction=discord.Interaction):
        await interaction.response.defer()
        self.view.result = False
        self.view.stop()


class LevelPick(discord.ui.View):
    def __init__(self, initiator, toplevel):
        super().__init__(timeout=180)
        self.initiator = initiator
        self.level = None
        self.toplevel = toplevel
        self.add_item(LevelSelect(self.toplevel))
        self.add_item(CancelButton())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.initiator.id:
            return True
        await interaction.response.send_message("This isn't your Sokoban game!", ephemeral=True)
        return False


class Sokoban(commands.Cog, name="Bob Box Arcade Sokoban Game", description="Sokoban is a puzzle game that looks easier then it seems. You are Bob, trying to deliver packages to the correct spots in the warehouse. You will be on a board where you will have to push boxes around obstacles to reach them to the right spots. There are 24 fun levels for you to play, so get those boxes moving!"):

    def __init__(self, bot):
        self.bot: PandasBot = bot

    async def run_game(self, ctx: commands.Context, level: int, embed: discord.Embed):
        edit = False
        while True:
            embed.title = f"Sokoban Level {level+1}"
            board = Board(level)
            board.boardarray = await board.make_array()
            board.goals = await board.get_boxes()
            embed.description = await board.pretty_board()
            embed.set_footer(text=levelsayings[level])
            view = MoveButtons(board, embed, ctx.author)
            if edit:
                await message.edit(embed=embed, view=view)
            else:
                message = await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.result is True:
                edit = True
                continue
            await message.delete()
            embed.set_footer(text=None)
            break
        return view.result

    async def create_player(self, member: discord.Member):
        if await self.bot.db.fetchval("SELECT level FROM sokoban WHERE member = $1;", member.id) is None:
            await self.bot.db.execute("INSERT INTO sokoban VALUES($1, $2);", member.id, 0)

    async def update_level(self, member: discord.Member, level: int):
        await self.bot.db.execute("UPDATE sokoban SET level = $1 WHERE member = $2;", level, member.id)

    async def run_menu(self, ctx: commands.Context, embed: discord.Embed):
        embed.title = "Spongebob Sokoban"
        embed.description = "Bob the builder is ready to work! This time, at a warehouse, pushing boxes to the right position in order to get them shipped out to your front door.\nThis is a Sokoban-style game made for Discord. You must use the arrows to move Bob👷 to push the boxes📦 into the correct positions🔸. Everything looks much easier then it seems :).\nThere are 24 unique levels that increase in difficulty each time, and at the end you get a very special (not really) prize. Have fun!"
        embed.set_image(
            url="https://m.media-amazon.com/images/M/MV5BNjRlYjgwMWMtNDFmMy00OWQ0LWFhMTMtNWE3MTU4ZjQ3MjgyXkEyXkFqcGdeQXVyNzU1NzE3NTg@._V1_QL75_UX500_CR0,47,500,281_.jpg")
        view = LevelPick(ctx.author, await self.bot.db.fetchval("SELECT level FROM sokoban WHERE member = $1;", ctx.author.id))
        message = await ctx.send(embed=embed, view=view)
        await view.wait()
        await message.delete()
        embed.set_image(url=None)
        return view.level

    async def run_continue(self, ctx: commands.Context, embed: discord.Embed, level):
        print(level)
        print(len(levels)-1)
        embed.title = "You win, congrats!"
        embed.description = random.choice(quotes)
        if level > len(levels)-1:
            embed.description = "You did it Bob. For the 364th time in a row, you've won the Employee of the Month award. Your work to the my walle- I mean the warehouse will not be forgotten. \n \n Enjoy this award, Bob, you've earned it. All those those puzzles you solved to get those boxes to those houses is giving me so much mone- I mean it is helping the warehouse. \n \n Because of your amazing work, I am adding 5 cents to your paycheck. Bob Jr, on the other hand, will work for free because of his asybmal work. Enjoy your 15 cent an hour paycheck my boy! \n \n Sincerely, \n Bob's Boss"
            embed.set_thumbnail(
                url="https://www.johnmarshall.edu/wp-content/uploads/EOM-Clip-Art.jpg")
        view = ContinueButtons(ctx.author, level > len(levels)-1)
        message = await ctx.send(embed=embed, view=view)
        await view.wait()
        await message.delete()
        embed.set_image(url=None)
        return view.result

    @commands.command(name="bobboxarcade", aliases=["sokoban"], brief="Bob Box Arcade Sokoban Game", help="Sokoban is a puzzle game that looks easier then it seems. You are Bob, trying to deliver packages to the correct spots in the warehouse. You will be on a board where you will have to push boxes around obstacles to reach them to the right spots. There are 24 fun levels for you to play, so get those boxes moving!")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def sokoban(self, ctx: commands.Context):
        if await self.bot.db.fetchval("SELECT * FROM sokogames WHERE member = $1;", ctx.author.id) is not None:
            await ctx.send("You already have a Sokoban game running!")
            return
        await self.create_player(ctx.author)
        await self.bot.db.execute("INSERT INTO sokogames VALUES($1);", ctx.author.id)
        plevel = await self.bot.db.fetchval("SELECT level FROM sokoban WHERE member = $1", ctx.author.id)
        level = None
        x = True
        embed = discord.Embed(color=discord.Color.dark_magenta())
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        while x:
            menu = await self.run_menu(ctx, embed)
            level = menu
            if level is False or level is None:
                await self.bot.db.execute("DELETE FROM sokogames WHERE member = $1;", ctx.author.id)
                return
            x = False
            while True:
                print(level)
                game = await self.run_game(ctx, level, embed)
                if game is False or game is None:
                    await self.bot.db.execute("DELETE FROM sokogames WHERE member = $1;", ctx.author.id)
                    return
                elif game == "return":
                    x = True
                    break
                else:
                    level += 1
                    if level > plevel:
                        await self.update_level(ctx.author, level)
                    conmenu = await self.run_continue(ctx, embed, level)
                    if conmenu == "return":
                        x = True
                        break
                    elif conmenu is False or conmenu is None:
                        await self.bot.db.execute("DELETE FROM sokogames WHERE member = $1;", ctx.author.id)
                        return


async def setup(bot: PandasBot):
    await bot.add_cog(Sokoban(bot))
