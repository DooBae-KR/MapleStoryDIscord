import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

if __name__ == '__main__':
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
