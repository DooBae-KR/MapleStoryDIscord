import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info, search_stock

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_price(self, price, currency):
        if price is None: return "-"
        if currency == "USD": return f"{price:,.2f}"
        return f"{int(price):,}"

    @app_commands.command(name="주가", description="종목 상세 분석 (차트, 52주 변동, 자본 흐름, 수혜주 포함)")
    @app_commands.describe(keyword="종목명(삼성전자, 애플) 또는 티커")
    async def get_price(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(thinking=True)
        search_results = search_stock(keyword)
        if not search_results:
            return await interaction.followup.send(f"❌ '{keyword}' 검색 결과를 찾을 수 없습니다.")
            
        best_match = search_results[0]
        info = get_stock_info(best_match['symbol'], best_match['name'])
        
        if info:
            curr = info['currency']
            price_str = self.format_price(info['price'], curr)
            open_str = self.format_price(info['open_price'], curr)
            prev_str = self.format_price(info['prev_close'], curr)
            high_str = self.format_price(info['high_52w'], curr)
            low_str = self.format_price(info['low_52w'], curr)
            growth_str = f"+{info['growth_52w']:.1f}%" if info['growth_52w'] > 0 else f"{info['growth_52w']:.1f}%"
            
            embed = discord.Embed(
                title=f"{info['icon']} {info['name']} ({info['ticker']}) - {info['exchange']}",
                color=0x2b2d31 # 디스코드 다크모드 배경과 어울리는 세련된 색상
            )
            
            # --- 1단: 금액적 정보 (우측 배열 느낌을 주기 위해 Inline 적극 활용) ---
            embed.add_field(name="💰 현재가", value=f"**`{price_str} {curr}`**", inline=True)
            embed.add_field(name="시가", value=f"{open_str} {curr}", inline=True)
            embed.add_field(name="전일 종가", value=f"{prev_str} {curr}", inline=True)
            
            embed.add_field(name="📊 52주 최저~최고", value=f"{low_str} ~ {high_str} {curr}", inline=True)
            embed.add_field(name="🚀 52주 저점 대비 성장", value=f"**{growth_str}**", inline=True)
            embed.add_field(name="📈 동종 업계 상대지표", value=f"*{info['relative_strength']}*", inline=True)

            # --- 2단: 투자 점수 및 가치 사슬 (하단 배치) ---
            embed.add_field(
                name="🤖 AI 퀀트 종합 투자 점수", 
                value=f"**{info['score']}점** / 100점\n*(자본 수급, 기관 매수세, 애널리스트 미래가치 평가 종합)*", 
                inline=False
            )
            embed.add_field(
                name="🔗 관련 수혜주 / 밸류체인", 
                value=f"`{info['related_tickers']}`\n*(해당 종목과 동조화되거나 자금이 같이 움직이는 종목들)*", 
                inline=False
            )
            
            embed.set_footer(text="※ 차트는 최근 3개월 추세입니다. 점수는 거래량 폭발(자본유입), 모멘텀, 가치평가를 기반으로 합니다.")

            # 차트 이미지가 생성되었다면 디스코드 파일로 변환하여 Embed에 첨부
            if info.get('chart_buf'):
                file = discord.File(info['chart_buf'], filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                await interaction.followup.send(file=file, embed=embed)
            else:
                await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 상세 데이터를 불러오는데 실패했습니다.")

async def setup(bot):
    await bot.add_cog(Stock(bot))
