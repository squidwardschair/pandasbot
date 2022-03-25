from __future__ import annotations
import contextlib
import discord
from discord.ext import commands
import traceback
from utils.converters import command_help_format
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import SquidwardBot


class DisabledCommandYes(commands.CheckFailure):
    pass


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot: SquidwardBot = bot
        self.bot.add_check(self.blacklist)
        self.bot.add_check(self.disabled)

    async def disabled(self, ctx):
        if (
            await self.bot.db.fetchval(
                "SELECT command FROM disabled WHERE guild = $1 AND command = $2;",
                ctx.guild.id,
                ctx.command.name,
            )
            is None
        ):
            return True
        print("aoihga")
        raise DisabledCommandYes

    async def blacklist(self, ctx):
        if (
            await self.bot.db.fetchval(
                "SELECT member FROM blacklist WHERE member = $1", ctx.author.id
            )
            is None
        ):
            return True
        await ctx.send("You are blacklisted from the bot.")
        return False

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, 'on_error'):
            return
        if cog := ctx.cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        error = getattr(error, 'original', error)
        iserror = False
        if isinstance(error, commands.DisabledCommand):
            message = discord.Embed(
                title="Disabled Command!", description=f'{ctx.command} is disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            with contextlib.suppress(discord.HTTPException):
                message = discord.Embed(
                    title="No Private Messages", description=f'{ctx.command} can not be used in Private Messages.')
                await ctx.send(embed=message)
                return
        if isinstance(error, (commands.UserInputError)):
            message = await command_help_format(ctx.command, ctx)
        elif isinstance(error, DisabledCommandYes):
            print("aoihjga")
            message = discord.Embed(
                title="Disabled Command", description="This command has been disabled by Administrators of this server.")
        elif isinstance(error, (commands.MissingPermissions, commands.MissingAnyRole, commands.MissingRole, commands.BotMissingAnyRole, commands.BotMissingPermissions, commands.BotMissingRole)):
            message = await command_help_format("permissions")
        elif isinstance(error, commands.CommandOnCooldown):
            message = discord.Embed(
                title="Cooldown", description=f"This command is on cooldown, try again in `{round(error.retry_after, 1)}` seconds.")
        elif isinstance(error, discord.errors.Forbidden):
            message = discord.Embed(
                title="No Permissions", description="I am missing the required permissions to perform this command!")
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CheckFailure):
            return
        else:
            iserror = True
            message = discord.Embed(
                title="Unknown Error", description=f"```python\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}```")
        await ctx.send(embed=message, delete_after=None if iserror else 10)


async def setup(bot: SquidwardBot):
    await bot.add_cog(CommandErrorHandler(bot))
