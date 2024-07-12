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
        # this is a simple boolean
        embed = Embed(title="Availability Toggled", description=f"Your availability has been set to **{'available' if availability else 'unavailable'}**.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)