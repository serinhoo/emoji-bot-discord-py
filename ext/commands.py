import secrets
import time

import discord
import requests
from discord.ext import commands, tasks
from fuzzywuzzy import fuzz


async def get_free_emoji_slots(guild):
    free_emoji_slots = guild.emoji_limit - len([emoji for emoji in guild.emojis if not emoji.animated])
    free_animated_emoji_slots = guild.emoji_limit - len([emoji for emoji in guild.emojis if emoji.animated])
    return free_emoji_slots, free_animated_emoji_slots

# https://emoji.gg/api/
class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        # Example structure of self.sessions
        # {'guild_id|user_id': {'api_state': [parsed results of https://emoji.gg/api/], 'message_id': int,'index': int, 'timeout:' int}}
        # {'2372132131|1232321': {'api_state': [], 'message_id': 3247824234, 'index': 23, 'timeout': 1609532770}}
        self.check_sessions.start()

# --------------------------------------------------------------------------------------

    @commands.guild_only()
    @commands.group(name='emoji', aliases=['emote', 'e'])
    async def emoji_base(self, ctx):
        if ctx.invoked_subcommand is None:
            free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(ctx.guild)

            embed=discord.Embed(title="**Unknown Subcommand**", description="Here are all subcommands that are available to you. If you don't see some of them, you don't have sufficient permissions.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

            embed.add_field(name="**browse** [optional: name]", value="Opens emoji explorer and gives you an ability to browse and add emojis.", inline=True)
            embed.add_field(name="**rename** [old name] [new name]", value="Renames chosen emoji.", inline=True)
            embed.add_field(name="**upload**", value="Uploads a new emoji. It should be used while uploading an image or images.")

            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)

# --------------------------------------------------------------------------------------

    @commands.has_guild_permissions(manage_emojis=True)
    @emoji_base.command(name='browse', aliases=['browser', 'list', 'search', 'b', 'l', 's'])
    async def emoji_browse(self, ctx, *, arg: str=None):
        if arg is None:
            await ctx.send('You need to specify what emoji are you searching for.\n `^emoji search [name]`')
            return
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
            emojis = r.json()
            for emoji in emojis:
                emoji['score'] = fuzz.ratio(emoji['title'], arg)
            emojis.sort(reverse=True, key=lambda x: x['score'])
            emojis = emojis[:50]

        if len(emojis) == 0:
            embed=discord.Embed(title="**Error while executing this command.**", description=f"Bot has not found any emojis matching title `{arg}`. Try using something else.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)
            return
        
        entry = emojis[0]

        embed = discord.Embed(
            title=f"**Choose emoji (1 of {len(emojis)})**", description="You can now choose emoji that you want to add to your server.\nYou have 10 minutes to look through the catalog, after that time passes the session will time out.\n\n Use :arrow_left: or :arrow_right: to cycle between emojis.\n Use :white_check_mark: to add current emoji to your server.\n Use :negative_squared_cross_mark: to end adding new emojis and close this session.\n After fifteen minutes session will close, embed will stop reacting and you will have to start new one using `^emoji browse`.", color=0x738adb)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=entry['image'])
        embed.add_field(name="**Name:**", value=entry['title'], inline=True)
        embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
        embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.", icon_url=entry['image'])

        message = await ctx.send(embed=embed)

        # No need to display this if there is only one emoji.
        if(len(emojis) > 1):
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')
        await message.add_reaction('✅')
        await message.add_reaction('❎')

        self.sessions[key] = {'available_emojis': emojis, 'message_id': message.id, 'index': 0, 'timeout': int(time.time())+600}

    @commands.has_guild_permissions(manage_emojis=True)
    @emoji_base.command(name='rename', aliases=['r'])
    async def emoji_rename(self, ctx, old_name=None, new_name=None):
        if old_name is None or new_name is None:
            await self.emoji_base(ctx)
        
        free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(ctx.guild)

        emoji_to_rename = None
        for emoji in ctx.guild.emojis:
            if emoji.name == old_name:
                emoji_to_rename = emoji
                break
        
        if emoji_to_rename is None:
            embed=discord.Embed(title="**Error while executing this command.**", description=f"There is no emoji named `{old_name}`.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)
            return

        await emoji_to_rename.edit(name=new_name)

        embed = discord.Embed(title=f"**Successfully renamed emoji!**", color=0x738adb)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.add_field(name="**Old name:**", value=old_name, inline=True)
        embed.add_field(name="**New name:**", value=new_name, inline=True)
        embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")

        await ctx.send(embed=embed)

    @commands.has_guild_permissions(manage_emojis=True)
    @emoji_base.command(name='upload', aliases=['u'])
    async def emoji_upload(self, ctx):
        free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(ctx.guild)
        files = []
        for file in ctx.message.attachments:
            file_extension = file.filename.rsplit('.')[-1]
            if file_extension not in ['png', 'jpg', 'jpeg', 'tiff', 'gif']:
                continue
            files.append(file)
        if len(files) == 0:
            embed=discord.Embed(title="**Error while executing this command.**", description=f"There are no image files attached to this message.\nAccepted file extensions are: `png`, `jpg`, `jpeg`, `tiff` and `gif`.", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")
            await ctx.send(embed=embed)
            return
        for file in files:
            emoji_name = file.filename.rsplit('.', 1)[0]
            try:
                fp = await file.read()
                emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=fp)
            except Exception as e:
                print(e)
                embed = discord.Embed(title=f"**Error while adding a new emoji.**", description=f"Encountered a problem adding emoji `{emoji_name}`.\n```{e}```\nThis may prove somewhat useful when it comes to tracing the cause of this problem.", color=0x738adb)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
                embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.")

                await ctx.send(embed=embed)
                continue
            embed = discord.Embed(title=f"**Added a new emoji!**", description=f"Added a new emoji ({emoji}) to your server!\n It is currently named `{emoji_name}` and you can rename it by using command `^emoji rename {emoji_name} [new_name].`", color=0x738adb)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            await ctx.send(embed=embed)

    @commands.is_owner()
    @emoji_base.command(name='cleansession', aliases=['cs'])
    async def emoji_cleansession(self, ctx, member: discord.Member):
        key = str(ctx.guild.id)+'|'+str(member.id)

        try:
            del self.sessions[key]
            await ctx.send('usunieto sesje')
        except:
            await ctx.send('taka sesja nie istnieje')


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
            embed.add_field(name="**Name:**", value=entry['title'], inline=True)
            embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.", icon_url=entry['image'])
            

            await message.edit(embed=embed)


            return
        # Swipe to right
        if reaction.emoji == '➡️':
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])
            await message.remove_reaction('➡️', user)

            if self.sessions[key]['index'] > len(self.sessions[key]['available_emojis']):
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
            embed.add_field(name="**Name:**", value=entry['title'], inline=True)
            embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.", icon_url=entry['image'])
            
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
            embed.add_field(name="**Name:**", value=emoji_name, inline=True)
            embed.add_field(name="**Submitted by:**", value=entry['submitted_by'], inline=True)
            
            free_emoji_slots, free_animated_emoji_slots = await get_free_emoji_slots(reaction.message.channel.guild)
            embed.set_footer(text=f"This server has {free_emoji_slots} normal emoji slots available and {free_animated_emoji_slots} animated emoji slots available.", icon_url=entry['image'])
            

            await reaction.message.channel.send(embed=embed)
                
            return
        # On emoji add (❎)
        if reaction.emoji == '❎':
            message = await reaction.message.channel.fetch_message(self.sessions[key]['message_id'])
            await message.remove_reaction('❎', user)

            del self.sessions[key]

            await message.edit(content='Session closed.', suppress=True)

# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------

    @tasks.loop(minutes=1.0)
    async def check_sessions(self):
        for key in self.sessions:
            if self.sessions[key]['timeout'] < int(time.time()):
                del(self.sessions[key])

def setup(bot):
    bot.add_cog(CommandsCog(bot))
    print(f"Uruchomiono moduł {__name__}")

def teardown(bot):
    print(f"Wyłączono moduł {__name__}")
