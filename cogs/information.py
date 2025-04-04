from __future__ import annotations
import aiohttp
import discord
from discord.ext import commands
from dateutil.parser import parse
import config
import contextlib
import random
from utils.viewutils import ButtonPaginate
import datetime
from typing import TYPE_CHECKING, Dict
from utils.voteutils import vote_embed, random_vote

if TYPE_CHECKING:
    from main import PandasBot

newsapikey = config.NEWSAPIKEY


class Information(commands.Cog, name="Information", description="Commands to get information from external sources or user content"):

    def __init__(self, bot):
        self.bot: PandasBot = bot

    @commands.command(name="vote", help="Only 69.1 percent of U.S eligible voters are registered to vote. Just over half have actually voted in the last presidential election, and this percentage drops for local and midterm elections. The United States ranks 31st in voter turnout for OCED countries, behind countries like Poland, Slovakia, and Brazil. Be part of the solution and register to vote today.", brief="Learn how to register to vote.")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def vote(self, ctx: commands.Context):
        embed, view = vote_embed()
        await ctx.reply(embed=embed, view=view)
        
    @commands.command(name="news", help="Gets top news headlines, using the NewsAPI", brief="Gets the top news")
    @commands.cooldown(rate=1, per=360, type=commands.BucketType.guild)
    async def news(self, ctx: commands.Context):
        now = datetime.datetime.now()

        async def to_time(check):
            if check is None:
                return "N/A"
            time = parse(check)
            return f'<t:{int(time.timestamp())}:f>'
        news = await self.bot.session_get(f'https://newsapi.org/v2/top-headlines?country=us&pageSize=10&page=1&apiKey={newsapikey}')
        embeds: Dict[str:discord.Embed] = {}
        for i in range(len(news['articles'])):
            embeds['embed_'+str(i)] = discord.Embed(title=f"News Headlines for <t:{str(int(now.timestamp()))}:f>", description=f"**{news['articles'][i]['title']}** \n **Author:** {news['articles'][i]['author'] if news['articles'][i]['author'] is not None else 'N/A'} \n {news['articles'][i]['description'] if news['articles'][i]['description'] is not None else 'No description found.'} \n **URL:** {news['articles'][i]['url']} \n **Publish Time:** {await to_time(news['articles'][i]['publishedAt'])}", timestamp=discord.utils.utcnow(), color=discord.Color.gold())
            if news['articles'][i]['urlToImage'] is not None:
                embeds['embed_' +
                       str(i)].set_image(url=news['articles'][i]['urlToImage'])
        embedspaginate = list(embeds.values())
        await ButtonPaginate(ctx, embedspaginate, ctx.author)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="word", help="Searches a word through the dictionary and returns the results", brief="Dictionary definitions and information")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def word(self, ctx: commands.Context, *, word: str):
        wordsearch = await self.bot.session_get(f"https://api.dictionaryapi.dev/api/v2/entries/en_US/{word}")
        with contextlib.suppress(KeyError, TypeError):
            await ctx.send(wordsearch['title'])
            return
        description = []
        embeds: Dict[str:discord.Embed] = {}
        for i in range(len(wordsearch[0]['meanings'])):
            try:
                example = wordsearch[0]['meanings'][i]['definitions'][0]['example']
            except KeyError:
                example = "No example found."
            description.append(
                f"**Definition:** {wordsearch[0]['meanings'][i]['definitions'][0]['definition']} \n **Example:** {example} \n **Part of Speech:** {wordsearch[0]['meanings'][i]['partOfSpeech'].title()}")
            embeds[f'embed_{str(i)}'] = discord.Embed(
                title=f"{wordsearch[0]['word']} - {wordsearch[0]['phonetics'][-1]['text']}",
                description=description[i],
                timestamp=discord.utils.utcnow(),
                color=discord.Color.orange(),
            )

            embeds['embed_' +
                   str(i)].set_footer(text=f"Search query: {word}")
            embedspaginate = list(embeds.values())

        await ButtonPaginate(ctx, embedspaginate, ctx.author)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="lichess", help="Searches for a LiChess user, using the LiChess API.", brief="Searches for a LiChess user.")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def lichess(self, ctx: commands.Context, *, user: str):
        if user is None:
            await ctx.send("Provide me a LiChess user to search for!")
            return
        try:
            usersearch = await self.bot.session_get(f"https://lichess.org/api/user/{user}")
        except aiohttp.ContentTypeError:
            await ctx.send("LiChess user not found!")
            return
        onlinemojis = {"yes": ':white_check_mark:', "no": ':x:'}
        types = ['blitz', 'bullet',
                 'correspondence', 'classical', 'rapid']
        embed = discord.Embed(title=f"LiChess User {usersearch['username']}", description=f"**Online Status:** {onlinemojis['yes' if usersearch['online']==True else 'no']} \n **Last Online:** {datetime.datetime.utcfromtimestamp(usersearch['seenAt']//1000).strftime('%m/%d/%Y, %I:%M %p')} UTC \n **Time Spent Playing:** {datetime.timedelta(seconds=usersearch['playTime']['total'])} \n **Record:** {usersearch['count']['win']}-{usersearch['count']['loss']}-{usersearch['count']['draw']} ({usersearch['count']['all']} games played) \n **Player Profile URL:** {usersearch['url']}", timestamp=discord.utils.utcnow(), color=discord.Color.dark_grey())
        for i in types:
            if usersearch['perfs'][i]['prog'] > 0:
                emoji = ':green_circle:'
            elif usersearch['perfs'][i]['prog'] == 0:
                emoji = ':heavy_minus_sign:'
            elif usersearch['perfs'][i]['prog'] < 0:
                emoji = ':small_red_triangle_down:'
            embed.add_field(name=f"{i.capitalize()} rated stats",
                            value=f"Rating: {usersearch['perfs'][i]['rating']} \n Games Played: {usersearch['perfs'][i]['games']} \n Progress: {usersearch['perfs'][i]['prog']} {emoji}")
            embed.set_footer(text=f"Search query: {user}")
        await ctx.send(embed=embed)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="chess.com", help="Searches for a chess.com user, using the chess.com API", brief="Searches for a chess.com user")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def chesscom(self, ctx: commands.Context, *, user: str):
        userinfosearch = await self.bot.session_get(f"https://api.chess.com/pub/player/{user}")
        if "code" in userinfosearch:
            await ctx.send("No chess.com user found!")
            return
        usersearch = await self.bot.session_get(f"https://api.chess.com/pub/player/{user}/stats")
        embed = discord.Embed(title=f"Chess.com User {userinfosearch['username']}", timestamp=discord.utils.utcnow(
        ), color=discord.Color.dark_grey())
        types = ['chess_blitz', 'chess_bullet', 'chess_rapid']
        totalrecord = {"win": 0, "loss": 0, "draw": 0}
        for i in types:
            try:
                embed.add_field(name=f"{i[6:].capitalize()} rated stats", value=f"Rating: {usersearch[i]['last']['rating']} \n Games Played: {usersearch[i]['record']['win']+usersearch[i]['record']['loss']+usersearch[i]['record']['draw']} \n Record: {usersearch[i]['record']['win']}-{usersearch[i]['record']['loss']}-{usersearch[i]['record']['draw']}")
            except KeyError:
                continue
            for k in totalrecord:
                totalrecord[k] = totalrecord[k] + \
                    usersearch[i]['record'][k]
            embed.description = f"**Last Online:** {datetime.datetime.utcfromtimestamp(userinfosearch['last_online']).strftime('%m/%d/%Y, %I:%M %p')} UTC \n **Followers:** {userinfosearch['followers']} \n **Record** {totalrecord['win']}-{totalrecord['loss']}-{totalrecord['draw']} \n **Player Profile URL:** {userinfosearch['url']}"
            embed.set_footer(text=f"Search query: {user}")
        if not embed.description:
            await ctx.send("Chess.com data unavaliable.")
            return
        await ctx.send(embed=embed)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="wikipedia", aliases=["wiki"], help="Searches through wikipedia and returns the page content", brief="Searches through wikipedia")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def wikipedia(self, ctx: commands.Context, *, search: str):
        embeds = []
        wikipediasearch = await self.bot.session_get(f"https://en.wikipedia.org/w/api.php?action=opensearch&format=json&search={search}&limit=10")
        if len(wikipediasearch[2]) == 0:
            await ctx.send("No articles found!")
            return
        for article in wikipediasearch[1]:
            articlesearch = await self.bot.session_get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{article}")
            if articlesearch['title'] == "Not found.":
                continue
            embed = discord.Embed(
                title=articlesearch['title'], description=f"[Wikipedia Article URL (desktop)]({articlesearch['content_urls']['desktop']['page']}) | [Wikipedia Article URL (mobile)]({articlesearch['content_urls']['mobile']['page']})\n {articlesearch['extract']}", timestamp=discord.utils.utcnow(), color=discord.Color.light_grey())
            with contextlib.suppress(KeyError):
                embed.set_thumbnail(
                    url=articlesearch['thumbnail']['source'])
            embed.set_footer(text=f"Search query: {search}")
            embeds.append(embed)

        await ButtonPaginate(ctx, embeds, ctx.author)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="iss", help="Retrives data from the ISS, including position, a map image, and the astronauts on board!", brief="Retrives data from the ISS")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def iss(self, ctx: commands.Context):
        astrojson = await self.bot.session_get('http://api.open-notify.org/astros.json')
        astronauts = [i['name']
                      for i in astrojson['people'] if i['craft'] == 'ISS']
        astronauts[-1] = f'and {astronauts[-1]}.'
        embedimage = self.bot.issimage
        embed = discord.Embed(title="International Space Station Data",
                              description=f"The International Space Station is a space station orbiting above earth, constructed as a joint effort among many countries. Run `!wikipedia International Space Station` for more info! \n **The current people aboard the ISS are:** {', '.join(astronauts)}", timestamp=discord.utils.utcnow(), color=discord.Color.gold())
        embed.set_author(name=str(
            ctx.author), icon_url=ctx.author.avatar.url or ctx.author.default_avatar)
        embed.add_field(name="Longitude", value=self.bot.isscoord[0])
        embed.add_field(name="Latitude", value=self.bot.isscoord[1])
        embed.set_image(url="attachment://image.png")
        embed.set_footer(
            text="The ISS's location is retrived every minute")
        await ctx.send(file=embedimage, embed=embed)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="apod", aliases=["astronomypicture", "spacepicture"], help="Shows the NASA Astronomy Picture of the Day", brief="Shows the Astronomy Picture of the Day")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def apod(self, ctx: commands.Context):
        apod = await self.bot.session_get(
            f'https://api.nasa.gov/planetary/apod?api_key={config.NASAAPI}'
        )
        embed = discord.Embed(title=apod['title'], description=apod['explanation'],
                              timestamp=discord.utils.utcnow(), color=discord.Color.dark_grey())
        embed.set_author(
            name=f"NASA Astronomy Picture of the Day for {datetime.datetime.strftime(datetime.datetime.strptime(apod['date'], '%Y-%m-%d'), '%B %#d, %Y')}", icon_url="https://i.gyazo.com/04e3cf40a29abf50ab374ef9f901c071.png")
        embed.set_image(url=apod['hdurl'])
        await ctx.send(embed=embed)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="marsphotos", aliases=["mars"], help="Gets photos from Mars using the Mars Imagery API (with pictures from the Perseverence rover)", brief="Gets photos from Mars")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def mars(self, ctx: commands.Context):
        info = await self.bot.session_get(f"https://api.nasa.gov/mars-photos/api/v1/rovers/Perseverance?api_key={config.NASAAPI}")
        maxsol = info['rover']['max_sol']
        rover = await self.bot.session_get(f"https://api.nasa.gov/mars-photos/api/v1/rovers/Perseverance/photos?api_key={config.NASAAPI}&sol={random.randint(0, maxsol)}")
        randindex = random.randrange(len(rover['photos']))
        photo = rover['photos'][randindex]['img_src']
        datetaken = rover['photos'][randindex]['earth_date']
        camera = rover['photos'][randindex]['camera']['full_name']
        embed = discord.Embed(title="Perseverance Rover Mars Photo",
                              description="", timestamp=discord.utils.utcnow(), color=discord.Color.dark_red())
        embed.add_field(name="Camera", value=camera)
        embed.add_field(name="Date Taken", value=datetaken)
        embed.set_image(url=photo)

        await ctx.send(embed=embed)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])


async def setup(bot: PandasBot):
    await bot.add_cog(Information(bot))
