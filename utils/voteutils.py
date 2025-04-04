import discord
import random

class VoteView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label='Register to vote', url="https://vote.gov"))

def vote_embed():
    embed = discord.Embed(title="🇺🇸 Register to vote today 🇺🇸", description="The United States ranks 31st among OCED countries in voter turnout. Nearly a third of Americans aren't even registered to vote. Yet trust in the governments at all levels remains at an all time low among American voters. We can't expect for change to happen on its own. We need to get active, be involved, and perform our civic duty that millions have fought and died for.", color=discord.Color.blue())
    embed.add_field(name="Learn how to make a difference", value="The first step to improving our democracy is participating in it. By registering to vote, you enable yourself to perform your civic duty and make your voice heard. Visit **vote.gov**, or click the button below to register to vote today.")
    return embed, VoteView()

def random_vote():
    r = random.random()
    if r>0.5:
        embed, view = vote_embed()
        return [embed, view]
    else:
        return None