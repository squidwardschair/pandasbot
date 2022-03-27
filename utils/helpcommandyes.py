import discord
from discord.ext.commands import Context, Command, HelpCommand, Cog
from difflib import get_close_matches
from typing import Mapping, Optional, List
from typing import Union

COG_EMOJIS = {"Information": "ℹ️", "Utilities": "⚙️",
              "Fun": "🎉", "Games": "🎮", "Main Page": "❔"}

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.message:Union[None, discord.Message]=None

    async def on_timeout(self):
        await self.message.edit(view=None)

class HelpSelect(discord.ui.Select):
    def __init__(self, embeddict, initiator):
        super().__init__(placeholder="Select a category")
        self.embeddict = embeddict
        self.initiator = initiator
        for option in self.embeddict:
            self.add_option(
                label=option, description=self.embeddict[option][1], emoji=COG_EMOJIS[option])

    async def callback(self, interaction: discord.Interaction = discord.Interaction):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
            return
        await interaction.response.edit_message(embed=self.embeddict[interaction.data['values'][0]][0])


class myHelp(HelpCommand):

    def __init__(self, **options):
        super().__init__(**options)
        self.games = {'Connect 4': '<:connect4emoji:942167650375708682>', 'Wordle': '<:wordleemoji:941907261243146240>',
                      'Chess': '<:chessemoji:942169366072529016>', 'Bob Box Arcade Sokoban Game': '<:sokobanemoji:942181851433402378>', "Worldle": "🌎"}

    def get_command_signature(self, command: Command):
        ctx = self.context
        allnames = [command.qualified_name, *command.aliases]
        signature = f" {command.signature}" if command.signature != "" else command.signature
        return ', '.join(f'{ctx.clean_prefix}{name}{signature}' for name in allnames)

    def get_command_name(self, command: Command):
        return f'{command.qualified_name}'

    async def create_embed(self, cog: Cog):
        ctx: Context = self.context
        description = cog.description or "No description."
        commandyes = cog.get_commands()
        filtercommands = await self.filter_commands(commandyes, sort=True)
        embed = discord.Embed(title=f"{cog.qualified_name} Category Help", description=description,
                              timestamp=discord.utils.utcnow(), color=discord.Color.dark_magenta())
        for command in filtercommands:
            embed.add_field(
                name=f"`{self.get_command_signature(command)}`", value=command.brief, inline=True)
        embed.set_thumbnail(url=ctx.me.display_avatar.url)
        embed.set_footer(
            text=f"Do {ctx.clean_prefix}help [command] or {ctx.clean_prefix}help for more information | <> is required | [] is optional")
        return [embed, cog.description or 'N/A']

    async def create_game_embed(self):
        embed = discord.Embed(title="Pandas Games", description="A variety of fun games to play on your own and with friends, play one of these while hanging out and chatting in your server!",
                              timestamp=discord.utils.utcnow(), color=discord.Color.dark_magenta())
        for name in self.games:
            cog: Cog = self.context.bot.get_cog(name)
            embed.add_field(name=f"{self.games[name]}{cog.qualified_name}{self.games[name]}",
                            value=f"`{self.get_command_signature(cog.get_commands()[0])}`\n{cog.description}", inline=False)
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/939545743428038706/942182019813756948/allgames.png")
        embed.set_footer(
            text="Happy discord-gaming! Check back in for new games being added :)")
        return embed

    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command]]):
        embed = discord.Embed(title="Pandas Help", timestamp=discord.utils.utcnow(
        ), color=discord.Color.dark_magenta())
        usablecommands = 0
        ctx: Context = self.context
        totalcommands = len(ctx.bot.commands)
        embeds = {}
        gamecogs = []
        for cog, commands in mapping.items():
            filtercommands = await self.filter_commands(commands, sort=True)
            amountcommands = len(filtercommands)
            if amountcommands == 0:
                continue
            usablecommands += amountcommands
            if cog:
                if cog.qualified_name in self.games:
                    print('bb')
                    gamecogs.append(cog)
                    continue
                embed.add_field(
                    name=f'{cog.qualified_name} [{amountcommands}]', value=cog.description)
                embeds[cog.qualified_name] = await self.create_embed(cog)
        embeds['Games'] = [await self.create_game_embed(), "Pandas games made for Discord"]
        embed.add_field(name="Pandas Games", value="Play some fun and unique games on Discord while hanging out with friends! Find the best starting word with Wordle, play mindgames with Chess, scream at your friend in Connect 4, and use logic to fill out the orders with Bob Box Arcade!")
        embed.set_thumbnail(url=ctx.me.display_avatar.url)
        embed.description = f"Pandas is a multi purpose bot designed to energize and engage a server. Read hilarious stories from Reddit, track where the ISS is, set reminders on Discord, and play games made for Discord.\n\n**{ctx.guild.name}'s prefix:** `{ctx.clean_prefix}` \n **Total Commands:** {totalcommands} | **Usable Commands:** {usablecommands} \n ```diff\n+ Do !help [command] or !help for more information\n- <> is required | [] is optional\n+ Use the dropdown menu to navigate through the command categories!```"
        embed.set_footer(text="Created by MrApples#2555",
                         icon_url="https://i.pinimg.com/564x/68/b0/6d/68b06dfca48a6a5fd8307d4a39dc3ef4.jpg")
        embed.set_author(name=str(ctx.author),
                         icon_url=ctx.author.display_avatar.url)
        embed.url="https://github.com/squidwardschair/pandasbot/blob/main/README.md"
        tempdict = {"Main Page": [embed, "The main help page"]}
        embeds = {**tempdict, **embeds}
        print(embeds)
        view = HelpView()
        view.add_item(HelpSelect(embeds, ctx.author))
        msg=await ctx.send(embed=embed, view=view)
        view.message=msg

    async def send_cog_help(self, cog: Cog):
        if cog.qualified_name in self.games:
            await self.context.send(embed=await self.create_game_embed())
            return
        ctx = self.context
        description = cog.description or "No description."
        embed = discord.Embed(title=f"{cog.qualified_name} Category Help", description=description,
                              timestamp=discord.utils.utcnow(), color=discord.Color.dark_magenta())
        commands = cog.get_commands()
        filtercommands = await self.filter_commands(commands, sort=True)
        amountcommands = len(filtercommands)
        if amountcommands == 0:
            await self.send("No usable commands in this category!")
            return
        for command in filtercommands:
            embed.add_field(
                name=f"`{self.get_command_signature(command)}`", value=command.brief, inline=True)
        embed.set_thumbnail(url=ctx.me.display_avatar.url)
        embed.set_footer(
            text=f"Do {ctx.clean_prefix}help [command] or {ctx.clean_prefix}help for more information | <> is required | [] is optional")
        embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                         icon_url=ctx.author.display_avatar.url)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: Command):
        if command.cog.qualified_name in self.games:
            await self.context.send(embed=await self.create_game_embed())
            return
        ctx: Context = self.context
        embed = discord.Embed(title=f"{ctx.clean_prefix}{command} - {command.cog.qualified_name} Category",
                              description=command.help or "No help found...")
        embed.add_field(
            name="Usage", value=f"`{self.get_command_signature(command)}`", inline=True)
        if command._buckets and (cooldown := command._buckets._cooldown):
            embed.add_field(name="Cooldown",
                            value=f"{cooldown.per:.0f} seconds", inline=True)
        if command.aliases:
            embed.add_field(name="Alias", value=",".join(
                command.aliases), inline=True)
        embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                         icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=ctx.me.display_avatar.url)
        embed.set_footer(
            text=f"Do {ctx.clean_prefix}help [category] or {ctx.clean_prefix}help for more information | <> is required | [] is optional")
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def command_not_found(self, string: str):
        cmdlist = [str(name) for name in self.context.bot.commands]
        cmdlist.extend(
            f"{c} (Category)"
            for c in self.context.bot.cogs
            if c != "CommandErrorHandler" and c not in self.games
        )

        if string.title() in self.context.bot.cogs:
            await self.send_cog_help(self.context.bot.get_cog(string.title()))
            return
        if matches := get_close_matches(string, cmdlist):
            desc = f"No command called \"{string}\" called. Did you mean...\n\n"
            for i, m in enumerate(matches):
                if i > 2:
                    continue
                desc = f'{desc}`{m}`\n'
        else:
            desc = f"No command called \"{string}\" called."
        return desc

    async def send_error_message(self, error):
        if error is None:
            return
        embed = discord.Embed(title="Help not found!", description=error)
        channel = self.get_destination()
        await channel.send(embed=embed)
        return
