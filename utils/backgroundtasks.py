import discord
from datetime import timedelta
from discord.ext import commands, tasks
from main import PandasBot
from io import BytesIO
import config


class BackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot: PandasBot = bot
        self.remind.start()
        self.get_iss.start()

    @tasks.loop(minutes=2)
    async def remind(self):
        allreminders = []
        nowtimestamp = discord.utils.utcnow().timestamp()
        leapedtimea = discord.utils.utcnow()+timedelta(minutes=2)
        leapedtime = leapedtimea.timestamp()
        allreminders.extend(
            dict(rem)
            for rem in await self.bot.db.fetch(
                "SELECT * FROM reminders WHERE time >= $1 AND time <= $2;",
                nowtimestamp,
                leapedtime,
            )
        )

        for result in allreminders:
            guild = self.bot.get_guild(result["guild"])
            if guild not in self.bot.guilds:
                await self.bot.db.execute('DELETE FROM reminders WHERE num = $1;', result['num'])
                continue
            remindermember = guild.get_member(result['member'])
            reminderchannel = guild.get_channel(result['channel'])
            try:
                await remindermember.send(
                    f':alarm_clock: Reminder set for <t:{int(result["time"])}:f>! {result["reminder"]} - <@{result["member"]}> \n \n {result["messageurl"]}'
                )

            except discord.errors.Forbidden:
                if reminderchannel is None:
                    await self.bot.db.execute('DELETE FROM reminders WHERE num = $1', result['num'])
                    continue
                await reminderchannel.send(
                    f':alarm_clock: Reminder set for <t:{int(result["time"])}:f>! {result["reminder"]} - <@{result["member"]}> \n \n {result["messageurl"]}'
                )

            await self.bot.db.execute('DELETE FROM reminders WHERE num = $1', result['num'])

    @remind.before_loop
    async def before_remind(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def get_iss(self):
        issjson = await self.bot.session_get("http://api.open-notify.org/iss-now.json")
        long, lat = issjson['iss_position']['longitude'], issjson['iss_position']['latitude']
        async with self.bot.session.get(f"https://api.mapbox.com/styles/v1/mapbox/light-v10/static/url-https%3A%2F%2Fi.gyazo.com%2F64b37a6723f44e375755192fb4978e99.png({long},{lat})/10.7538,0,0.46,0/700x500?access_token={config.MAPBOX}") as m:
            bytesimage = BytesIO(await m.content.read())
            embedimage = discord.File(fp=bytesimage, filename="image.png")
        self.bot.issimage = embedimage
        self.bot.isscoord = (long, lat)

    @get_iss.before_loop
    async def before_iss(self):
        await self.bot.wait_until_ready()


async def setup(bot: PandasBot):
    await bot.add_cog(BackgroundTasks(bot))
