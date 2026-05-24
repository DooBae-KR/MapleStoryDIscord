import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info, search_stock

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_price(self, price, currency):
        if price is None: return "정보 없음"
        if currency == "USD": return f"{price:,.2f}"
        return f"{int(price):,}"

    @app_commands.command(name="주가", description="종목명이나 종목코드로 주가 상세 정보와 분석 점수를 확인합니다.")
    @app_commands.describe(keyword="종목명(예: 삼성전자, 애플) 또는 티커")
    async def get_price(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(thinking=True)
        
        search_results = search_stock(keyword)
        
        if not search_results:
            await interaction.followup.send(f"❌ '{keyword}' 검색 결과를 찾을 수 없습니다.")
            return
            
        best_match = search_results[0]
        # 네이버에서 찾은 한국어 기업명을 get_stock_info로 넘겨줍니다.
        info = get_stock_info(best_match['symbol'], best_match['name'])
        
        if info:
            curr = info['currency']
            price_str = self.format_price(info['price'], curr)
            open_str = self.format_price(info['open_price'], curr)
            prev_str = self.format_price(info['prev_close'], curr)
            high_str = self.format_price(info['high_52w'], curr)
            low_str = self.format_price(info['low_52w'], curr)
                
            embed_color = discord.Color.green() if info['score'] >= 50 else discord.Color.red()
            
            embed = discord.Embed(
                title=f"{info['icon']} {info['name']} ({info['ticker']})",
                description=f"**{info['exchange']}** 상장",
                color=embed_color
            )
            
            # 첫 번째 줄: 현재가, 전일비(시가/종가)
            embed.add_field(name="💵 현재가", value=f"**`{price_str} {curr}`**", inline=True)
            embed.add_field(name="📉 전일 종가", value=f"{prev_str} {curr}", inline=True)
            embed.add_field(name="📈 금일 시가", value=f"{open_str} {curr}", inline=True)
            
            # 두 번째 줄: 52주 변동폭 및 섹터
            embed.add_field(name="📊 52주 최저 / 최고가", value=f"{low_str} ~ {high_str}", inline=True)
            embed.add_field(name="🏢 섹터 / 업종", value=f"{info['sector']} / {info['industry']}", inline=True)
            
            # 세 번째 줄: 투자 분석 점수
            embed.add_field(name="🤖 AI 상대적 투자 점수", value=f"**{info['score']}점** / 100점", inline=False)
            
            if len(search_results) > 1:
                other_matches = [f"{r['name']}({r['display_symbol']})" for r in search_results[1:5]]
                embed.add_field(name="🔍 연관 검색어", value=", ".join(other_matches), inline=False)
            
            embed.set_footer(text="※ 점수는 PER 상대평가, 이동평균선(50일, 200일) 모멘텀, 애널리스트 목표가를 종합한 봇의 참고용 평가 지표입니다. 공모가는 지원하지 않아 52주 변동폭을 제공합니다.")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 가장 비슷한 종목을 찾았으나, 상장폐지되었거나 상세 데이터를 불러오는데 실패했습니다.")

async def setup(bot):
    await bot.add_cog(Stock(bot))
