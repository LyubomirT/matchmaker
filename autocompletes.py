import discord
from database import db

async def job_autocomplete(ctx: discord.AutocompleteContext):
    jobs = db.jobs.find({'guild_id': ctx.interaction.guild.id})
    return [job['name'] for job in jobs if 'name' in job and len(job['name']) <= 50]

async def myLobbies_autocomplete(ctx: discord.AutocompleteContext):
    lobbies = db.lobbies.find({'guild_id': ctx.interaction.guild.id})
    return [lobby['name'] for lobby in lobbies if 'name' in lobby and len(lobby['name']) <= 50]