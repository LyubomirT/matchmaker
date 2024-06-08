import discord
from discord.ext import commands
from discord import ui, Option, Embed
from pymongo import MongoClient
import random
import dotenv
import os
from modals import ProfileModal, LobbyModal, JobUploadModal, JobRemoveModal, ConfirmKickEveryoneModal
from database import db
import asyncio
from autocompletes import job_autocomplete, myLobbies_autocomplete
from helpfile import helpstr


dotenv.load_dotenv()

# Discord bot setup
intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.slash_command(name="help", description="Get help with the bot")
async def help(ctx):
    embed = Embed(title="Matchmaker Bot Help", description=helpstr, color=discord.Color.blue())
    await ctx.respond(embed=embed)

@bot.slash_command(name="profile", description="Setup your profile")
async def profile(ctx):
    await ctx.send_modal(ProfileModal())

@bot.slash_command(name="setjobs", description="Add jobs to your profile")
async def setjobs(ctx, job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
    if not db.jobs.find_one({'name': job, 'guild_id': ctx.guild.id}):
        embed = Embed(title="Job Not Found", description="The job you are trying to add does not exist or is not set up in the server.", color=discord.Color.red())
    db.profiles.update_one(
        {'user_id': ctx.author.id, 'guild_id': ctx.guild.id},
        {'$addToSet': {'jobs': job}},
        upsert=True
    )
    embed = Embed(title="Job Added", description=f"Job **{job}** added to your profile!", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="removejob", description="Remove jobs from your profile")
async def removejob(ctx, job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
    if not db.jobs.find_one({'name': job, 'guild_id': ctx.guild.id}):
        embed = Embed(title="Job Not Found", description="The job you are trying to remove does not exist or is not set up in the server.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

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
        # Check if user's jobs are still valid
        valid_jobs = []
        for job in profile.get('jobs', []):
            if db.jobs.find_one({'name': job, 'guild_id': ctx.guild.id}):
                valid_jobs.append(job)
        # Update user's profile with valid jobs
        db.profiles.update_one(
            {'user_id': member.id, 'guild_id': ctx.guild.id},
            {'$set': {'jobs': valid_jobs}}
        )
        jobs = ", ".join(valid_jobs)
        embed = Embed(title=f"{profile['username']}'s Profile", color=discord.Color.blue())
        embed.set_thumbnail(url=member.avatar)
        embed.add_field(name="Call Me", value=profile['call_me'], inline=False)
        embed.add_field(name="Bio", value=profile['bio'], inline=False)
        embed.add_field(name="Jobs", value=jobs, inline=False)
        embed.add_field(name="Available", value="Yes" if status else "No", inline=False)
        activityrank = db.messages.find_one({'user_id': member.id, 'guild_id': ctx.guild.id})
        if activityrank:
            embed.add_field(name="Message Count", value=activityrank['message_count'], inline=False)
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
async def leavelobby(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete))):
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
async def kickfromlobby(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete)), member: discord.Member):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to kick the member from does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if member.id not in lobby['members']:
        embed = Embed(title="Member Not Found", description="The member you are trying to kick is not in this lobby.", color=discord.Color.red())
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
async def createreq(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete)), job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to create a ReqS for does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    if db.reqs.count_documents({'lobby_name': lobby_name, 'guild_id': ctx.guild.id}) >= 25:
        embed = Embed(title="ReqS Limit Reached", description="This lobby has reached the maximum number of ReqSes (25).", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if not db.jobs.find_one({'name': job, 'guild_id': ctx.guild.id}):
        embed = Embed(title="Job Not Found", description="The job you are trying to create a ReqS for does not exist or is not set up in the server.", color=discord.Color.red())
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
async def removereq(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete)), job: Option(str, "Select a job", autocomplete=discord.utils.basic_autocomplete(job_autocomplete))):
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
async def launch(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete))):
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
            try:
                await member.send(f"You have been matched for job **{job}** in lobby **{lobby_name}**.")
            except discord.Forbidden:
                await ctx.respond("I couldn't send a message to the matched member. Seems like they have DMs disabled.")
        else:
            await ctx.respond(f"Could not find member with ID: {member_id}")

@bot.slash_command(name="uploadjobs", description="Upload a .txt file with the list of available jobs")
async def uploadjobs(ctx, file: discord.Attachment):
    # if not the server owner, return
    if ctx.author.id != ctx.guild.owner_id:
        embed = Embed(title="Permission Denied", description="You do not have permission to upload jobs (only the server owner can).", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    jobs = list(db.jobs.find({'guild_id': ctx.guild.id}))
    job_names = [job['name'] for job in jobs if 'name' in job]
    total_length = sum(len(job_name) for job_name in job_names)
    if total_length >= 5000:
        embed = Embed(title="Job Limit Exceeded", description="The list of jobs has reached the maximum character limit.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    # if not txt file, return
    if file.filename.split('.')[-1] != 'txt':
        embed = Embed(title="Invalid File Type", description="You can only upload .txt files.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    jobs_text = file.fp.read().decode('utf-8')
    jobs = set(filter(None, map(str.strip, jobs_text.splitlines())))
    for job in jobs:
        if len(job) <= 50:
            db.jobs.update_one(
                {'name': job, 'guild_id': ctx.guild.id},
                {'$set': {'name': job, 'guild_id': ctx.guild.id}},
                upsert=True
            )
    embed = Embed(title="Jobs Uploaded", description="The list of jobs has been uploaded and processed.", color=discord.Color.green())
    await ctx.respond(embed=embed)

@bot.slash_command(name="removelists", description="Upload a .txt file with the list of jobs to remove")
async def removelists(ctx, file: discord.Attachment):
    # if not the server owner, return
    if ctx.author.id != ctx.guild.owner_id:
        embed = Embed(title="Permission Denied", description="You do not have permission to remove jobs (only the server owner can).", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    # if not txt file, return
    if file.filename.split('.')[-1] != 'txt':
        embed = Embed(title="Invalid File Type", description="You can only upload .txt files.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    jobs_text = file.fp.read().decode('utf-8')
    jobs = set(filter(None, map(str.strip, jobs_text.splitlines())))
    for job in jobs:
        db.jobs.delete_one({'name': job, 'guild_id': ctx.guild.id})
    embed = Embed(title="Jobs Removed", description="The listed jobs have been removed.", color=discord.Color.red())
    await ctx.respond(embed=embed)

@bot.slash_command(name="viewjobs", description="View the list of available jobs in the server")
async def viewjobs(ctx):
    jobs = list(db.jobs.find({'guild_id': ctx.guild.id}))
    if not jobs:
        embed = Embed(title="No Jobs", description="There are no jobs currently available.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    job_names = [job['name'] for job in jobs if 'name' in job]
    chunk_size = 1000
    chunks = [job_names[i:i+chunk_size] for i in range(0, len(job_names), chunk_size)]

    for chunk in chunks:
        embed = Embed(title="Available Jobs", description="\n".join(chunk), color=discord.Color.blue())
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
async def lobbyinfo(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete))):
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

@bot.slash_command(name="blockuser", description="Block a user from a lobby")
async def blockuser(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete)), member: discord.Member):
    lobby = db.lobbies.find_one
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to block the user from does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to block users from this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$addToSet': {'blocked_users': member.id}}
    )

    # also remove the user from the lobby
    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$pull': {'members': member.id}}
    )

    embed = Embed(title="User Blocked", description=f"{member.mention} has been blocked from the lobby **{lobby_name}**.", color=discord.Color.red())
    try:
        await member.send(f"You have been blocked from the lobby **{lobby_name}**.")
    except discord.Forbidden:
        embed.description += " (User has DMs disabled)"
    await ctx.respond(embed=embed)

@bot.slash_command(name="unblockuser", description="Unblock a user from a lobby")
async def unblockuser(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete)), member: discord.Member):
    lobby = db.lobbies.find_one
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to unblock the user from does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to unblock users from this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    db.lobbies.update_one(
        {'name': lobby_name, 'guild_id': ctx.guild.id},
        {'$pull': {'blocked_users': member.id}}
    )
    embed = Embed(title="User Unblocked", description=f"{member.mention} has been unblocked from the lobby **{lobby_name}**.", color=discord.Color.green())
    try:
        await member.send(f"You have been unblocked from the lobby **{lobby_name}**.")
    except discord.Forbidden:
        embed.description += " (User has DMs disabled)"
    await ctx.respond(embed=embed)

@bot.slash_command(name="announce", description="Announce a message to all members in a lobby")
async def announce(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete)), message: str):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to announce a message to does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id not in lobby['members'] and ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to announce a message to this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    members = [ctx.guild.get_member(member_id) for member_id in lobby['members']]
    member_mentions = [member.mention for member in members if member]

    embed = Embed(title=f"Announcement from {ctx.author}", description=message, color=discord.Color.blue())
    embed.set_footer(text=f"If the user has DMs disabled, they will not receive this message.")
    await ctx.respond(f"Announcement sent to {', '.join(member_mentions)}")
    for member in members:
        try:
            await member.send(embed=embed)
            asyncio.sleep(1)
        except discord.Forbidden:
            pass
    
@bot.slash_command(name="kickeveryone", description="Kick everyone from a lobby (DANGEROUS)")
async def kickeveryone(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete))):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to kick everyone from does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to kick everyone from this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    await ctx.send_modal(ConfirmKickEveryoneModal(lobby['_id']))

@bot.slash_command(name="deletelobby", description="Delete a lobby")
async def deletelobby(ctx, lobby_name: Option(str, "Select a lobby", autocomplete=discord.utils.basic_autocomplete(myLobbies_autocomplete))):
    lobby = db.lobbies.find_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    if not lobby:
        embed = Embed(title="Lobby Not Found", description="The lobby you are trying to delete does not exist.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return
    
    if ctx.author.id != lobby['creator_id']:
        embed = Embed(title="Permission Denied", description="You do not have permission to delete this lobby.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    db.lobbies.delete_one({'name': lobby_name, 'guild_id': ctx.guild.id})
    embed = Embed(title="Lobby Deleted", description=f"Lobby **{lobby_name}** has been successfully deleted.", color=discord.Color.red())
    # message all members that the lobby has been deleted
    try:
        for member in lobby['members']:
            user = ctx.guild.get_member(member)
            await user.send(f"The lobby **{lobby_name}** has been deleted.")
    except:
        pass
    # also delete all ReqSes for this lobby
    db.reqs.delete_many({'lobby_name': lobby_name, 'guild_id': ctx.guild.id})
    await ctx.respond(embed=embed)

# add a listener for when the bot is ready
@bot.event
async def on_ready():
    greenansi = "\033[92m"
    resetansi = "\033[0m"
    print(f"{greenansi}Bot is ready!{resetansi}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # init the table if it doesn't exist
    if 'messages' not in db.list_collection_names():
        db.create_collection('messages')
    # here we add the amount of messages (not the content) to the database (per-user on a per-guild basis)
    db.messages.update_one(
        {'user_id': message.author.id, 'guild_id': message.guild.id},
        {'$inc': {'message_count': 1}},
        upsert=True
    )

@bot.slash_command(name="messagecount", description="Get the amount of messages you've sent in this server")
async def messagecount(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    message_count = db.messages.find_one({'user_id': member.id, 'guild_id': ctx.guild.id})
    if message_count:
        embed = Embed(title="Message Count", description=f"{member.mention} has sent {message_count['message_count']} messages in this server.", color=discord.Color.blue())
        await ctx.respond(embed=embed)
    else:
        embed = Embed(title="Message Count", description=f"{member.mention} has not sent any messages in this server.", color=discord.Color.red())
        await ctx.respond(embed=embed)

@bot.slash_command(name="activityleaderboard", description="Get the top 10 most active users in this server")
async def activityleaderboard(ctx):
    message_counts = list(db.messages.find({'guild_id': ctx.guild.id}).sort('message_count', -1).limit(10))
    if not message_counts:
        embed = Embed(title="Activity Leaderboard", description="There are no message counts available for this server.", color=discord.Color.red())
        await ctx.respond(embed=embed)
        return

    leaderboard = []
    for count in message_counts:
        user = ctx.guild.get_member(count['user_id'])
        if user:
            leaderboard.append(f"{user.mention} - {count['message_count']} messages")
    embed = Embed(title="Activity Leaderboard", description="\n".join(leaderboard), color=discord.Color.blue())
    await ctx.respond(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))
