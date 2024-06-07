import discord
from discord.ext import commands
from discord import ui, Option, Embed
from pymongo import MongoClient
import random
import dotenv
import os
from modals import ProfileModal, LobbyModal, JobUploadModal, JobRemoveModal
from database import db

dotenv.load_dotenv()

# Discord bot setup
intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)



async def job_autocomplete(ctx: discord.AutocompleteContext):
    jobs = db.jobs.find({'guild_id': ctx.interaction.guild.id})
    return [job['name'] for job in jobs if 'name' in job and len(job['name']) <= 50]

async def myLobbies_autocomplete(ctx: discord.AutocompleteContext):
    lobbies = db.lobbies.find({'guild_id': ctx.interaction.guild.id})
    return [lobby['name'] for lobby in lobbies if 'name' in lobby and len(lobby['name']) <= 50]

@bot.slash_command(name="profile", description="Setup your profile")
async def profile(ctx):
    await ctx.send_modal(ProfileModal())

@bot.slash_command(name="setjobs", description="Add jobs to your profile")
async def setjobs(ctx, job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
    db.profiles.update_one(
        {'user_id': ctx.author.id, 'guild_id': ctx.guild.id},
        {'$addToSet': {'jobs': job}},
        upsert=True
    )
    embed = Embed(title="Job Added", description=f"Job **{job}** added to your profile!", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="removejob", description="Remove jobs from your profile")
async def removejob(ctx, job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
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
async def joinlobby(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete))):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to join does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id in lobby['members']:
        embed = Embed(title="Already Joined", description="You are already a member of this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id in lobby['blocked_users']:
        embed = Embed(title="Access Denied", description="You are blocked from this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    # check if there is space (amount of members must not be higher than amount of reqs + 1)
    reqs = db.reqs.count_documents({'lobby_name': lobby_name, 'guild_id': ctx.guild.id})
    if len(lobby['members']) >= reqs + 1:
        embed = Embed(title="Lobby Full", description="This lobby is already full.", color=discord.Color.red())
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
async def createreq(ctx, lobby_name: str, job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to create a ReqS for does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    if db.reqs.count_documents({'lobby_name': lobby_name, 'guild_id': ctx.guild.id}) >= 25:
        embed = Embed(title="ReqS Limit Reached", description="This lobby has reached the maximum number of ReqSes (25).", color=discord.Color.red())
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
async def removereq(ctx, lobby_name: str, job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
    if not db.reqs.find_one({'lobby_name': lobby_name, 'job': job, 'creator_id': ctx.author.id, 'guild_id': ctx.guild.id}):
        embed = Embed(title="ReqS Not Found", description="The ReqS you are trying to remove does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    if not db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id}):
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to remove a ReqS from does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
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
    
    if ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to launch this lobby.", color=discord.Color.red())
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
    # if not the server owner, return
    if ctx.author.id != ctx.guild.owner_id:
        embed = Embed(title="Permission Denied", description="You do not have permission to upload jobs (only the server owner can).", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    await ctx.send_modal(JobUploadModal())

@bot.slash_command(name="removelists", description="Upload a .txt file with the list of jobs to remove")
async def removelists(ctx):
    # if not the server owner, return
    if ctx.author.id != ctx.guild.owner_id:
        embed = Embed(title="Permission Denied", description="You do not have permission to remove jobs (only the server owner can).", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    await ctx.send_modal(JobRemoveModal())

@bot.slash_command(name="viewjobs", description="View the list of available jobs in the server")
async def viewjobs(ctx):
    jobs = list(db.jobs.find({'guild_id': ctx.guild.id}))
    if not jobs:
        embed = Embed(title="No Jobs", description="There are no jobs currently available.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    job_names = [job['name'] for job in jobs if 'name' in job]
    embed = Embed(title="Available Jobs", description="\n".join(job_names), color=discord.Color.blue())
    await ctx.respond(embed=embed)

@bot.slash_command(name="mylobbies", description="View all your current lobbies")
async def viewlobbystatus(ctx):
    lobbies = list(db.lobbies.find({'$or': [{'members': ctx.author.id}, {'creator_id': ctx.author.id}], 'guild_id': ctx.guild.id}))
    if not lobbies:
        embed = Embed(title="No Lobbies", description="You are not currently in any lobbies.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    lobby_descriptions = []
    for lobby in lobbies:
        lobby_descriptions.append(f"**{lobby['name']}** - {lobby['description']}")
    embed = Embed(title="Current Lobbies", description="\n".join(lobby_descriptions), color=discord.Color.blue())
    await ctx.respond(embed=embed) 

@bot.slash_command(name="lobbyinfo", description="View information about a lobby (and its members)")
async def lobbyinfo(ctx, lobby_name: str):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to view does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    members = [ctx.guild.get_member(member_id) for member_id in lobby['members']]
    owner = ctx.guild.get_member(lobby['creator_id'])
    member_mentions = [member.mention for member in members if member]
    embed = Embed(title=f"{lobby_name} Information", description=f"**Description:** {lobby['description']}\n**Members:** {', '.join(member_mentions)}\n**Owner:** {owner.mention}", color=discord.Color.blue())
    await ctx.respond(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))
