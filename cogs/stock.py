import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info, search_stock
from typing import List

class Stock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_price(self, price, currency):
        if price is None: return "-"
        if currency == "USD": return f"{price:,.2f}"
        return f"{int(price):,}"

    # --- 실시간 자동완성 (UX/UI 최적화) ---
    @app_commands.command(name="주가", description="종목 상세 분석 (차트, 52주 변동, 자본 흐름, 수혜주 포함)")
    @app_commands.describe(keyword="종목명(대건, lg 등) 또는 티커를 검색하세요")
    async def get_price(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(thinking=True)
        
        # 만약 사용자가 자동완성을 클릭해서 정확한 티커가 넘어왔거나, 직접 쳤는데 티커라면?
        # search_stock 로 한 번 더 안전하게 찾습니다.
        search_results = search_stock(keyword)
        if not search_results:
            return await interaction.followup.send(f"❌ '{keyword}' 검색 결과를 찾을 수 없습니다.")
            
        best_match = search_results[0]
        # 자동완성을 거쳤으므로 코스닥/코스피 구분이 정확한 symbol이 넘어갑니다.
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
                color=0x2b2d31
            )
            
            embed.add_field(name="💰 현재가", value=f"**`{price_str} {curr}`**", inline=True)
            embed.add_field(name="시가", value=f"{open_str} {curr}", inline=True)
            embed.add_field(name="전일 종가", value=f"{prev_str} {curr}", inline=True)
            
            embed.add_field(name="📊 52주 최저~최고", value=f"{low_str} ~ {high_str} {curr}", inline=True)
            embed.add_field(name="🚀 52주 저점 대비 성장", value=f"**{growth_str}**", inline=True)
            embed.add_field(name="📈 동종 업계 상대지표", value=f"*{info['relative_strength']}*", inline=True)

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

            if info.get('chart_buf'):
                file = discord.File(info['chart_buf'], filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                await interaction.followup.send(file=file, embed=embed)
            else:
                await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 상세 데이터를 불러오는데 실패했습니다.")

    @get_price.autocomplete('keyword')
    async def keyword_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not current:
            return []
        
        # 타이핑 할 때마다 실시간으로 네이버에 물어봐서 드롭다운으로 보여줍니다.
        results = search_stock(current)
        choices = []
        for r in results:
            # 예: "LG전자 (066570)"
            display_name = f"{r['name']} ({r['display_symbol']})"
            choices.append(app_commands.Choice(name=display_name, value=r['symbol']))
            
        return choices[:25] # 디스코드 제한은 최대 25개

async def setup(bot):
    await bot.add_cog(Stock(bot))
