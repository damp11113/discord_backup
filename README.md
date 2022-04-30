discord_backup
===============
save only

load is not available

Demo code
===============
```py
import discord
import asyncio
from damp11113.file import *
from damp11113.randoms import ranstr
from discord_backup.backup import BackupServer
from discord_backup.info import BackupInfo
from discord_backup.loader import BackupLoader
from discord.ext import commands
from discord.ext.tasks import task
import logging

logging.basicConfig(level=logging.INFO)

# get all intents
intent = discord.Intents.default()
intent.members = True
bot = commands.Bot(command_prefix='!', intents=intent)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def backup(ctx):
    guild = ctx.guild
    filename = ranstr(10)
    await ctx.send(f'Backing up {guild.name}')
    backup = BackupServer(bot, guild)
    json = await backup.save()
    writejson(filename, json)
    print(json)
    await ctx.send(f'Backup complete. your code is {filename} for load')

@bot.command()
async def info(ctx, filename):
    try:
        json = readjson(filename)
    except:
        await ctx.send('Backup not found')

    info = BackupInfo(json)
    embed = discord.embeds.Embed(title=f'Backup info')
    embed.add_field(name='Name', value=info.name)
    embed.add_field(name='Member', value=info.member_count)
    embed.set_footer(text=f'Created on {info.name} at {info.create_backup_at()}')
    await ctx.send(embed=embed)
    
@bot.command()
async def load(ctx, filename):
    try:
        json = readjson(filename)
    except:
        await ctx.send('Backup not found')

    # get ctx user
    user = ctx.author
    # get guild
    guild = ctx.guild

    m = await ctx.send('You are sure you want to load this backup?')
    await m.add_reaction('✅')
    await m.add_reaction('❌')
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['✅', '❌']
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        try:
            await m.clear_reactions()
            if str(reaction.emoji) == '✅':
                await m.edit(content='Loading backup...')
                try:
                    backup = BackupLoader(bot, guild, json)
                    # run task await backup.load(guild, user)
                    task
                    # create message with bot
                    # get main channel
                    channel = guild.system_channel
                    # create embed
                    await channel.send(f'Backup loaded by {user.name}')
                except Exception as e:
                    await ctx.send(f'Error: {e}')
            else:
                await ctx.send('Backup not loaded')
        except:
            pass
    except asyncio.TimeoutError:
        await ctx.send('Timed out')

bot.run('token')

```

Installing
===============
    pip install discord_backup
    
or

    pip install git+https://github.com/damp11113/discord_backup.git
    
License
===============

MIT License

Copyright (c) 2022 damp11113

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
