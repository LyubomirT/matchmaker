import discord
from discord import ui
from discord import Embed
from database import db

class ProfileModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Profile Setup")

        self.add_item(ui.InputText(label="Username", max_length=50))
        self.add_item(ui.InputText(label="Call Me Name", max_length=50))
        self.add_item(ui.InputText(label="Short Bio", style=discord.InputTextStyle.paragraph, max_length=512))

    async def callback(self, interaction: discord.Interaction):
        username = self.children[0].value
        call_me = self.children[1].value
        bio = self.children[2].value

        db.profiles.update_one(
            {'user_id': interaction.user.id, 'guild_id': interaction.guild.id},
            {'$set': {'username': username, 'call_me': call_me, 'bio': bio}},
            upsert=True
        )
        embed = Embed(title="Profile Updated", description="Your profile has been successfully updated!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LobbyModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Create Lobby")

        self.add_item(ui.InputText(label="Lobby Name", max_length=50))
        self.add_item(ui.InputText(label="Description", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        name = self.children[0].value
        description = self.children[1].value

        db.lobbies.insert_one({
            'name': name,
            'description': description,
            'creator_id': interaction.user.id,
            'guild_id': interaction.guild.id,
            'members': [],
            'blocked_users': []
        })
        embed = Embed(title="Lobby Created", description=f"Lobby **{name}** has been successfully created!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)