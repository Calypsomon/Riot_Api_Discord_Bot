import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio
import requests
import sqlite3
from database import init_db, add_user, get_puuid
from riot_api import get_lp, get_rank, get_name

# Load environment variables from .env file
load_dotenv(override=True)

# Get the token from environment
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_KEY = os.getenv('RIOT_API_KEY') 
init_db()

handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # needed to access member lists (role.members, ctx.guild.members, etc.)

# Create bot instance
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    for guild in bot.guilds:
        await guild.fetch_members().flatten()

@bot.command()
async def join(ctx, var: str):
    # Nur ausführen wenn var 2-3 Zeichen lang ist
    if len(var) > 3 or len(var) < 2:
        await ctx.send('Teamname must contain 2-3 characters!')
        return

    role = discord.utils.get(ctx.guild.roles, name=var)

    if role is None:
        role = await ctx.guild.create_role(name=var, colour=discord.Colour.blue(), reason=f"Created by {ctx.author}")
        await ctx.send(f" joined {role.mention}!")
        await ctx.author.add_roles(role)
        await role.edit(hoist=True)

    elif role is not None:
        if role in ctx.author.roles:
            await ctx.send(f"youre part of this team already! {ctx.author.mention}")
            return
        elif role.colour in [r.colour for r in ctx.author.roles]:
            await ctx.send(f"youre part of another team already! {ctx.author.mention}")
            return
        sent_message = await ctx.send(f'{ctx.author.mention} wants to join {role.mention}!')
        await sent_message.add_reaction('✅')
        await sent_message.add_reaction('❌')

        # Prüfen: nur Reaktionen vom Nutzer, der die Rolle hat
        def check(reaction, user):
            if getattr(user, "bot", False):
                return False
            member = user if isinstance(user, discord.Member) else reaction.message.guild.get_member(user.id)
            return (
                member is not None
                and role in member.roles
                and reaction.message.id == sent_message.id
                and str(reaction.emoji) in ('✅', '❌')
            )

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            if reaction.emoji == '✅':
                await reaction.message.channel.send(f'{user.mention} Accepted!')
                if role.colour in [r.colour for r in ctx.author.roles]:
                    await ctx.send(f"youre part of another team already! {ctx.author.mention}")
                    return
                await ctx.author.add_roles(role)
        
            elif reaction.emoji == '❌':
                await reaction.message.channel.send(f'{user.mention} nvm!')
        except asyncio.TimeoutError:
            await sent_message.edit(content='Timed out!')

@bot.command()
async def leave(ctx, var: str):
    role = discord.utils.get(ctx.guild.roles, name=var)
    if role is None:
        await ctx.send(f"{var} does not exist!")
        return
    if role not in ctx.author.roles:
        await ctx.send(f"You are not part of {var}!")
        return
    if role in ctx.author.roles:
        await ctx.author.remove_roles(role)
        await ctx.send(f"You have left {var}!")
        # after the removal the member cache will reflect the change when intents.members
        # is enabled.  check truthiness instead of equality with list for clarity.
        if not role.members:
            await role.delete(reason=f"{ctx.author} was the last member, {var} got deleted.")
            await ctx.send(f"{ctx.author.mention} was the last member, {var} got deleted. RIP")

@bot.command()
async def connect(ctx, var,var2: str):
    sent_mesage = await ctx.send(f"Change your Profile Picture to rose in 3 seconds!")
    await asyncio.sleep(3)
    
    puuid_api_key = "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/" + str(var) + "/" + str(var2) + "?api_key=" + API_KEY
    puuid = requests.get(puuid_api_key).json()['puuid']
    pp_url_api_key = "https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/" + puuid + "?api_key=" + API_KEY
    picture_id = requests.get(pp_url_api_key).json()['profileIconId']
    if picture_id == 7:
        await sent_mesage.edit(content=f"Your Riot Account is Connected! {ctx.author.mention}")
        add_user(str(ctx.author.id), puuid)

    elif picture_id != 7:
        await sent_mesage.edit(content=f"Profile Picture is incorrect! {ctx.author.mention}")

@bot.command()
async def info(ctx):
    puuid = get_puuid(str(ctx.author.id))
    if puuid:
        await ctx.send(f"Your are connected whit {get_name(puuid)} {ctx.author.mention}")
        await ctx.send(f"You have {get_lp(puuid)} LP / {get_rank(get_lp(puuid))}")
    else:
        await ctx.send(f"You haven't connected your Riot Account yet! {ctx.author.mention}")

@bot.command()
async def teaminfo(ctx,var:str):
    combined_lp = 0
    count = 0
    rolle = discord.utils.get(ctx.guild.roles, name=var)
    for member in rolle.members:
        puuid = get_puuid(str(member.id))
        if puuid:
            await ctx.send(f"{member} is connected whit {get_name(puuid)} and has {get_lp(puuid)} LP")
            combined_lp += get_lp(puuid)
            count +=1
        else:
            await ctx.send(f"{member.mention} hasn't connected their Riot Account yet!")
    avg = combined_lp/count if count > 0 else 0
    await ctx.send(f"average LP of {rolle} = {avg} LP / {get_rank(avg)}")

@bot.command()
async def stats(ctx):
    statschannel = discord.utils.get(ctx.guild.text_channels, name="stats")
    if statschannel is None:
        await ctx.send("Could not find a channel named 'stats'.")
        return
    old_channel = statschannel
    new_channel = await old_channel.clone()
    await old_channel.delete()
    teams = []
    for role in ctx.guild.roles:
        if role.colour == discord.Colour.blue():
            teams.append(role)
    team_stats = []
    for team in teams:
        combined_lp = 0
        count = 0
        for member in team.members:
            puuid = get_puuid(str(member.id))
            if puuid:
                try:
                    lp = get_lp(puuid)
                except Exception:
                    # skip members we can't resolve (API error or unranked)
                    continue
                combined_lp += lp
                count += 1
        avg = combined_lp/count if count > 0 else 0
        team_stats.append((team.name, avg, team))
    team_stats.sort(key=lambda x: x[1], reverse=True)
    stats_message = "Team Rankings:\n"
    for i, (team_name, avg_lp, team) in enumerate(team_stats, start=1):
        stats_message += f"{i}. {team_name} - {avg_lp} LP / {get_rank(avg_lp)}\n"
        await team.edit(position=len(team_stats)-i+1)
    await new_channel.send(stats_message)


#/match erkennen, sucht in den letzten 5 games des spielers nach games welche von nur team membern gespielt wurden und speichert in matchhistory gewinner und verlierer 
#/ danach bei teaminfo und rating dei wr einfügen 





bot.run(DISCORD_TOKEN)


 