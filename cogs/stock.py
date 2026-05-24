import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info, search_stock

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="주가", description="종목명이나 종목코드로 주가를 검색합니다.")
    @app_commands.describe(keyword="종목명(예: 삼성, 애플) 또는 티커(AAPL, 005930)")
    async def get_price(self, interaction: discord.Interaction, keyword: str):
        # 검색 및 데이터 조회를 위해 '생각 중...' 메시지 띄우기
        await interaction.response.defer(thinking=True)
        
        # 1. 키워드로 먼저 종목 검색
        search_results = search_stock(keyword)
        
        if not search_results:
            await interaction.followup.send(f"❌ '{keyword}'에 대한 검색 결과를 찾을 수 없습니다. (정확한 띄어쓰기나 코드로 다시 검색해 보세요!)")
            return
            
        # 2. 가장 연관성이 높은 첫 번째 결과로 상세 정보 가져오기
        best_match = search_results[0]
        info = get_stock_info(best_match['symbol'])
        
        if info:
            if info['currency'] == "USD":
                price_str = f"{info['price']:,.2f}"
            else:
                price_str = f"{int(info['price']):,}"
                
            embed_color = discord.Color.green() if info['score'] >= 50 else discord.Color.red()
            
            # 주가 및 분석 점수 임베드 생성
            embed = discord.Embed(
                title=f"{info['icon']} {info['name']} ({info['ticker']})",
                color=embed_color
            )
            embed.add_field(name="💵 현재가", value=f"`{price_str} {info['currency']}`", inline=True)
            embed.add_field(name="🏢 섹터 / 업종", value=f"{info['sector']}\n({info['industry']})", inline=True)
            embed.add_field(name="📈 투자 분석 점수", value=f"**{info['score']}점** / 100점", inline=False)
            
            # 3. 2~5번째 연관 검색어가 있다면 추천 리스트로 추가
            if len(search_results) > 1:
                other_matches = []
                for res in search_results[1:5]:  # 최대 4개까지만
                    other_matches.append(f"{res['name']} ({res['display_symbol']})")
                
                embed.add_field(name="🔍 혹시 이 종목을 찾으셨나요?", value=", ".join(other_matches), inline=False)
            
            embed.set_footer(text="※ 점수는 목표가 대비 상승 여력, 단기 모멘텀 등을 종합한 봇의 참고 지표입니다.")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 가장 비슷한 종목을 찾았으나 상세 데이터를 불러오는데 실패했습니다.")

async def setup(bot):
    await bot.add_cog(Stock(bot))
