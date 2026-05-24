import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from utils.db import init_db

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        init_db()  # DB 초기화
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
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
