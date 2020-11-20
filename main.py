import os

import discord
from discord.ext import commands


def get_command_prefix(bot, message):
    # Prefixy na które bot odpowiada
    prefixes = ['^']
    return commands.when_mentioned_or(*prefixes)(bot, message)

bot = commands.Bot(command_prefix=get_command_prefix)

@bot.event
async def on_ready():
    print(f'\n---\nNazwa bota: {bot.user.name} (ID: {bot.user.id})')
    print(f'Wersja discord.py: {discord.__version__}')
    print(f'Invite link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=1074079808&scope=bot\n---\n')

    bot.load_extension('ext.commands')

@bot.event
async def on_message(message):
    if message.guild == None:
        print(message.content)
    await bot.process_commands(message)

# On Windows you can set your token by running `setx EMOJI_BOT_TOKEN your_token` in terminal
# If it doesn't work, then reboot your system
token = os.getenv('EMOJI_BOT_TOKEN')

bot.run(token)
