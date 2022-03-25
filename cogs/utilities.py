from __future__ import annotations
from turtle import update
import discord
from discord.ext import commands
import time
from datetime import timedelta
from utils.converters import RemindShorthandConverter, RemindTime, command_help_format
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import SquidwardBot


class Utilities(commands.Cog, name="Utilities", description="Utility commands to help the server in the wear and tear!"):

    def __init__(self, bot):
        self.bot: SquidwardBot = bot
        self.type = "verified"

    @commands.command(name="reload", help="Reloads a cog (updates the changes)", brief="Reloads a cog")
    @commands.is_owner()
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def reload(self, ctx: commands.Context, cog_name: str):
        try:
            await self.bot.reload_extension(cog_name)
            await ctx.send(f"🔄 {cog_name} successfuly reloaded!")
        except (commands.errors.ExtensionNotFound, commands.errors.ExtensionNotLoaded) as e:
            await ctx.send(f"I did not find a cog named {cog_name}.")
            return
        dbgames = ['chessgame', 'wordle', 'sokoban', 'worldgame']
        for game in dbgames:
            if cog_name.lower().endswith(game):
                await self.bot.db.execute(f"DELETE FROM {game}")

    @commands.command(name="shutdown", help="Shuts down the bot", brief="Shuts down the bot")
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.command(name="setprefix", help="Sets a servers prefix", brief="Sets a servers prefix")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    @commands.has_guild_permissions(administrator=True)
    async def setprefix(self, ctx: commands.Context, prefix: str):
        if len(prefix) > 5:
            await ctx.send("Prefix cannot be larger then 5 characters!")
            return
        if prefix == ctx.clean_prefix:
            await ctx.send("This is already the prefix of this guild!")
            return
        if await self.bot.db.fetchval("SELECT prefix FROM prefix WHERE guild = $1", ctx.guild.id) is not None:
            await self.bot.db.execute("UPDATE prefix SET prefix = $1", prefix)
        else:
            await self.bot.db.execute('INSERT INTO prefix VALUES ($1, $2)', ctx.guild.id, prefix)
        await ctx.send(f"✅ Prefix successfully updated to `{prefix}`")

    @commands.command(name="ping", help="Displays a bots websocket latency and API latency", brief="Checks the bots latency")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def ping(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Ping!", description="Pinging... 💻💻💻", color=discord.Color.orange())
        starttime = time.perf_counter()
        message = await ctx.send(embed=embed)
        endtime = time.perf_counter()
        startdb = time.perf_counter()
        await self.bot.db.fetch('SELECT 1;')
        enddb = time.perf_counter()
        embed = discord.Embed(
            title="Pong!", description=f"🤖 Discord API Latency: `{round((endtime-starttime) * 1000)}ms` \n 🌐 Websocket Latency: `{round(self.bot.latency * 1000)}ms` \n :desktop: Database Latency: `{round((enddb-startdb)*1000)}ms`", color=discord.Color.orange())
        await message.edit(embed=embed)

    @commands.command(name="avatar", aliases=["av"], help="Gets a user's avatar.", brief="Gets a user's avatar.")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        embed = discord.Embed(title="Avatar", color=discord.Color.purple())
        embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                         icon_url=ctx.author.avatar.with_size(1024).url)
        embed.set_image(url=member.avatar.with_size(1024).url)
        await ctx.send(embed=embed)

    @commands.command(name="setstatus", help="Changes the bot's status, only can be used by the owner.", brief="Changes the bot's status.")
    @commands.is_owner()
    async def setstatus(self, ctx: commands.Context, type=None, *, status=None):
        if status is None:
            await ctx.send("set STATUS dummy")
            return
        if type == "competing":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=status))
            await ctx.send("done")
        elif type == "playing":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=status))
            await ctx.send("done")
        elif type == "watching":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))
            await ctx.send("done")
        elif type == "listening":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
            await ctx.send("done")
        else:
            await ctx.send("what KIND of status")

    @commands.command(name="remind", help="Sets a reminder for yourself", brief="Sets a reminder for yourself")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def remind(self, ctx: commands.Context, *, reminder=None):
        remindernumber = await self.bot.db.fetchval("SELECT num FROM remindnum;")
        if reminder is None:
            await ctx.send(embed=await command_help_format(ctx.command))
            return
        converttry = await RemindShorthandConverter().convert(ctx, reminder)
        if converttry is None:
            converttry = await RemindTime().convert(ctx, reminder)
        if converttry is None:
            await ctx.send("Invalid time format! You can use time and dates with a specified TIMEZONE, or it will default to US Eastern, relative times, and time shorthands. Examples: 7/1 7PM EST, in 3 hours, 2d.")
            return
        if converttry is False:
            await ctx.send("You can't set a reminder for something in the past! Remember, if you provide a date and time without a timezone, Eastern time is defaulted. This may also be because you reminded yourself for something within a minute, or you forgot the AM or PM for your time.")
            return
        if converttry[1] is None or converttry[1].isspace is True or converttry[1] == "":
            await ctx.send("Provide me something to remind you for!")
            return
        remindertime = converttry[0]
        remindtext = converttry[1]
        if remindertime-timedelta(days=14) > discord.utils.utcnow() or remindertime-timedelta(minutes=2) < discord.utils.utcnow():
            await ctx.send("Reminder times cannot be more then 14 days and less then 2 minutes! Remember, if you provide a date and time without a timezone, Eastern time is defaulted.")
            return
        if len(await self.bot.db.fetch("SELECT * FROM reminders WHERE member = $1", ctx.author.id)) >= 3:
            await ctx.send("You can only have a maximum of 3 reminders set at once.")
            return
        await self.bot.db.execute("INSERT INTO reminders VALUES ($1, $2, $3 ,$4, $5, $6, $7);", ctx.author.id, ctx.guild.id, ctx.channel.id, remindertime.timestamp(), ctx.message.jump_url, remindtext, remindernumber)
        await ctx.send(
            f':clock1: Okay, I will remind you at <t:{int(remindertime.timestamp())}:f>'
        )

        newremindernum = remindernumber+1
        await self.bot.db.execute("UPDATE remindnum SET num = $1", newremindernum)

    @commands.command(name="deleteremind", help="Deletes a reminder by its reminder number.", brief="Deletes a reminder")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def deleteremind(self, ctx: commands.Context, remindernum: int = None):
        if remindernum is None:
            await ctx.send(embed=await command_help_format(ctx.command))
            return
        if await self.bot.db.fetchval("SELECT * FROM reminders WHERE num = $1 AND member = $2;", remindernum, ctx.author.id) is None:
            await ctx.send("No reminders found! Make sure the reminder ID is correct, run `!showreminders` to check, and make sure the reminder is yours.")
            return
        await self.bot.db.execute("DELETE FROM reminders WHERE num = $1 AND member = $2;", remindernum, ctx.author.id)
        await ctx.send("✅ Reminder deleted successfully.")

    @commands.command(name="showreminders", help="Shows a user's reminders, or your own reminders if user is not specified", brief="Shows a users reminders")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def showreminders(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if await self.bot.db.fetchval("SELECT * FROM reminders WHERE member = $1", member.id) is None:
            await ctx.send("No reminders were found for this user!")
            return
        embed = discord.Embed(
            title=f'Reminders for {member}',
            description="",
            timestamp=discord.utils.utcnow(),
            color=discord.Color.dark_gold(),
        )

        results = [dict(rem) for rem in await self.bot.db.fetch("SELECT * FROM reminders WHERE member = $1", member.id)]
        for result in results:
            guild = self.bot.get_guild(result['guild'])
            embed.add_field(name=f"Reminder {result['num']}",
                            value=f"**Time:** <t:{result['time']}:f> \n **Content:** {result['reminder']} \n **Guild Created In:** {guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="userinfo", aliases=['ui', 'info'], help="Shows a server member's information relating to their account", brief="Shows a server member's information")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        statusemojis = {"online": '🟢 Online', "idle": '🟡 Idle',
                        "dnd": '🔴 Do Not Disturb', "offline": '⚫ Offline', "invisible": '⚪ Invisible'}
        botemojis = {"yes": ':white_check_mark:', "no": ':x:'}
        rolelist = [f"<@&{role.id}>" for role in member.roles]
        roles = ', '.join(str(x) for x in rolelist[1:])
        embed = discord.Embed(
            title=str(member),
            description=f"""**__Member Information__** \n **Member:** {member.mention} \n **Name:** {member} \n **ID:** {member.id} \n **Nickname:** {member.nick} \n **Avatar:** [Avatar URL]({member.avatar.url or member.default_avatar}) \n **Bot:** {botemojis["yes" if member.bot==True else "no"]} \n **Status:** {statusemojis[member.raw_status]} \n **On Mobile:** {botemojis["yes" if member.is_on_mobile()==True else "no"]} \n **Account Created:** {discord.utils.format_dt(member.created_at)} \n **Joined At:** {discord.utils.format_dt(member.joined_at)} \n **Mutual Guilds:** {'N/A' if member.bot else ", ".join(guild.name for guild in member.mutual_guilds)} \n \n **__Member Roles__** \n **Top Role:** {member.top_role.mention} \n **All Roles:** @everyone, {roles}""",
            timestamp=discord.utils.utcnow(),
            color=member.color,
        )
        embed.set_thumbnail(url=member.avatar.url or member.default_avatar)
        await ctx.send(embed=embed)

    @commands.command(name="disable", help="Disables a command to prevent it from being used in a guild. Can only be used by Administrators.", brief="Disables a command")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    @commands.has_guild_permissions(administrator=True)
    async def disable(self, ctx: commands.Context, command_name):
        if command_name in ["disable", "enable"]:
            await ctx.send("You can't disable this command!")
            return
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send("I could not find the command to disable!")
            return
        if await command.can_run(ctx) is False or command.name == "enable" or command.name == "disable":
            await ctx.send("You can't disable this command!")
            return
        if await self.bot.db.fetchval("SELECT command FROM disabled WHERE command = $1 AND guild = $2;", command.name, ctx.guild.id) is not None:
            await ctx.send("This command is already disabled!")
            return
        await self.bot.db.execute("INSERT INTO disabled VALUES ($1, $2);", ctx.guild.id, command.name)
        await ctx.send(f"Command `{command.name}` disabled.")

    @commands.command(name="enable", help="Enables a command to allow it to be used in a guild. Can only be used by Administrators.", brief="Enables a command")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    @commands.has_guild_permissions(administrator=True)
    async def enable(self, ctx: commands.Context, command_name):
        if self.bot.get_command(command_name) is None:
            await ctx.send("I could not find the command to enable!")
            return
        command = self.bot.get_command(command_name)
        if await self.bot.db.fetchval("SELECT command FROM disabled WHERE command = $1 AND guild = $2;", command.name, ctx.guild.id) is None:
            await ctx.send("This command is already enabled!")
            return
        await self.bot.db.execute("DELETE FROM disabled WHERE guild = $1 AND command = $2;", ctx.guild.id, command.name)
        await ctx.send(f"Command `{command.name}` enabled.")

    @commands.command(name="blacklist", help="Blacklists a user from using the bot. Can only be used by the owner of the bot.", brief="Blacklists a user")
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context, user: discord.User):
        if await self.bot.db.fetchval("SELECT member FROM blacklist WHERE member = $1;", user.id) is not None:
            await ctx.send("This user is already blacklisted.")
            return
        await self.bot.db.execute("INSERT INTO blacklist VALUES ($1);", user.id)
        await ctx.send(f"Blacklisted {str(user)}")

    @commands.command(name="unblacklist", help="Unblacklists a user from using the bot. Can only be used by the owner of the bot.", brief="Unblacklists a user")
    @commands.is_owner()
    async def unblacklist(self, ctx: commands.Context, user: discord.User):
        if await self.bot.db.fetchval("SELECT member FROM blacklist WHERE member = $1;", user.id) is None:
            await ctx.send("This user is not blacklisted.")
            return
        await self.bot.db.execute("DELETE FROM blacklist WHERE member = $1;", user.id)
        await ctx.send(f"Unblacklisted {str(user)}")


async def setup(bot: SquidwardBot):
    await bot.add_cog(Utilities(bot))
