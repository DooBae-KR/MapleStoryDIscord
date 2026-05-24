import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.command() 대신 @app_commands.command()를 사용하여 슬래시 명령어로 만듭니다.
    @app_commands.command(name="주가", description="종목의 현재가와 섹터 기반 투자 분석 점수를 확인합니다.")
    @app_commands.describe(ticker="종목코드 (예: AAPL, 005930) 또는 영문 티커를 입력하세요.")
    async def get_price(self, interaction: discord.Interaction, ticker: str):
        # yfinance 데이터 가져오는데 시간이 약간 걸릴 수 있으므로 '생각 중...' 메시지를 먼저 띄웁니다.
        await interaction.response.defer(thinking=True)
        
        info = get_stock_info(ticker)
        
        if info:
            if info['currency'] == "USD":
                price_str = f"{info['price']:,.2f}"
            else:
                price_str = f"{int(info['price']):,}"
                
            # 점수에 따라 색상 변경 (50점 이상은 초록색, 미만은 빨간색)
            embed_color = discord.Color.green() if info['score'] >= 50 else discord.Color.red()
            
            # 깔끔한 임베드(Embed) 박스 생성
            embed = discord.Embed(
                title=f"{info['icon']} {info['name']} ({info['ticker']})",
                color=embed_color
            )
            embed.add_field(name="💵 현재가", value=f"`{price_str} {info['currency']}`", inline=True)
            embed.add_field(name="🏢 섹터 / 업종", value=f"{info['sector']}\n({info['industry']})", inline=True)
            embed.add_field(name="📈 투자 분석 점수", value=f"**{info['score']}점** / 100점", inline=False)
            
            embed.set_footer(text="※ 점수는 목표가 대비 상승 여력, 모멘텀, 애널리스트 의견 등을 종합한 봇의 참고용 지표입니다.")
            
            # defer()를 사용했으므로 followup.send()로 응답합니다.
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 종목 정보를 찾을 수 없습니다. 올바른 종목코드(티커)를 입력해주세요.\n*(한국 주식은 6자리 숫자)*")

async def setup(bot):
    await bot.add_cog(Stock(bot))
