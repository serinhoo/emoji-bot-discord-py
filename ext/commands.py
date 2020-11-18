import os
import requests
import difflib
import secrets

import discord
from discord.ext import commands

async def get_free_emoji_slots(guild):
    emojis = await guild.fetch_emojis()
    free_emoji_slots = guild.emoji_limit - len([emoji for emoji in emojis if not emoji.animated])
    free_animated_emoji_slots = guild.emoji_limit - len([emoji for emoji in emojis if emoji.animated])
    return free_emoji_slots, free_animated_emoji_slots

# https://emoji.gg/api/
class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        # Example structure of self.sessions
        # {'guild_id|user_id': {'api_state': [parsed results of https://emoji.gg/api/], 'message_id': int,'index': int}}
        # {'2372132131|1232321': {'api_state': [], 'message_id': 3247824234, 'index': 23}}

    @commands.guild_only()
    @commands.group(name='emoji', aliases=['e'])
    async def emoji_base(self, ctx):
        if ctx.invoked_subcommand is None:
            emojis = await ctx.guild.fetch_emojis()
            free_emoji_slots = ctx.guild.emoji_limit - len([emoji for emoji in emojis if not emoji.animated])
            free_animated_emoji_slots = ctx.guild.emoji_limit - len([emoji for emoji in emojis if emoji.animated])

            embed=discord.Embed(title="**Unknown Subcommand**", description="Here are all subcommands that are available to you. If you don't see some of them, you don't have sufficient permissions.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

            embed.add_field(name="**browse** [optional: name]", value="Opens emoji explorer and gives you an ability to browse and add emojis.", inline=True)
            embed.add_field(name="**rename** [old name] [new name]", value="Renames chosen emoji.", inline=True)

            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)

    @commands.has_guild_permissions(manage_emojis=True)
    @emoji_base.command(name='browse', aliases=['browser', 'list', 'b', 'l'])
    async def emoji_browse(self, ctx, *, arg=None):
        
        key = str(ctx.guild.id)+'|'+str(ctx.message.author.id)

        free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(ctx.guild)

        if key in self.sessions.keys():
            embed=discord.Embed(title="**You can't use this command now.**", description="You already have opened an emoji browser on this serwer. Close it first before proceeding.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)
            return

        # This takes some time. We will make bot "type" to show the user that he received this command and is running it.
        async with ctx.message.channel.typing():
            r = requests.get('https://emoji.gg/api/')
            available_emojis = r.json()

            if arg is not None:
                matching_titles = difflib.get_close_matches(word=arg, possibilities=[entry['title'] for entry in available_emojis], n=50, cutoff=0.5)
                available_emojis = [entry for entry in available_emojis if entry['title'] in matching_titles]

        if len(available_emojis) == 0:
            embed=discord.Embed(title="**Error while executing this command.**", fdescription="Bot has not found any emojis matching title `{arg}`. Try using something else.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)
            return
        
        entry = available_emojis[0]
        print(entry)

        embed = discord.Embed(
            title=f"**Choose emoji (1 of {len(available_emojis)})**", description="You can now choose emoji that you want to add to your server.\n Use :arrow_left: or :arrow_right: to cycle between emojis.\n Use :white_check_mark: to add current emoji to your server.\n Use :negative_squared_cross_mark: to end adding new emojis and close this session.\n After fifteen minutes session will close, embed will stop reacting and you will have to start new one using `^emoji browse`.", color=0x738adb)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=entry['image'])
        embed.set_image(url=entry['image'])
        embed.add_field(name="**Name:**", value=entry['title'], inline=True)
        embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
        embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")

        message = await ctx.send(embed=embed)

        # No need to display this if there is only one emoji.
        if(len(available_emojis) > 1):
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')
        await message.add_reaction('✅')
        await message.add_reaction('❎')

        self.sessions[key] = {'available_emojis': available_emojis, 'message_id': message.id, 'index': 0}


    @commands.has_guild_permissions(manage_emojis=True)
    @emoji_base.command(name='rename', aliases=['r'])
    async def emoji_rename(self, ctx, old_name=None, new_name=None):
        if old_name is None or new_name is None:
            await emoji_base(ctx)
        
        free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(ctx.guild)

        

        embed = discord.Embed(title=f"**Successfully renamed emoji!**", color=0x738adb)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.add_field(name="**Old name:**", value=old_name, inline=True)
        embed.add_field(name="**New name:**", value=new_name, inline=True)
        embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")


# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        key = str(reaction.message.channel.guild.id)+'|'+str(user.id)
        
        if key not in self.sessions:
            return
        if self.sessions[key]['message_id'] != reaction.message.id:
            return
        
        # Swipe to left
        if reaction.emoji == '⬅️':
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])
            await message.remove_reaction('⬅️', user)

            if self.sessions[key]['index'] - 1 < 0:
                return
            
            free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(reaction.message.channel.guild)

            available_emojis = self.sessions[key]['available_emojis']
            index = self.sessions[key]['index']-1
            entry = available_emojis[index]

            # Reassign index
            self.sessions[key]['index'] = index

            embed = discord.Embed(
                title=f"**Choose emoji ({index+1} of {len(available_emojis)})**", description="You can now choose emoji that you want to add to your server.\n Use :arrow_left: or :arrow_right: to cycle between emojis.\n Use :white_check_mark: to add current emoji to your server.\n Use :negative_squared_cross_mark: to end adding new emojis and close this session.\n After fifteen minutes session will close, embed will stop reacting and you will have to start new one using `^emoji browse`.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_thumbnail(url=entry['image'])
            embed.set_image(url=entry['image'])
            embed.add_field(name="**Name:**", value=entry['title'], inline=True)
            embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            

            await message.edit(embed=embed)


            return
        # Swipe to right
        if reaction.emoji == '➡️':
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])
            await message.remove_reaction('➡️', user)

            if self.sessions[key]['index'] + 1 > len(self.sessions[key]['available_emojis']):
                return
            
            free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(reaction.message.channel.guild)

            available_emojis = self.sessions[key]['available_emojis']
            index = self.sessions[key]['index']+1
            entry = available_emojis[index]

            # Reassign index
            self.sessions[key]['index'] = index

            embed = discord.Embed(
                title=f"**Choose emoji ({index+1} of {len(available_emojis)})**", description="You can now choose emoji that you want to add to your server.\n Use :arrow_left: or :arrow_right: to cycle between emojis.\n Use :white_check_mark: to add current emoji to your server.\n Use :negative_squared_cross_mark: to end adding new emojis and close this session.\n After fifteen minutes session will close, embed will stop reacting and you will have to start new one using `^emoji browse`.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_thumbnail(url=entry['image'])
            embed.set_image(url=entry['image'])
            embed.add_field(name="**Name:**", value=entry['title'], inline=True)
            embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])

            await message.edit(embed=embed)
                
            return
        # On emoji add (✅)
        if reaction.emoji == '✅':
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])
            await message.remove_reaction('✅', user)

            free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(reaction.message.channel.guild)

            available_emojis = self.sessions[key]['available_emojis']
            index = self.sessions[key]['index']
            entry = available_emojis[index]

            emoji_name = entry['title']+'_'+secrets.token_urlsafe(8)

            r = requests.get(entry['image'], stream=True)
            image = r.content

            try:
                emoji = await reaction.message.channel.guild.create_custom_emoji(name=emoji_name, image=image)
            except Exception as e:
                print(e)
                embed = discord.Embed(title=f"**Error while adding a new emoji.**", description="You can't add any more emojis as you have hit the limit for this server. If you need more slots, you can boost this server.", color=0x738adb)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
                embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")

                await reaction.message.channel.send(embed=embed)
                return


            embed = discord.Embed(title=f"**Added a new emoji!**", description=f"Added a new emoji ({emoji}) to your server!\n It is currently named `{emoji_name}` and you can rename it by using command `^emoji rename {emoji_name} [new_name].`", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_thumbnail(url=entry['image'])
            embed.set_image(url=entry['image'])
            embed.add_field(name="**Name:**", value=emoji_name, inline=True)
            embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
            
            free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(reaction.message.channel.guild)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            

            await reaction.message.channel.send(embed=embed)
                
            return
        # On emoji add (❎)
        if reaction.emoji == '❎':
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])
            await message.remove_reaction('❎', user)

            del self.sessions[key]

            await message.edit(content='Session closed.', suppress=True)


def setup(bot):
    bot.add_cog(CommandsCog(bot))
    print(f"Uruchomiono moduł {__name__}")


def teardown(bot):
    print(f"Wyłączono moduł {__name__}")
