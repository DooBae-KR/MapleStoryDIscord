import discord
from discord.ext import commands
from utils.fetcher import get_stock_info

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="주가")
    async def get_price(self, ctx, ticker: str):
        """!주가 <종목코드> 형태로 주가를 확인합니다. (예: !주가 AAPL, !주가 005930)"""
        msg = await ctx.send(f"🔍 `{ticker}` 주가 정보를 가져오는 중입니다...")
        
        info = get_stock_info(ticker)
        
        if info:
            # 달러는 소수점 2자리, 원화는 정수로 표현
            if info['currency'] == "USD":
                price_str = f"{info['price']:,.2f}"
            else:
                price_str = f"{int(info['price']):,}"
                
            await msg.edit(content=f"{info['icon']} **{info['ticker']}** 현재가: `{price_str} {info['currency']}`")
        else:
            await msg.edit(content="❌ 종목 정보를 찾을 수 없습니다. 티커(종목코드)가 올바른지 확인해주세요.\n*(한국 주식은 6자리 숫자, 미국 주식은 영문 티커를 입력해주세요)*")

async def setup(bot):
    await bot.add_cog(Stock(bot))
