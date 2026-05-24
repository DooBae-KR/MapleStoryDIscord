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

    @app_commands.command(name="주가", description="종목 분석 (AI 타이밍, 외인/기관 수급, 수혜주)")
    @app_commands.describe(keyword="종목명(삼성전자, lg 등) 또는 티커를 검색하세요")
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
            
            embed.add_field(
                name="[ 💵 주가 및 시세 정보 ]",
                value=f"```yaml\n현재가   : {price_str} {curr}\n시가     : {open_str} {curr}\n전일종가 : {prev_str} {curr}```",
                inline=False
            )

            # 한국 주식일 경우에만 외인/기관 수급 데이터 표시
            if info['is_korean']:
                inst_flow = info['money_flow']['inst']
                for_flow = info['money_flow']['foreign']
                embed.add_field(
                    name="[ 💸 당일 기관 / 외국인 수급 흐름 ]",
                    value=f"```diff\n기관 순매수 : {inst_flow} 주\n외인 순매수 : {for_flow} 주```",
                    inline=False
                )

            embed.add_field(
                name="[ 📊 52주 변동 및 성장률 ]",
                value=f"```yaml\n최저~최고 : {low_str} ~ {high_str} {curr}\n성장률    : {growth_str}```",
                inline=False
            )

            # AI 타이밍 및 가이드라인
            embed.add_field(
                name=f"[ {info['signal_icon']} AI 기술적 분석 & 매매 타이밍 ]", 
                value=f"> **AI 시그널**: **{info['trading_signal']}**\n"
                      f"> {info['ai_guideline']}", 
                inline=False
            )

            # 종합 점수 및 밸류체인
            embed.add_field(
                name="[ 🎯 퀀트 가치평가 및 수혜주 ]", 
                value=f"> **종합 투자 점수**: **{info['score']}점** / 100점\n"
                      f"> **연관 수혜주/밸류체인**: `{info['related_tickers']}`", 
                inline=False
            )
            
            embed.set_footer(text="※ 차트 X축은 월.일입니다. 본 AI 패턴 분석은 과거 데이터(볼린저 밴드, RSI, 거래량)를 통한 통계적 시뮬레이션이며 투자 결과에 법적 책임을 지지 않습니다.")

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
