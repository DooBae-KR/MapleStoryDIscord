import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

class MyBot(commands.Bot):
    def __init__(self):
        # 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        # 기존 prefix 방식도 유지하려면 빈 접두사나 !를 넣습니다.
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # 봇이 시작될 때 cogs 폴더의 기능들을 불러옵니다.
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        
        # 추가된 슬래시 명령어들을 디스코드 서버에 동기화(등록) 합니다.
        await self.tree.sync()
        print("✅ Slash commands synced!")

    async def on_ready(self):
        print(f'✅ Logged in as {self.user} (ID: {self.user.id})')
        print('------')

bot = MyBot()

async def main():
    await bot.start(TOKEN)

if __name__ == '__main__':
    if TOKEN:
        asyncio.run(main())
    else:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
