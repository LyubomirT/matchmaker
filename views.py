import discord
from discord import ui
from discord import Embed
from database import db

class ProfileView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=1800)
        self.owner_id = owner_id

        self.add_item(ToggleAvailabilityButton(owner_id=owner_id))
    
    async def on_timeout(self):
        await self.message.reply("Something went wrong. Please try again.")


class ToggleAvailabilityButton(ui.Button):
    def __init__(self, **kwargs):
        super().__init__(style=discord.ButtonStyle.primary, label="Toggle Availability")
        self.owner_id = kwargs.get('owner_id')

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            embed = Embed(title="Permission Denied", description="You do not have permission to toggle availability as you are not the owner of this profile.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        user = db.profiles.find_one({'user_id': interaction.user.id, 'guild_id': interaction.guild.id})
        availability = not user.get('available', False)
        db.profiles.update_one({'user_id': interaction.user.id, 'guild_id': interaction.guild.id}, {'$set': {'available': availability}})
        embed = Embed(title="Availability Toggled", description=f"Your availability has been set to **{'available' if availability else 'unavailable'}**.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    

class JobsPaginatedView(ui.View):
    def __init__(self, jobs):
        super().__init__(timeout=1800)
        self.jobs = jobs
        self.current_page = 0
        self.message = None
        self.add_item(StartBrowseButton())

    async def update_message(self, interaction: discord.Interaction):
        jobs = self.jobs[self.current_page]
        embed = discord.Embed(title="Jobs", description="Here are the jobs available for you to apply to on this server.", color=discord.Color.blurple())
        for job in jobs:
            embed.description += f"\n- {job}"
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.jobs)}")
        await interaction.response.edit_message(embed=embed, view=self)

class PreviousButton(ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Previous")

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.current_page = max(0, view.current_page - 1)
        await view.update_message(interaction)

class NextButton(ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Next")

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.current_page = min(len(view.jobs) - 1, view.current_page + 1)
        await view.update_message(interaction)

class StartBrowseButton(ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Start Browsing")

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.clear_items()
        view.add_item(PreviousButton())
        view.add_item(NextButton())
        await view.update_message(interaction)
