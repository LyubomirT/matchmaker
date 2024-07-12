import discord
from discord import ui
from discord import Embed
from database import db

class ProfileView(ui.View):
    def __init__(self):
        super().__init__()

        self.add_item(ToggleAvailabilityButton())
    
    async def on_timeout(self):
        pass


class ToggleAvailabilityButton(ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Toggle Availability")

    async def callback(self, interaction: discord.Interaction):
        user = db.profiles.find_one({'user_id': interaction.user.id, 'guild_id': interaction.guild.id})
        availability = not user.get('available', False)
        db.profiles.update_one({'user_id': interaction.user.id, 'guild_id': interaction.guild.id}, {'$set': {'available': availability}})
        # this is a simple boolean
        embed = Embed(title="Availability Toggled", description=f"Your availability has been set to **{'available' if availability else 'unavailable'}**.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)