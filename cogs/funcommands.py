from __future__ import annotations
import discord
from discord.ext import commands
from utils.viewutils import ButtonPaginate
from utils.imageedit import dumpy_get
import random
from typing import TYPE_CHECKING
from utils.voteutils import random_vote
if TYPE_CHECKING:
    from main import PandasBot


class Fun(commands.Cog, name="Fun", description="Fun commands to play around and joke with!"):

    def __init__(self, bot):
        self.bot: PandasBot = bot

    @commands.command(name="8ball", help="Runs a question through an 8ball.", brief="Runs a question through an 8ball.")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def _8ball(self, ctx: commands.Context):
        await ctx.send(random.choice(["It is Certain.", " It is decidedly so.", "Without a doubt.", "Yes definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",  "Yes.", "Signs point to yes.", " Reply hazy, try again.",  "Ask again later.", "Better not tell you now.",  "Cannot predict now.",  "Concentrate and ask again.", "Don\'t count on it.", "My reply is no.",  "My sources say no.",  "Outlook not so good.", "Very doubtful."]))
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    @commands.command(name="dumpy", help="Create a sus dumpy with a member", brief="Create a sus dumpy with a member")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def dumpy(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        message = await ctx.send("⌛ GIF Loading...")
        image = await dumpy_get(await member.display_avatar.read())
        await ctx.send(file=discord.File(image, filename="dumpy.gif"))
        await message.delete()
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])

    # TODO make replacements of dog, cat, fact, add joke commands, maybe get them from reddit subreddits?

    @commands.command(name="spongebobtext", aliases=["mocktext"], help="moCK SOmeoNE WItH SPongEBoB tEXT", brief="moCK SOmeoNE WItH SPongEBoB tEXT")
    @commands.cooldown(rate=1, per=3)
    async def spongebobtext(self, ctx: commands.Context, *, text: str = None):
        if text is None:
            await ctx.reply("pROvIdE a tExT tO sPoNGeBOb tExT")
            return
        newtext = ""
        for t in text:
            capital = random.choice([t.capitalize(), t.lower()])
            newtext += capital
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])
        if len(text) < 256:
            embed = discord.Embed(title=newtext)
            embed.set_image(
                url="https://i.gyazo.com/5d8eef62553c4fe1fd30373225090f94.png")
            embed.set_author(name=str(ctx.author),
                             icon_url=ctx.author.avatar.url)
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(newtext)

    @commands.command(name="tifu", aliases=["todayifuckedup"], help="Retrives stories of people messing up on r/tifu", brief="Retrives stories of people messing up on r/tifu")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def tifu(self, ctx: commands.Context):
        await self.send_reddit_story(ctx, "tifu")

    @commands.command(name="nosleep", help="Retrives creepy fictional stories on r/nosleep", brief="Retrives stories on r/nosleep")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def nosleep(self, ctx: commands.Context):
        await self.send_reddit_story(ctx, "nosleep")

    @commands.command(name="confessions", help="Retrives crazy confessions from people on r/confessions", brief="Retrives crazy confessions from people on r/confessions")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def confessions(self, ctx: commands.Context):
        await self.send_reddit_story(ctx, "confessions")

    @commands.command(name="relationships", help="Retrives insane relationship stories from people on r/relationships", brief="Retrives insane relationship stories from people on r/relationships")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def relationships(self, ctx: commands.Context):
        await self.send_reddit_story(ctx, "relationships")

    @commands.command(name="redditstory", help="Randomly selects 3 stories from 4 subreddits: r/relationships, r/confessions, r/nosleep, and r/tifu", brief="Provides 3 random stories from Reddit")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def redditstory(self, ctx: commands.Context):
        msg = await ctx.reply("Reddit stories loading...")
        embeds = []
        for _ in range(3):
            subreddit = random.choice(
                ['relationships', 'confessions', 'nosleep', 'tifu'])
            info = await self.return_reddit_data(subreddit, getpic=False)
            embed = discord.Embed(
                title=info['title'], url=info['url'], color=discord.Color.dark_red())
            embed.set_author(name=f"u/{info['author']}")
            embed.set_footer(text=f"r/{subreddit}")
            embed.description = info['desc']
            embeds.append(embed)
        await msg.delete()
        await ButtonPaginate(ctx, embeds, ctx.author)

    @commands.command(name="unpopularopinion", help="Selects 5 unpopular opinions from r/unpopularopinion", brief="Selects 5 unpopular opinions from r/unpopularopinion")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def unpopopinion(self, ctx: commands.Context):
        msg = await ctx.reply("Reddit story loading...")
        embeds = []
        for _ in range(5):
            info = await self.return_reddit_data("unpopularopinion", getpic=False)
            embed = discord.Embed(
                title=info['title'], url=info['url'], color=discord.Color.dark_red())
            embed.set_author(name=f"u/{info['author']}")
            embed.set_footer(text="r/unpopularopinion")
            embed.description = info['desc']
            embeds.append(embed)
        await msg.delete()
        await ButtonPaginate(ctx, embeds, ctx.author)

    @commands.command(name="aww", help="Retrives an aww picture from the r/aww subreddit", brief="Retrives an aww picture from Reddit")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def aww(self, ctx: commands.Context):
        await self.send_reddit_story(ctx, "aww", getpic=True)

    @commands.command(name="redditpics", help="Retrives an interesting picture from the r/pics subreddit", brief="Retrives a picture from r/pics")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.guild)
    async def pics(self, ctx: commands.Context):
        await self.send_reddit_story(ctx, "pics", getpic=True)

    async def send_reddit_story(self, ctx: commands.Context, subreddit: str, getpic=False):
        info = await self.return_reddit_data(subreddit, getpic)
        if info is False:
            await ctx.reply("Error retriving Reddit story, please try again later.")
            return
        embed = discord.Embed(
            title=info['title'], url=info['url'], color=discord.Color.dark_red())
        embed.set_author(name=f"u/{info['author']}")
        embed.set_footer(text=f"r/{subreddit}")
        if getpic:
            embed.set_image(url=info['img'])
        else:
            embed.description = info['desc']
        await ctx.reply(embed=embed)

    # TODO ADD ERROR HANDLING FOR THIS CHANGE THE SESSION_GET METHOD TO INCLUDE STATUS CODE AND JUST CHECK 4 THAT
    async def return_reddit_data(self, subreddit: str, getpic):
        async with self.bot.session.get(f"https://www.reddit.com/r/{subreddit}/top.json", headers={"User-Agent": "squidwardbot"}) as s:
            if s.status != 200:
                return False
            info = await s.json()
        while True:
            post = random.choice(info['data']['children'])['data']
            if getpic and (post['is_video'] is False and post['url'].endswith(('jpg', 'png', 'webp'))):
                return {"title": post['title'], "author": post['author_fullname'], "img": post['url'], "url": f"https://www.reddit.com/{post['permalink']}"}
            if not getpic and len(post['selftext']) < 4096:
                return {"title": post['title'], "desc": post['selftext'], "author": post['author_fullname'], "url": post['url']}
            continue
# TODO CONSIDER TRANSITION TO SLASH
# TODO func for returning random info of a post from a subreddit (title, user, user pfp, body of the text), use that to post embeds for stories from tales from retail, tales for tech support, TIFU, malicious comliance, etc
# TODO also add reddit stuff from nottheonion


async def setup(bot: PandasBot):
    await bot.add_cog(Fun(bot))
