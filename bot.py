import discord
from discord.ext import commands
from discord import ui, Option, Embed
from pymongo import MongoClient
import random
import dotenv
import os

dotenv.load_dotenv()

# MongoDB setup
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['matchmakerdb']

# Discord bot setup
intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

class ProfileModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Profile Setup")

        self.add_item(ui.InputText(label="Username"))
        self.add_item(ui.InputText(label="Call Me Name"))
        self.add_item(ui.InputText(label="Short Bio", style=discord.InputTextStyle.paragraph))

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

        self.add_item(ui.InputText(label="Lobby Name"))
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

async def job_autocomplete(ctx: discord.AutocompleteContext):
    jobs = db.jobs.find({'guild_id': ctx.interaction.guild.id})
    return [job['name'] for job in jobs if 'name' in job]


@bot.slash_command(name="profile", description="Setup your profile")
async def profile(ctx):
    await ctx.send_modal(ProfileModal())

@bot.slash_command(name="setjobs", description="Add jobs to your profile")
async def setjobs(ctx, job: Option(str, "Select a job", autocomplete=job_autocomplete)):
    db.profiles.update_one(
        {'user_id': ctx.author.id, 'guild_id': ctx.guild.id},
        {'$addToSet': {'jobs': job}},
        upsert=True
    )
    embed = Embed(title="Job Added", description=f"Job **{job}** added to your profile!", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="removejob", description="Remove jobs from your profile")
async def removejob(ctx, job: Option(str, "Select a job", autocomplete=job_autocomplete)):
    db.profiles.update_one(
        {'user_id': ctx.author.id, 'guild_id': ctx.guild.id},
        {'$pull': {'jobs': job}}
    )
    embed = Embed(title="Job Removed", description=f"Job **{job}** removed from your profile.", color=discord.Color.red())
    await ctx.respond(embed=embed)

@bot.slash_command(name="viewprofile", description="View a user's profile")
async def viewprofile(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    profile = db.profiles.find_one({'user_id': member.id, 'guild_id': ctx.guild.id})
    if profile:
        jobs = ", ".join(profile.get('jobs', []))
        status = profile.get('available', False)
        embed = Embed(title=f"{profile['username']}'s Profile", description=f"**Call Me:** {profile['call_me']}\n**Bio:** {profile['bio']}\n**Jobs:** {jobs}\n**Available:** {status}", color=discord.Color.blue())
        await ctx.respond(embed=embed)
    else:
        embed = Embed(title="Profile Not Found", description="The profile you are looking for does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)

@bot.slash_command(name="available", description="Set your availability")
async def available(ctx, status: bool):
    db.profiles.update_one(
        {'user_id': ctx.author.id, 'guild_id': ctx.guild.id},
        {'$set': {'available': status}}
    )
    embed = Embed(title="Availability Updated", description=f"Your availability is now set to {'available' if status else 'not available'}.", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="createlobby", description="Create a lobby")
async def createlobby(ctx):
    await ctx.send_modal(LobbyModal())

@bot.slash_command(name="joinlobby", description="Join a lobby")
async def joinlobby(ctx, lobby_name: str):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to join does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id in lobby['blocked_users']:
        embed = Embed(title="Access Denied", description="You are blocked from this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$addToSet': {'members': ctx.author.id}}
    )
    db.profiles.update_one(
        {'user_id': ctx.author.id, 'guild_id': ctx.guild.id},
        {'$set': {'available': False}}
    )
    embed = Embed(title="Lobby Joined", description=f"You have successfully joined the lobby **{lobby_name}**.", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="leavelobby", description="Leave a lobby")
async def leavelobby(ctx, lobby_name: str):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to leave does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$pull': {'members': ctx.author.id}}
    )
    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$addToSet': {'blocked_users': ctx.author.id}}
    )
    embed = Embed(title="Lobby Left", description=f"You have successfully left the lobby **{lobby_name}**.", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="kickfromlobby", description="Kick a member from a lobby")
async def kickfromlobby(ctx, lobby_name: str, member: discord.Member):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to kick the member from does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    if ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to kick members from this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$pull': {'members': member.id}}
    )
    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$addToSet': {'blocked_users': member.id}}
    )
    embed = Embed(title="Member Kicked", description=f"{member.mention} has been kicked from the lobby **{lobby_name}**.", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="createreqs", description="Create a ReqS")
async def createreq(ctx, lobby_name: str, job: Option(str, "Select a job", autocomplete=job_autocomplete)):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to create a ReqS for does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    db.reqs.insert_one({
        'lobby_name': lobby_name,
        'job': job,
        'creator_id': ctx.author.id,
        'guild_id': ctx.guild.id
    })
    embed = Embed(title="ReqS Created", description=f"ReqS for job **{job}** created in lobby **{lobby_name}**.", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="removereqs", description="Remove a ReqS")
async def removereq(ctx, lobby_name: str, job: Option(str, "Select a job", autocomplete=job_autocomplete)):
    db.reqs.delete_one({
        'lobby_name': lobby_name,
        'job': job,
        'creator_id': ctx.author.id,
        'guild_id': ctx.guild.id
    })
    embed = Embed(title="ReqS Removed", description=f"ReqS for job **{job}** removed from lobby **{lobby_name}**.", color=discord.Color.red())
    await ctx.respond(embed=embed)

@bot.slash_command(name="launch", description="Launch a lobby")
async def launch(ctx, lobby_name: str):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to launch does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    reqs = list(db.reqs.find({'lobby_name': lobby_name, 'guild_id': ctx.guild.id}))
    if len(reqs) == 0:
        embed = Embed(title="No ReqSes", description="No ReqSes found for this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    for req in reqs:
        job = req['job']
        profiles = list(db.profiles.find({'jobs': job, 'available': True, 'guild_id': ctx.guild.id}))
        if not profiles:
            await ctx.respond(f"No profiles available for job: {job}")
            continue
        
        member_id = random.choice(profiles)['user_id']
        member = ctx.guild.get_member(member_id)
        
        if member:
            embed = Embed(title="Member Matched", description=f"{member.mention} has been matched for job **{job}** in lobby **{lobby_name}**.", color=discord.Color.green())
            await ctx.respond(embed=embed)
            await member.send(f"You have been matched for job **{job}** in lobby **{lobby_name}**.")
        else:
            await ctx.respond(f"Could not find member with ID: {member_id}")

@bot.slash_command(name="uploadjobs", description="Upload a .txt file with the list of available jobs")
async def uploadjobs(ctx):
    class JobUploadModal(ui.Modal):
        def __init__(self):
            super().__init__(title="Upload Jobs")

            self.add_item(ui.InputText(label="Jobs", style=discord.InputTextStyle.paragraph, placeholder="Paste jobs here, one per line."))

        async def callback(self, interaction: discord.Interaction):
            jobs_text = self.children[0].value
            jobs = set(filter(None, map(str.strip, jobs_text.splitlines())))

            for job in jobs:
                db.jobs.update_one(
                    {'name': job, 'guild_id': interaction.guild.id},
                    {'$set': {'name': job, 'guild_id': interaction.guild.id}},
                    upsert=True
                )
            embed = Embed(title="Jobs Uploaded", description="The list of jobs has been uploaded and processed.", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    await ctx.send_modal(JobUploadModal())


@bot.slash_command(name="viewlobbystatus", description="View your current lobby status")
async def viewlobbystatus(ctx):
    lobbies = list(db.lobbies.find({'members': ctx.author.id, 'guild_id': ctx.guild.id}))
    if not lobbies:
        embed = Embed(title="No Lobbies", description="You are not currently in any lobbies.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    lobby_descriptions = []
    for lobby in lobbies:
        lobby_descriptions.append(f"**{lobby['name']}** - {lobby['description']}")
    embed = Embed(title="Current Lobbies", description="\n".join(lobby_descriptions), color=discord.Color.blue())
    await ctx.respond(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))
