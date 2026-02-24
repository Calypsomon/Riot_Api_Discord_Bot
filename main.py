import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables from .env file
load_dotenv()

# Get the token from environment
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

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
                await reaction.message.channel.send(f'{user.mention} Joined!')
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
        if role.members == []:
            await role.delete(reason=f"{ctx.author} was the last member, {var} got deleted.")
            await ctx.send(f"{ctx.author.mention} was the last member, {var} got deleted. RIP")

bot.run(DISCORD_TOKEN)



