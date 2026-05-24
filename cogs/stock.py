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

    @app_commands.command(name="주가", description="종목 상세 분석 (차트, 52주 변동, 매수/매도 타이밍, 수혜주 포함)")
    @app_commands.describe(keyword="종목명(대건, lg 등) 또는 티커를 검색하세요")
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
                color=0x2b2d31
            )
            
            # --- 가독성을 높인 직사각형 블록형 데이터 배치 ---
            embed.add_field(
                name="[ 💵 주가 및 시세 정보 ]",
                value=f"```yaml\n현재가   : {price_str} {curr}\n시가     : {open_str} {curr}\n전일종가 : {prev_str} {curr}```",
                inline=False
            )

            embed.add_field(
                name="[ 📊 52주 변동 및 성장률 ]",
                value=f"```yaml\n최저~최고 : {low_str} ~ {high_str} {curr}\n성장률    : {growth_str}\n동종업계  : {info['relative_strength']}```",
                inline=False
            )

            embed.add_field(
                name="[ 🎯 AI 퀀트 투자 분석 및 매수/매도 타이밍 ]", 
                value=f"> **종합 점수**: **{info['score']}점** / 100점\n"
                      f"> {info['signal_icon']} **{info['trading_signal']}**\n"
                      f"*(외인/기관 자본 흐름, 이동평균선 역배열/정배열, 기술적 RSI 지표 등을 종합한 분석입니다.)*", 
                inline=False
            )

            embed.add_field(
                name="[ 🔗 관련 수혜 기업 및 밸류체인 ]", 
                value=f"> {info['related_tickers']}", 
                inline=False
            )
            
            embed.set_footer(text="※ 차트 하단에는 X축(월.일)이 표시됩니다. 본 분석은 투자 참고용이며 법적 책임은 지지 않습니다.")

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
        results = search_stock(current)
        choices = []
        for r in results:
            display_name = f"{r['name']} ({r['display_symbol']})"
            choices.append(app_commands.Choice(name=display_name, value=r['symbol']))
        return choices[:25]

async def setup(bot):
    await bot.add_cog(Stock(bot))
