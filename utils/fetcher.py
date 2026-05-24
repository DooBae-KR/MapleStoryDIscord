import yfinance as yf
import requests
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import difflib
import pandas as pd

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

def generate_sparkline(hist, color='green'):
    try:
        # 가독성을 위해 차트 크기를 약간 키움
        plt.figure(figsize=(7, 2.5))
        plt.plot(hist.index, hist['Close'], color=color, linewidth=2)
        plt.fill_between(hist.index, hist['Close'].min(), hist['Close'], color=color, alpha=0.1)
        
        ax = plt.gca()
        # 위, 왼쪽, 오른쪽 테두리 제거 (바닥선만 남김)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#888888')
        
        # Y축 숨김, X축 날짜(월.일) 표시
        ax.get_yaxis().set_visible(False)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m.%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
        plt.xticks(color='#cccccc', fontsize=10) # 디스코드 다크모드 대응 텍스트 색상
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print("Chart Error:", e)
        return None

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

def get_stock_info(final_ticker: str, kor_name: str = None):
    icon = "🇰🇷" if ".KS" in final_ticker or ".KQ" in final_ticker else "🇺🇸"
    currency = "KRW" if icon == "🇰🇷" else "USD"
    
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
        vol_score = 0
        trading_signal = "관망 (추세 확인 필요)"
        signal_icon = "⏸️"
        
        if not hist.empty:
            chart_color = 'red' if hist['Close'].iloc[-1] < hist['Close'].iloc[0] else 'green'
            if currency == "KRW": chart_color = 'red' if hist['Close'].iloc[-1] > hist['Close'].iloc[0] else 'blue'
            chart_buf = generate_sparkline(hist, chart_color)
            
            # 수급(거래량) 분석
            recent_vol = hist['Volume'].tail(5).mean()
            avg_vol = hist['Volume'].mean()
            if recent_vol > avg_vol * 1.5: vol_score = 15
            elif recent_vol > avg_vol: vol_score = 5

            # RSI 기반 매수/매도 타이밍 예측
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            ma50, ma200 = info.get('fiftyDayAverage'), info.get('twoHundredDayAverage')
            
            if current_rsi < 30:
                trading_signal = "강력 매수 (RSI 과매도 구간, 단기 기술적 반등 예상)"
                signal_icon = "🟢"
            elif current_rsi > 70:
                trading_signal = "분할 매도 (RSI 과매수 구간, 단기 고점 조정 주의)"
                signal_icon = "🔴"
            elif ma50 and ma200 and current_price > ma50 and current_price > ma200:
                trading_signal = "매수 / 보유 (단장기 정배열 우상향 추세 진행중)"
                signal_icon = "📈"
            elif ma50 and ma200 and current_price < ma50 and current_price < ma200:
                trading_signal = "관망 (이동평균선 역배열, 하락 추세 주의)"
                signal_icon = "📉"
            else:
                trading_signal = "보유 / 관망 (특이 시그널 없음, 모멘텀 대기)"
                signal_icon = "➖"

        beta = info.get('beta', 1.0)
        relative_strength = "시장 흐름과 유사"
        if beta > 1.2: relative_strength = "동종 업계 대비 매우 강한 변동성 및 탄력성"
        elif beta < 0.8: relative_strength = "동종 업계 대비 방어적이고 안정적인 흐름"
        
        # 퀀트 점수 산출
        score = 20 + vol_score
        rec = info.get('recommendationKey', 'none')
        if rec == 'strong_buy': score += 20
        elif rec == 'buy': score += 10
        elif rec in ['underperform', 'sell']: score -= 10
            
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100))
            
        if current_price and info.get('fiftyDayAverage') and current_price > info.get('fiftyDayAverage'): score += 10
        if current_price and info.get('twoHundredDayAverage') and current_price > info.get('twoHundredDayAverage'): score += 10
            
        pe_ratio = info.get('trailingPE', info.get('forwardPE'))
        if pe_ratio:
            if pe_ratio < 15: score += 10
            elif pe_ratio > 40: score -= 5
            
        score = max(0, min(100, score))
        
        # 관련 수혜주 (티커 -> 기업명 변환 로직 추가)
        related_tickers_names = []
        try:
            rec_url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{final_ticker}"
            recs = requests.get(rec_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2).json().get('finance', {}).get('result', [])
            if recs and recs[0].get('recommendedSymbols'):
                r_symbols = [r['symbol'] for r in recs[0]['recommendedSymbols'][:3]]
                for sym in r_symbols:
                    clean_sym = sym.replace('.KS', '').replace('.KQ', '')
                    resolved_name = clean_sym
                    # 1. 내부 캐시에서 검색
                    for cache_item in ALL_STOCKS_CACHE:
                        if cache_item['code'] == clean_sym:
                            resolved_name = cache_item['name']
                            break
                    # 2. 캐시에 없으면 (해외주식 등) 야후 API로 이름 조회 (빠르게)
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
            "score": score, "relative_strength": relative_strength,
            "related_tickers": related_text, "chart_buf": chart_buf,
            "trading_signal": trading_signal, "signal_icon": signal_icon
        }
    except Exception as e:
        print(f"Error fetching detail: {e}")
        return None
