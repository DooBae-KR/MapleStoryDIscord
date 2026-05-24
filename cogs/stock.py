import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info, search_stock, get_recommended_stocks
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

            embed.add_field(
                name=f"[ {info['signal_icon']} AI 기술적 분석 & 매매 타이밍 ]", 
                value=f"> **AI 시그널**: **{info['trading_signal']}**\n"
                      f"> {info['ai_guideline']}", 
                inline=False
            )

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
        if not current: return []
        results = search_stock(current)
        choices = []
        for r in results:
            display_name = f"{r['name']} ({r['display_symbol']})"
            choices.append(app_commands.Choice(name=display_name, value=r['symbol']))
        return choices[:25]

    # --- 종목 추천 명령어 ---
    @app_commands.command(name="종목추천", description="AI 알고리즘이 매수하기 좋은 유망 종목을 선별하여 추천합니다.")
    @app_commands.describe(market="분석할 시장을 선택하세요")
    @app_commands.choices(market=[
        app_commands.Choice(name="코스피 (KOSPI)", value="KOSPI"),
        app_commands.Choice(name="코스닥 (KOSDAQ)", value="KOSDAQ"),
        app_commands.Choice(name="나스닥/미국주식 (US)", value="US")
    ])
    async def recommend(self, interaction: discord.Interaction, market: app_commands.Choice[str]):
        # 이 작업은 데이터를 병렬로 긁어오므로 시간이 걸립니다.
        await interaction.response.defer(thinking=True)
        
        market_val = market.value
        market_name = market.name
        curr = "USD" if market_val == "US" else "KRW"
        
        recommended_list = get_recommended_stocks(market_val)
        
        if not recommended_list:
            return await interaction.followup.send(f"❌ 현재 {market_name} 시장에서 확실한 매수 시그널이 감지된 종목이 없습니다. (장이 너무 안 좋거나 데이터 오류일 수 있습니다)")
            
        embed = discord.Embed(
            title=f"🤖 {market_name} - AI 추천 매수 유망 종목 Top {len(recommended_list)}",
            description="현재 거래량이 폭발하거나 기술적(RSI/볼린저)으로 강력한 매수 패턴을 그리는 종목들입니다.",
            color=0x00ff00
        )
        
        for idx, rec in enumerate(recommended_list, 1):
            price_str = self.format_price(rec['price'], curr)
            # 가시성을 위해 yaml 코드블록과 인라인 필드를 조합합니다.
            field_value = (
                f"**섹터/업종**: `{rec['sector']}`\n"
                f"**현재가**: `{price_str} {curr}`\n"
                f"> {rec['icon']} **{rec['signal']}**\n"
                f"> {rec['reason']}"
            )
            embed.add_field(
                name=f"{idx}. {rec['name']} ({rec['symbol']})",
                value=field_value,
                inline=False
            )
            
        embed.set_footer(text="※ 추천 종목은 기술적 지표 시뮬레이션의 결과이므로 반드시 본인의 판단하에 투자하시기 바랍니다.")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Stock(bot))
