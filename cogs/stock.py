import discord
from discord.ext import commands
from discord import app_commands
from utils.fetcher import get_stock_info, search_stock, get_recommended_stocks
from utils.db import toggle_favorite, get_favorites, get_favorite_count
import asyncio
from typing import List

MARKET_ALIASES = {
    "KOSPI": ["코스피", "ㅋㅅㅍ", "kospi", "코스피 (KOSPI)"],
    "KOSDAQ": ["코스닥", "ㅋㅅㄷ", "kosdaq", "코스닥 (KOSDAQ)"],
    "US": ["나스닥", "미국", "미국주식", "미장", "ㄴㅅㄷ", "ㅁㅈ", "us", "nasdaq", "나스닥/미국주식 (US)"]
}

class FavoriteButton(discord.ui.Button):
    def __init__(self, ticker: str, name: str, current_count: int):
        # 라벨을 빈 문자열로, 이모지를 하트(❤️)로 변경
        super().__init__(style=discord.ButtonStyle.secondary, label=f" {current_count}", emoji="❤️")
        self.ticker = ticker
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        added = toggle_favorite(user_id, self.ticker, self.name)
        new_count = get_favorite_count(self.ticker)
        
        # 버튼 텍스트(하트 수) 업데이트
        self.label = f" {new_count}"
        if added:
            self.style = discord.ButtonStyle.danger # 눌렀을 때 빨간색
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(f"❤️ **{self.name}** 종목이 내 하트 목록에 추가되었습니다!\n(`/ㅈㅁ` 명령어로 모아볼 수 있습니다)", ephemeral=True)
        else:
            self.style = discord.ButtonStyle.secondary # 해제하면 다시 회색
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(f"💔 **{self.name}** 종목이 하트 목록에서 제거되었습니다.", ephemeral=True)

class StockView(discord.ui.View):
    def __init__(self, ticker: str, name: str):
        super().__init__(timeout=None)
        count = get_favorite_count(ticker)
        self.add_item(FavoriteButton(ticker, name, count))

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
            
            # DB 조회해서 전체 하트 개수 가져오기
            fav_count = get_favorite_count(best_match['symbol'])
            embed.set_footer(text=f"※ 현재 총 {fav_count}명이 이 종목에 하트(❤️)를 눌렀습니다! 버튼을 눌러 내 종목(/ㅈㅁ)에 추가하세요.")

            view = StockView(ticker=best_match['symbol'], name=info['name'])

            if info.get('chart_buf'):
                file = discord.File(info['chart_buf'], filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                await interaction.followup.send(file=file, embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)
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

    @app_commands.command(name="추천", description="AI 알고리즘이 매수하기 좋은 유망 종목을 추천합니다.")
    @app_commands.describe(market="검색할 장종류 (코스피/ㅋㅅㅍ, 코스닥/ㅋㅅㄷ, 나스닥/ㄴㅅㄷ 등)")
    async def recommend(self, interaction: discord.Interaction, market: str):
        await interaction.response.defer(thinking=True)
        
        market_val = None
        market_lower = market.lower().replace(" ", "")
        for std, aliases in MARKET_ALIASES.items():
            if market_lower == std.lower() or market_lower in aliases:
                market_val = std
                break
                
        if not market_val:
            return await interaction.followup.send(f"❌ '{market}'은(는) 알 수 없는 장 종류입니다. 코스피(ㅋㅅㅍ), 코스닥(ㅋㅅㄷ), 나스닥(ㄴㅅㄷ) 중에서 입력해주세요.")
            
        market_name = {"KOSPI": "코스피", "KOSDAQ": "코스닥", "US": "나스닥/미국주식"}[market_val]
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

    @recommend.autocomplete('market')
    async def recommend_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        choices = [
            app_commands.Choice(name="코스피 (KOSPI)", value="KOSPI"),
            app_commands.Choice(name="코스닥 (KOSDAQ)", value="KOSDAQ"),
            app_commands.Choice(name="나스닥/미국주식 (US)", value="US")
        ]
        if not current: return choices
            
        current_lower = current.lower()
        filtered = []
        for choice in choices:
            val = choice.value
            aliases = MARKET_ALIASES[val]
            if any(current_lower in alias for alias in aliases):
                filtered.append(choice)
        return filtered if filtered else choices

    # --- 내 종목 모아보기 명령어 변경 (/ㅈㅁ) ---
    @app_commands.command(name="ㅈㅁ", description="내가 하트(❤️)를 누른 종목들의 현재 상태와 매매 전략(물타기/존버 등)을 확인합니다.")
    async def my_portfolio(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        
        user_id = str(interaction.user.id)
        favs = get_favorites(user_id)
        
        if not favs:
            return await interaction.followup.send("❌ 아직 하트를 누른 종목이 없습니다. `/주가` 검색 후 하단에 있는 ❤️ 버튼을 눌러 추가해보세요!")
            
        embed = discord.Embed(
            title=f"❤️ {interaction.user.display_name}님의 관심 종목 포트폴리오",
            description=f"총 {len(favs)}개의 종목을 AI가 일괄 분석했습니다.",
            color=0xff69b4 # 핫핑크색
        )
        
        async def fetch_fav(fav):
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, get_stock_info, fav['ticker'], fav['name'])
            return info

        tasks = [fetch_fav(f) for f in favs[:10]]
        results = await asyncio.gather(*tasks)
        
        for info in results:
            if not info: continue
            
            signal = info['trading_signal']
            icon = info['signal_icon']
            
            strategy = ""
            if "강력 매수" in signal:
                strategy = "🚨 **물타기 / 신규진입 강력 추천** (RSI 과매도 바닥 구간)"
            elif "단기 추세 매수" in signal:
                strategy = "🔥 **불타기(추매) 가능** (거래량 동반 우상향, 자금 유입중)"
            elif "눌림목 매수" in signal:
                strategy = "📉 **비중 확대 및 물타기 추천** (단기 조정 중인 가성비 구간)"
            elif "강력 매도" in signal:
                strategy = "💰 **익절 고려 / 물타기 절대 금지** (과열 구간 진입)"
            elif "관망 (데드" in signal:
                strategy = "🥶 **물타기 금지 / 바닥 확인 전까지 존버 요망** (하락 추세 진행중)"
            else:
                strategy = "🧘 **존버 / 관망** (뚜렷한 방향성 없음, 지지선 대기)"

            price_str = self.format_price(info['price'], info['currency'])
            val_text = f"**현재가**: `{price_str} {info['currency']}` | **AI 점수**: `{info['score']}점`\n> {icon} {strategy}"
            
            embed.add_field(name=f"{info['icon']} {info['name']} ({info['ticker']})", value=val_text, inline=False)
            
        if len(favs) > 10:
            embed.set_footer(text="※ 서버 부하를 막기 위해 상위 10개 종목만 분석되었습니다. 종목 관리는 다시 /주가 검색 후 ❤️를 눌러 취소할 수 있습니다.")
        else:
            embed.set_footer(text="※ 본 매매 가이드는 기술적 지표 시뮬레이션 결과이므로 투자 참고용으로만 활용하세요.")
            
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Stock(bot))
