import discord
from discord.ext import commands


class GameRequest(discord.ui.View):
    def __init__(self, accepter=None):
        super().__init__(timeout=120)
        self.result = None
        self.accepter = accepter

    @discord.ui.button(label="Accept Match", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.accepter.id:
            await interaction.response.send_message("This request is not for you!", ephemeral=True)
            return
        self.result = True
        self.stop()

    @discord.ui.button(label="Deny Match", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.accepter.id:
            await interaction.response.send_message("This request is not for you!", ephemeral=True)
            return
        self.result = False
        self.stop()


async def request_game(ctx, message: str, requestee: discord.Member):
    view: GameRequest = GameRequest(requestee)
    getmessage = [message, requestee.mention]
    offermsg = await ctx.send("\n".join(getmessage), view=view)
    await view.wait()
    await offermsg.delete()
    if view.result is None or view.result is False:
        await ctx.send(f"{ctx.author.mention}, the game was declined.")
        return False

    return True


async def opponent_check(ctx: commands.Context, opponent: discord.Member):
    if opponent is None:
        await ctx.send("Provide me someone to play with!")
        return False
    if opponent.bot is True:
        await ctx.send("I can't play a bot!")
        return False
    return True


def get_other_player(curplayer, players: list):
    return players[0] if curplayer == players[1] else players[1]
