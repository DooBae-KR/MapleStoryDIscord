import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# .env 파일에서 환경변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def load_extensions():
    # cogs 폴더에 있는 모든 파이썬 파일을 봇 모듈로 불러옵니다.
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

async def main():
    await load_extensions()
    await bot.start(TOKEN)

if __name__ == '__main__':
    if TOKEN:
        asyncio.run(main())
    else:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
