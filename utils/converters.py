import discord
from datetime import timedelta
from discord.ext import commands, tasks
from dateparser.search import search_dates
from dateparser import parse
import functools
import asyncio

time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


class TimeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if argument.endswith('s') or argument.endswith('h') or argument.endswith('m') or argument.endswith('d'):
            get_unit = argument[-1]
            if get_unit in time_dict:
                return time_dict[get_unit] * int(argument.rstrip(get_unit))
            else:
                raise TypeError("Invalid shorthand")
        else:
            raise TypeError("Invalid shorthand")


class RemindTime(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        getparse = await parse_get(argument)
        if getparse is None:
            return None
        string_date = getparse[1]
        date_obj = getparse[0]
        if date_obj <= discord.utils.utcnow():
            return False

        reason = argument.replace(string_date, "")
        if reason.startswith('me') and reason[:6] in (
            'me to ',
            'me in ',
            'me at ',
        ):
            reason = reason[6:]

        if reason[:2] == 'me' and reason[:9] == 'me after ':
            reason = reason[9:]

        if reason[:3] == 'me ':
            reason = reason[3:]

        if reason[:2] == 'me':
            reason = reason[2:]

        if reason[:6] == 'after ':
            reason = reason[6:]

        if reason[:5] == 'after':
            reason = reason[5:]

        return (date_obj, reason)


class RemindShorthandConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        argsplit = argument.split(' ', 1)
        try:
            length = await TimeConverter().convert(ctx, argsplit[0])
        except TypeError:
            return None
        if discord.utils.utcnow()+timedelta(seconds=length) <= discord.utils.utcnow():
            return False
        try:
            reason = argsplit[1]
        except IndexError:
            reason = None
        return (discord.utils.utcnow()+timedelta(seconds=length), reason)


async def command_help_format(command: str, ctx: commands.Context = None):
    if command == "permissions":
        embed = discord.Embed(title="Missing Permissions",
                              description="You are missing the required permissions to run this command!")
        return embed
    if command == "remind":
        embed = discord.Embed(
            title="Command: remind", description=f"**Description:** Sets a reminder for yourself \n **Format:** {ctx.clean_prefix}remind <time - timedelta, timeshorthand, or time and date with timezone> <reminder text> \n **Category:** Utilities")
    if command._buckets and (cooldown := command._buckets._cooldown):
        saying = f"**Cooldown:** {cooldown.per:.0f} seconds \n"
    else:
        saying = ""
    print(command.usage)
    embed = discord.Embed(
        title=f"Command: {command.name}", description=f"**Description:** {command.short_doc} \n {saying} **Format:** {ctx.clean_prefix}{command.qualified_name} {command.signature} \n **Category:** {command.cog_name or 'N/A'} ")
    return embed


def parsetime(argument: str):
    parsedbefore = search_dates(argument)
    if parsedbefore is None:
        return None
    parsed = parse(parsedbefore[0][0])
    if parsed.tzinfo is None:
        parsed = parse(parsedbefore[0][0], settings={
                       'TIMEZONE': 'US/Eastern', 'RETURN_AS_TIMEZONE_AWARE': True})
    return [parsed, parsedbefore[0][0]]


async def parse_get(argument: str):
    loop = asyncio.get_running_loop()
    thing = functools.partial(parsetime, argument)
    result = await loop.run_in_executor(None, thing)
    return result
