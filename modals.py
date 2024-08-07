import discord
from discord import ui
from discord import Embed
from database import db

class ProfileModal(ui.Modal):
    def __init__(self, runnerguild, runnerid):
        super().__init__(title="Profile Setup", timeout=1800)

        self.runnerguild = runnerguild
        self.runnerid = runnerid

        user_profile = db.profiles.find_one({'user_id': runnerid, 'guild_id': runnerguild})
        if user_profile:
            username = user_profile.get('username', '')
            call_me = user_profile.get('call_me', '')
            bio = user_profile.get('bio', '')
        else:
            username = ''
            call_me = ''
            bio = ''

        self.add_item(ui.InputText(label="Username", max_length=50, value=username))
        self.add_item(ui.InputText(label="Call Me Name", max_length=50, value=call_me))
        self.add_item(ui.InputText(label="Short Bio", style=discord.InputTextStyle.paragraph, max_length=512, value=bio))

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
        self.add_item(ui.InputText(label="Description", style=discord.InputTextStyle.paragraph, max_length=512))

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

class JobUploadModal(ui.Modal):
        def __init__(self):
            super().__init__(title="Upload Jobs")

            self.add_item(ui.InputText(label="Jobs", style=discord.InputTextStyle.paragraph, placeholder="Paste jobs here, one per line.", max_length=1000))

        async def callback(self, interaction: discord.Interaction):
            jobs_text = self.children[0].value
            jobs = set(filter(None, map(str.strip, jobs_text.splitlines())))

            for job in jobs:
                if len(job) <= 50:
                    db.jobs.update_one(
                        {'name': job, 'guild_id': interaction.guild.id},
                        {'$set': {'name': job, 'guild_id': interaction.guild.id}},
                        upsert=True
                    )
            embed = Embed(title="Jobs Uploaded", description="The list of jobs has been uploaded and processed.", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)

class JobRemoveModal(ui.Modal):
        def __init__(self):
            super().__init__(title="Remove Jobs")

            self.add_item(ui.InputText(label="Jobs", style=discord.InputTextStyle.paragraph, placeholder="Paste jobs here, one per line."))

        async def callback(self, interaction: discord.Interaction):
            jobs_text = self.children[0].value
            jobs = set(filter(None, map(str.strip, jobs_text.splitlines())))

            for job in jobs:
                db.jobs.delete_one({'name': job, 'guild_id': interaction.guild.id})
            embed = Embed(title="Jobs Removed", description="The listed jobs have been removed.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmKickEveryoneModal(ui.Modal):
    def __init__(self, id=None):
        super().__init__(title="Are you sure? This action is irreversible.")
        self.id = id

        self.add_item(ui.InputText(label="Dummy", placeholder="This is a dummy input to make the modal work.", required=False))

    async def callback(self, interaction: discord.Interaction):
        lobby_id = self.id
        # debug print the contents of the lobby
        print(db.lobbies.find_one({'_id': lobby_id}))
        # message all members that they have been kicked
        for member in db.lobbies.find_one({'_id': lobby_id})['members']:
            user = interaction.guild.get_member(member)
            await user.send(f"You have been kicked from the lobby.")
        db.lobbies.update_one({'_id': lobby_id}, {'$set': {'members': []}})
        embed = Embed(title="Kicked Everyone", description="Everyone has been kicked from the lobby.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmDeleteProfileModal(ui.Modal):
    def __init__(self, id=None):
        super().__init__(title="Are you sure? This action is irreversible.")
        self.id = id

        self.add_item(ui.InputText(label="Dummy", placeholder="This is a dummy input to make the modal work.", required=False))

    async def callback(self, interaction: discord.Interaction):
        profile_id = self.id
        db.profiles.delete_one({'_id': profile_id})
        embed = Embed(title="Profile Deleted", description="Your profile has been successfully deleted.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)