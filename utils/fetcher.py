import yfinance as yf
import requests
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import difflib
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
import concurrent.futures

KOR_TICKER_MAP = {
    "애플 (Apple)": "AAPL", "엔비디아 (NVIDIA)": "NVDA", "테슬라 (Tesla)": "TSLA",
    "마이크로소프트 (마소)": "MSFT", "구글 (알파벳)": "GOOGL",
    "아마존 (Amazon)": "AMZN", "메타 (페이스북)": "META", "넷플릭스 (Netflix)": "NFLX",
    "AMD (암드)": "AMD", "TQQQ (티큐)": "TQQQ", "SPY (에센피)": "SPY", "QQQ (나스닥)": "QQQ",
    "삼성전자 (삼전)": "005930.KS", "대우건설 (대건)": "047040.KS", 
    "SK하이닉스": "000660.KS", "에코프로": "086520.KQ",
}

EXCHANGE_MAP = {
    "KSC": "코스피 (KOSPI)", "KOE": "코스닥 (KOSDAQ)",
    "NMS": "나스닥 (NASDAQ)", "NYQ": "뉴욕증권거래소 (NYSE)"
}

ALL_STOCKS_CACHE = []

def load_all_stocks():
    global ALL_STOCKS_CACHE
    if ALL_STOCKS_CACHE: return
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        for sosok in [0, 1]:
            url = f"https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=market_sum&sosok={sosok}&pageSize=3000&page=1"
            data = requests.get(url, headers=headers, timeout=5).json()
            market = '.KS' if sosok == 0 else '.KQ'
            for item in data.get('result', {}).get('itemList', []):
                ALL_STOCKS_CACHE.append({'name': item['nm'], 'code': item['cd'], 'market': market})
    except: pass

import threading
threading.Thread(target=load_all_stocks).start()

def fuzzy_search(keyword, limit=5):
    keyword_upper = keyword.upper()
    results = []
    
    for name, ticker in KOR_TICKER_MAP.items():
        if keyword_upper in name.upper() or keyword_upper == ticker.split('.')[0]:
            results.append({'symbol': ticker, 'display_symbol': ticker.replace('.KS','').replace('.KQ',''), 'name': name, 'score': 2.0})

    if ALL_STOCKS_CACHE:
        for stock in ALL_STOCKS_CACHE:
            s_name = stock['name']
            ticker = f"{stock['code']}{stock['market']}"
            if keyword_upper == s_name.upper():
                results.append({'symbol': ticker, 'display_symbol': stock['code'], 'name': s_name, 'score': 1.5})
            elif keyword_upper in s_name.upper():
                results.append({'symbol': ticker, 'display_symbol': stock['code'], 'name': s_name, 'score': 1.0})
            else:
                ratio = difflib.SequenceMatcher(None, keyword_upper, s_name.upper()).ratio()
                if ratio > 0.5:
                    results.append({'symbol': ticker, 'display_symbol': stock['code'], 'name': s_name, 'score': ratio})

    seen = set()
    final_results = []
    results.sort(key=lambda x: x['score'], reverse=True)
    
    for r in results:
        if r['symbol'] not in seen:
            seen.add(r['symbol'])
            final_results.append(r)
            if len(final_results) >= limit: break
    return final_results

def search_stock(keyword: str):
    fuzzy_results = fuzzy_search(keyword, limit=5)
    if len(fuzzy_results) > 0 and fuzzy_results[0]['score'] >= 1.0:
        return fuzzy_results

    try:
        url = f"https://m.stock.naver.com/front-api/search/autoComplete?query={keyword}&target=stock"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2).json()
        items = res.get('result', {}).get('items', [])
        if items:
            for item in items[:5]:
                code = item['code']
                if item['nationCode'] == 'KOR':
                    ticker = f"{code}{'.KS' if item['typeCode'] == 'KOSPI' else '.KQ'}"
                else: ticker = code
                fuzzy_results.append({'symbol': ticker, 'display_symbol': code, 'name': item['name'], 'score': 0.9})
    except: pass

    if not fuzzy_results:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={keyword}&quotesCount=3"
            quotes = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2).json().get('quotes', [])
            for q in quotes:
                if q.get('symbol'):
                    fuzzy_results.append({'symbol': q['symbol'], 'display_symbol': q['symbol'], 'name': q.get('shortname', q['symbol']), 'score': 0.5})
        except: pass

    fuzzy_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    seen = set()
    cleaned = []
    for r in fuzzy_results:
        if r['symbol'] not in seen:
            seen.add(r['symbol'])
            cleaned.append(r)
    return cleaned[:5]

def generate_sparkline(hist, color='green'):
    try:
        plt.figure(figsize=(7, 2.5))
        plt.plot(hist.index, hist['Close'], color=color, linewidth=2)
        plt.fill_between(hist.index, hist['Close'].min(), hist['Close'], color=color, alpha=0.1)
        
        ax = plt.gca()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#888888')
        ax.get_yaxis().set_visible(False)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m.%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
        plt.xticks(color='#cccccc', fontsize=10)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print("Chart Error:", e)
        return None

def get_money_flow(code: str):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table", {"class": "type2"})
        if len(tables) > 1:
            rows = tables[1].find_all("tr")
            for r in rows:
                cols = r.find_all("td", {"class": "num"})
                if len(cols) >= 6:
                    inst = cols[4].text.strip()
                    foreign = cols[5].text.strip()
                    return {"inst": inst, "foreign": foreign}
    except Exception as e:
        print("Money Flow Error:", e)
    return {"inst": "제공 안됨", "foreign": "제공 안됨"}

def ai_pattern_analysis(hist, current_price):
    signal_icon = "➖"
    trading_signal = "보유 / 관망 대기"
    guideline = "현재 특별한 패턴이 감지되지 않았습니다. 박스권 횡보 가능성이 높으니 지지선을 확인하세요."
    score_adj = 0

    if hist.empty or len(hist) < 20:
        return trading_signal, signal_icon, guideline, score_adj

    delta = hist['Close'].diff()
    gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]

    ma20 = hist['Close'].rolling(window=20).mean()
    std20 = hist['Close'].rolling(window=20).std()
    upper_band = ma20 + (std20 * 2)
    lower_band = ma20 - (std20 * 2)
    curr_upper = upper_band.iloc[-1]
    curr_lower = lower_band.iloc[-1]
    
    vol20 = hist['Volume'].rolling(window=20).mean().iloc[-1]
    vol3 = hist['Volume'].tail(3).mean()
    vol_surge = vol3 > vol20 * 1.5

    if current_rsi < 30 and current_price <= curr_lower:
        trading_signal = "강력 매수 (기술적 과매도 + 밴드 하단 이탈)"
        signal_icon = "🟢"
        guideline = f"AI 패턴 분석 결과: 현재가는 볼린저 밴드 하단({int(curr_lower):,} 부근)을 이탈하였으며, RSI({current_rsi:.1f})가 극심한 과매도를 가리킵니다. 반발 매수세 유입이 예상되므로 분할 매수 타이밍으로 적합합니다."
        score_adj += 15
    elif current_rsi > 70 and current_price >= curr_upper:
        trading_signal = "강력 매도 (과열 구간 진입 + 밴드 상단 터치)"
        signal_icon = "🔴"
        guideline = f"AI 패턴 분석 결과: 주가가 단기 급등하여 밴드 상단({int(curr_upper):,} 부근)을 돌파했습니다. RSI({current_rsi:.1f}) 과열로 차익 실현 매물이 쏟아질 수 있으니 비중 축소를 권장합니다."
        score_adj -= 15
    elif vol_surge and hist['Close'].iloc[-1] > hist['Close'].iloc[-2]:
        trading_signal = "단기 추세 매수 (거래량 동반 상승 돌파)"
        signal_icon = "🔥"
        guideline = f"AI 패턴 분석 결과: 평소 대비 거래량이 폭발하며 강하게 말아 올리는 패턴이 감지되었습니다. 외인/기관 또는 세력의 단기 자본 유입 추세에 탑승해볼 만한 자리입니다."
        score_adj += 10
    elif current_rsi < 45 and current_price > ma20.iloc[-1]:
        trading_signal = "눌림목 매수 (상승장 속 일시적 조정)"
        signal_icon = "📈"
        guideline = f"AI 패턴 분석 결과: 20일선({int(ma20.iloc[-1]):,} 부근) 지지를 받으며 조정을 거치고 있습니다. 손절 라인을 20일선으로 짧게 잡고 매수 진입하기 좋은 가성비 구간입니다."
        score_adj += 5
    elif current_rsi > 55 and current_price < ma20.iloc[-1]:
        trading_signal = "관망 (데드크로스 및 추세 이탈 경고)"
        signal_icon = "📉"
        guideline = f"AI 패턴 분석 결과: 생명선인 20일선을 하향 이탈했습니다. 하락 파동이 시작될 수 있으므로 바닥이 확인될 때까지 신규 매수는 보류하는 것이 좋습니다."
        score_adj -= 10
    else:
        trading_signal = "보유 / 관망 (방향성 탐색 구간)"
        signal_icon = "➖"
        guideline = f"AI 패턴 분석 결과: 현재 뚜렷한 수급이나 기술적 지표 이탈이 없는 박스권 횡보 상태입니다. 위아래로 방향성이 결정될 때까지 관망하세요. (현재 RSI: {current_rsi:.1f})"

    return trading_signal, signal_icon, guideline, score_adj

def get_stock_info(final_ticker: str, kor_name: str = None):
    is_korean = ".KS" in final_ticker or ".KQ" in final_ticker
    icon = "🇰🇷" if is_korean else "🇺🇸"
    currency = "KRW" if is_korean else "USD"
    
    ticker_obj = yf.Ticker(final_ticker)
    try: current_price = ticker_obj.fast_info.last_price
    except: return None

    try:
        info = ticker_obj.info
        name = kor_name if kor_name else info.get('shortName', final_ticker.replace('.KS', '').replace('.KQ', ''))
        
        open_price = info.get('regularMarketOpen')
        prev_close = info.get('previousClose')
        high_52w = info.get('fiftyTwoWeekHigh')
        low_52w = info.get('fiftyTwoWeekLow')
        
        growth_52w = 0
        if current_price and low_52w:
            growth_52w = ((current_price - low_52w) / low_52w) * 100
            
        hist = ticker_obj.history(period="3mo")
        chart_buf = None
        
        if not hist.empty:
            chart_color = 'red' if hist['Close'].iloc[-1] < hist['Close'].iloc[0] else 'green'
            if currency == "KRW": chart_color = 'red' if hist['Close'].iloc[-1] > hist['Close'].iloc[0] else 'blue'
            chart_buf = generate_sparkline(hist, chart_color)
            
        money_flow = {"inst": "-", "foreign": "-"}
        if is_korean:
            code = final_ticker.replace('.KS', '').replace('.KQ', '')
            money_flow = get_money_flow(code)

        trading_signal, signal_icon, ai_guideline, pattern_score = ai_pattern_analysis(hist, current_price)

        score = 40 + pattern_score
        rec = info.get('recommendationKey', 'none')
        if rec == 'strong_buy': score += 20
        elif rec == 'buy': score += 10
        elif rec in ['underperform', 'sell']: score -= 10
            
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100))
            
        pe_ratio = info.get('trailingPE', info.get('forwardPE'))
        if pe_ratio:
            if pe_ratio < 15: score += 10
            elif pe_ratio > 40: score -= 5
            
        score = max(0, min(100, score))
        
        related_tickers_names = []
        try:
            rec_url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{final_ticker}"
            recs = requests.get(rec_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2).json().get('finance', {}).get('result', [])
            if recs and recs[0].get('recommendedSymbols'):
                r_symbols = [r['symbol'] for r in recs[0]['recommendedSymbols'][:3]]
                for sym in r_symbols:
                    clean_sym = sym.replace('.KS', '').replace('.KQ', '')
                    resolved_name = clean_sym
                    for cache_item in ALL_STOCKS_CACHE:
                        if cache_item['code'] == clean_sym:
                            resolved_name = cache_item['name']
                            break
                    if resolved_name == clean_sym:
                        temp_search = search_stock(clean_sym)
                        if temp_search:
                            resolved_name = temp_search[0]['name']
                    related_tickers_names.append(resolved_name)
        except: pass

        related_text = ", ".join(related_tickers_names) if related_tickers_names else "관련 데이터 없음"

        return {
            "price": current_price, "open_price": open_price, "prev_close": prev_close,
            "high_52w": high_52w, "low_52w": low_52w, "growth_52w": growth_52w,
            "currency": currency, "icon": icon, "ticker": final_ticker.replace('.KS', '').replace('.KQ', ''),
            "name": name, "sector": info.get('sector', '분류 안됨'), 
            "exchange": EXCHANGE_MAP.get(info.get('exchange', ''), info.get('exchange', '알 수 없음')),
            "score": score,
            "related_tickers": related_text, "chart_buf": chart_buf,
            "trading_signal": trading_signal, "signal_icon": signal_icon,
            "ai_guideline": ai_guideline,
            "money_flow": money_flow,
            "is_korean": is_korean
        }
    except Exception as e:
        print(f"Error fetching detail: {e}")
        return None

# --- AI 종목 추천 엔진 ---
def analyze_single_candidate(cand):
    """병렬 처리용 단일 종목 분석 함수"""
    sym = cand['symbol']
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="3mo")
        if hist.empty: return None
        
        curr_price = hist['Close'].iloc[-1]
        signal, icon, guide, score_adj = ai_pattern_analysis(hist, curr_price)
        
        # 매수/상승 패턴이 감지된 종목만 필터링
        if score_adj > 0 or "매수" in signal:
            info = ticker.info
            sector = info.get('sector', '업종/섹터 정보 없음')
            industry = info.get('industry', '')
            
            # 간단한 스코어 산출 (기본 + 패턴점수)
            base_score = 60 + score_adj
            
            return {
                "name": cand['name'],
                "symbol": sym.replace('.KS', '').replace('.KQ', ''),
                "price": curr_price,
                "signal": signal,
                "icon": icon,
                "reason": guide,
                "sector": f"{sector} / {industry}",
                "score": base_score
            }
    except: pass
    return None

def get_recommended_stocks(market: str):
    """지정된 시장의 거래량/시총 상위 종목을 추출하여 AI 알고리즘으로 분석 후 추천"""
    candidates = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        if market == "KOSPI":
            url = "https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=quant&sosok=0&pageSize=40&page=1"
            res = requests.get(url, headers=headers, timeout=5).json()
            for item in res.get('result', {}).get('itemList', []):
                # ETF 제외
                if 'KODEX' not in item['nm'] and 'TIGER' not in item['nm'] and 'KBSTAR' not in item['nm']:
                    candidates.append({"symbol": f"{item['cd']}.KS", "name": item['nm']})
                    
        elif market == "KOSDAQ":
            url = "https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=quant&sosok=1&pageSize=40&page=1"
            res = requests.get(url, headers=headers, timeout=5).json()
            for item in res.get('result', {}).get('itemList', []):
                if 'KODEX' not in item['nm'] and 'TIGER' not in item['nm']:
                    candidates.append({"symbol": f"{item['cd']}.KQ", "name": item['nm']})
                    
        elif market in ["NASDAQ", "US"]:
            # US 3대 지수 편입 및 거래량 상위
            url = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&scrIds=day_gainers&count=40"
            res = requests.get(url, headers=headers, timeout=5).json()
            quotes = res.get('finance', {}).get('result', [{}])[0].get('quotes', [])
            for q in quotes:
                sym = q['symbol']
                if "^" not in sym and "." not in sym and "=" not in sym and "-" not in sym:
                    candidates.append({"symbol": sym, "name": q.get('shortName', sym)})
    except Exception as e:
        print(f"Candidate Fetch Error: {e}")

    recommended = []
    # ThreadPoolExecutor를 이용하여 40개 종목을 빠르게 동시 분석
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_cand = {executor.submit(analyze_single_candidate, cand): cand for cand in candidates}
        for future in concurrent.futures.as_completed(future_to_cand):
            res = future.result()
            if res:
                recommended.append(res)
    
    # 점수 높은 순으로 정렬 후 상위 10개 반환
    recommended.sort(key=lambda x: x['score'], reverse=True)
    return recommended[:10]
