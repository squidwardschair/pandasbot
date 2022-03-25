import discord
from typing import List, Tuple, Union
from discord.ext import commands


class ButtonPaginator(discord.ui.View):
    def __init__(self, embeds: List[discord.Embed], initiator: discord.Member):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.initiator = initiator
        self.message = None
        self.currentindex = 0

        for e in self.embeds:
            e.set_footer(
                text=f"({self.embeds.index(e) + 1}/{len(self.embeds)}) • {'' if e.footer.text is None else e.footer.text}"
            )

    async def interaction_check(self, interaction):
        if interaction.user.id == self.initiator.id:
            return True

        await interaction.response.send_message("This isn't your paginator!", ephemeral=True)
        return False

    async def on_timeout(self):
        await self.message.edit(view=None)

    @discord.ui.button(emoji="⏮️")
    async def fullbackwards(self, button: discord.Button, interaction: discord.Interaction = discord.Interaction):
        self.currentindex = 0
        await interaction.response.edit_message(embed=self.embeds[self.currentindex])

    @discord.ui.button(emoji="⬅️")
    async def backwards(self, button: discord.Button, interaction: discord.Interaction = discord.Interaction):
        self.currentindex = self.currentindex-1 if self.currentindex >= 1 else -1
        await interaction.response.edit_message(embed=self.embeds[self.currentindex])

    @discord.ui.button(emoji="➡️")
    async def forwards(self, button: discord.Button, interaction: discord.Interaction = discord.Interaction):
        try:
            self.embeds[self.currentindex+1]
            self.currentindex = self.currentindex+1
        except IndexError:
            self.currentindex = 0
        await interaction.response.edit_message(embed=self.embeds[self.currentindex])

    @discord.ui.button(emoji="⏭️")
    async def fullforwards(self, button: discord.Button, interaction: discord.Interaction = discord.Interaction):
        self.currentindex = len(self.embeds)-1
        await interaction.response.edit_message(embed=self.embeds[self.currentindex])

    @discord.ui.button(emoji="🛑")
    async def stop(self, button: discord.Button, interaction=discord.Interaction):
        await self.message.edit(view=None)


class ButtonConfirmation(discord.ui.View):
    def __init__(self, initiator, timeout):
        super().__init__(timeout=timeout)
        self.initiator = initiator
        self.result = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.initiator.id:
            return True
        await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)
        return False

    @discord.ui.button(emoji="✔️", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.Button, interaction=discord.Interaction):
        self.result = True
        self.stop()

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.red)
    async def deny(self, button: discord.Button, interaction=discord.Interaction):
        self.result = False
        self.stop()


async def button_confirm(initiator: discord.Member, channel: discord.TextChannel, prompt: Union[discord.Embed, str], embed=None, timeout=120) -> Tuple[bool, discord.Message]:
    view = ButtonConfirmation(initiator, timeout)
    message = await channel.send(prompt if embed is None else None, embed=None if embed is None else embed, view=view)
    await view.wait()
    return view.result, message


async def followup_confirm(interaction: discord.Interaction, prompt: Union[discord.Embed, str], embed=None, timeout=120) -> Tuple[bool, discord.Message]:
    view = ButtonConfirmation(interaction.user, timeout)
    message = await interaction.followup.send(prompt if embed is None else None, embed=None if embed is None else embed, view=view, ephemeral=True)
    await view.wait()
    return view.result, message


async def ButtonPaginate(ctx, embeds, initiator) -> None:
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
        return
    view = ButtonPaginator(embeds, initiator)
    view.message = await ctx.reply(embed=embeds[0], view=view)


class ListView(discord.ui.View):
    def __init__(self, namestyles: dict, member: discord.Member, ctx: commands.Context, timeout, timeouttalk, cancel: bool = False):
        super().__init__(timeout=timeout)
        self.result = None
        self.member = member
        self.ctx = ctx
        self.timeouttalk = timeouttalk
        for name, value in namestyles.items():
            self.add_item(ListButton(name, value))
        if cancel:
            self.add_item(CancelButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This button menu is not for you.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.timeouttalk:
            await self.ctx.send("Menu timed out, please try again.")


class ListButton(discord.ui.Button):
    def __init__(self, name: str, style: discord.ButtonStyle):
        super().__init__(style=style, label=name)
        self.name = name

    async def callback(self, interaction: discord.Interaction = discord.Interaction):
        view: ListView = self.view
        view.result = self.name
        await interaction.response.send_message(f"Selected `{self.name}`.", ephemeral=True)
        view.stop()


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Cancel")

    async def callback(self, interaction: discord.Interaction = discord.Interaction):
        view: ListView = self.view
        view.result = False
        await interaction.response.send_message('Cancelled prompt.', ephemeral=True)
        view.stop()


async def list_buttons(ctx: commands.Context, namestyles: Union[list, dict], member: discord.Member, *, timeouttalk: bool = True, prompt: str = None, embed: discord.Embed = None, cancel=False, timeout=120) -> Union[str, None]:
    if prompt is None and embed is None:
        raise ValueError("Provide a prompt or embed to add a select to")
    view = ListView(namestyles, member, ctx, timeout, timeouttalk, cancel)
    if prompt is not None:
        message = await ctx.send(prompt, view=view)
    elif embed is not None:
        message = await ctx.send(embed=embed, view=view)
    else:
        raise ValueError("Selected prompt and embed to False")
    await view.wait()
    await message.delete()
    return None if view.result is None else view.result


class SelectList(discord.ui.View):
    def __init__(self, options: list, placeholder: str, member: discord.Member, ctx: commands.Context, cancel: bool = False):
        super().__init__(timeout=120)
        self.placeholder = placeholder
        self.options = options
        self.member = member
        self.result = None
        self.ctx = ctx
        self.add_item(SelectListOption(placeholder, options, cancel))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This select menu is not for you.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        await self.ctx.send("Menu timed out, please try again.")


class SelectListOption(discord.ui.Select):
    def __init__(self, placeholder, pickers, cancel: bool):
        super().__init__(placeholder=placeholder)
        self.pickers = pickers
        for option in pickers:
            self.add_option(label=str(option))
        if cancel:
            self.add_option(label="Cancel", emoji="❌")

    async def callback(self, interaction: discord.Interaction):
        view: SelectList = self.view
        option = interaction.data['values'][0]
        if option == "Cancel":
            view.result = False
            await interaction.response.send_message('Cancelled prompt.', ephemeral=True)
            view.stop()
            return
        view.result = option
        await interaction.response.send_message(f"Selected `{option}`.", ephemeral=True)
        view.stop()


async def list_select(ctx: commands.Context, options: Union[list, dict], placeholder: str, member: discord.Member, *, prompt: str = None, embed: discord.Embed = None, cancel=False) -> Union[str, None]:
    if prompt is None and embed is None:
        raise ValueError("Provide a prompt or embed to add a select to")
    view = SelectList(options, placeholder, member, ctx, cancel)
    if prompt is not None:
        message = await ctx.send(prompt, view=view)
    elif embed is not None:
        message = await ctx.send(embed=embed, view=view)
    else:
        raise ValueError("Selected prompt and embed to False")
    await view.wait()
    await message.delete()
    return None if view.result is None else view.result
