import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio
import requests
import sqlite3
from database import init_db, add_user, get_puuid

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
    # make sure member cache is populated; the privileged "Server Members Intent"
    # must also be enabled in the bot's application settings on the Discord
    # developer portal.
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
        name_api_key = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={API_KEY}"
        name = requests.get(name_api_key).json()['gameName']
        tag = requests.get(name_api_key).json()['tagLine']
        await ctx.send(f"Your are connected whit {name}#{tag} {ctx.author.mention}")
        await ctx.send(f"You have {get_lp(puuid)} LP {ctx.author.mention}")
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
            name_api_key = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={API_KEY}"
            name = requests.get(name_api_key).json()['gameName']
            tag = requests.get(name_api_key).json()['tagLine']
            await ctx.send(f"{member} is connected whit {name}#{tag} and has {get_lp(puuid)} LP")
            combined_lp += get_lp(puuid)
            count +=1
        else:
            await ctx.send(f"{member.mention} hasn't connected their Riot Account yet!")
    avg = combined_lp/count if count > 0 else 0
    await ctx.send(f"average LP of {rolle} = {avg} LP / {get_rank(avg)}")


def get_lp(puuid):
    lp_api_key = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}?api_key={API_KEY}"
    entries = requests.get(lp_api_key).json()
    solo_rank = None
    for entry in entries:
        if entry['queueType'] ==  "RANKED_SOLO_5x5":
            solo_rank = entry
    if solo_rank['tier'] == "IRON":
        x= 0
    elif solo_rank['tier'] == "BRONZE":
        x= 400
    elif solo_rank['tier'] == "SILVER":
        x= 800
    elif solo_rank['tier'] == "GOLD":
        x= 1200
    elif solo_rank['tier'] == "PLATINUM":
        x= 1600
    elif solo_rank['tier'] == "EMERALD":
        x= 2000 
    elif solo_rank['tier'] == "DIAMOND":
        x= 2400
    elif solo_rank['tier'] == "MASTER":
        x= 2800
    elif solo_rank['tier'] == "GRANDMASTER":
        x= 3200
    elif solo_rank['tier'] == "CHALLENGER":
        x= 3600
    if solo_rank['rank'] == "IV":
        y= 0
    elif solo_rank['rank'] == "III":
        y= 100
    elif solo_rank['rank'] == "II":
        y= 200
    elif solo_rank['rank'] == "I":
        y= 300
    lp = x + y + solo_rank['leaguePoints']
    return lp

def get_rank(lp):
    rank = lp/400
    tier = (lp%400)/100
    ranks = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM","EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    tiers = ["IV", "III", "II", "I"]
    return f"{ranks[int(rank)]} {tiers[int(tier)]}"
        

#/rating einführen , postet eine nachricht in den teamratings channel mit allen teams in reienfolge und sortiert rechts team nach platz 
#/match erkennen, sucht in den letzten 5 games des spielers nach games welche von nur team membern gespielt wurden und speichert in matchhistory gewinner und verlierer 
#/ danach bei teaminfo und rating dei wr einfügen 





bot.run(DISCORD_TOKEN)


