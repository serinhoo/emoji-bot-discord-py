import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

def get_command_prefix(bot, message):
    # Prefixy na które bot odpowiada
    prefixes = ['^']
    return commands.when_mentioned_or(*prefixes)(bot, message)


bot = commands.Bot(command_prefix=get_command_prefix, intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'\n---\nNazwa bota: {bot.user.name} (ID: {bot.user.id})')
    print(f'Wersja discord.py: {discord.__version__}')
    print(f'Invite link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=1074079808&scope=bot\n---')
    for guild in bot.guilds:
        print(f'[{guild.id}] {guild.name} ({guild.owner.name}#{guild.owner.discriminator})')
    print(f'---\n')

    bot.load_extension('ext.commands')

@bot.event
async def on_message(message):
    if message.guild is None:
        print(message.content)
    await bot.process_commands(message)

load_dotenv(override=True)

token = os.getenv('EMOJI_BOT_TOKEN')

bot.run(token)
