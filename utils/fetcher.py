import yfinance as yf
import requests
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 자주 찾는/줄임말 사전 (autocomplete 및 빠른 검색용)
KOR_TICKER_MAP = {
    "애플 (Apple)": "AAPL", "엔비디아 (NVIDIA)": "NVDA", "테슬라 (Tesla)": "TSLA",
    "마이크로소프트 (마소)": "MSFT", "구글 (알파벳)": "GOOGL",
    "아마존 (Amazon)": "AMZN", "메타 (페이스북)": "META", "넷플릭스 (Netflix)": "NFLX",
    "AMD (암드)": "AMD", "TQQQ (티큐)": "TQQQ", "SPY (에센피)": "SPY", "QQQ (나스닥)": "QQQ",
    "삼성전자 (삼전)": "005930.KS",
    "대우건설 (대건)": "047040.KS", # 사용자 요청 축약어
    "SK하이닉스": "000660.KS",
    "에코프로": "086520.KQ",
}

EXCHANGE_MAP = {
    "KSC": "코스피 (KOSPI)", "KOE": "코스닥 (KOSDAQ)",
    "NMS": "나스닥 (NASDAQ)", "NYQ": "뉴욕증권거래소 (NYSE)"
}

def generate_sparkline(hist, color='green'):
    try:
        plt.figure(figsize=(6, 2.5))
        plt.plot(hist.index, hist['Close'], color=color, linewidth=2)
        plt.fill_between(hist.index, hist['Close'].min(), hist['Close'], color=color, alpha=0.1)
        plt.axis('off')
        plt.margins(0)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        plt.close()
        return buf
    except:
        return None

def search_stock(keyword: str):
    """
    m.stock.naver.com API를 사용하여 종목을 완벽하게 검색합니다.
    """
    keyword_upper = keyword.upper()
    
    # 1. 로컬 사전 매칭
    for name, ticker in KOR_TICKER_MAP.items():
        if keyword_upper in name.upper() or keyword_upper == ticker.split('.')[0]:
            return [{'symbol': ticker, 'display_symbol': ticker.replace('.KS','').replace('.KQ',''), 'name': name}]

    # 2. 네이버 신형 자동완성 API (KOSPI, KOSDAQ 정확한 구분 가능)
    try:
        url = f"https://m.stock.naver.com/front-api/search/autoComplete?query={keyword}&target=stock"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        data = res.json()
        items = data.get('result', {}).get('items', [])
        
        if items:
            results = []
            for item in items[:5]:
                code = item['code']
                name = item['name']
                if item['nationCode'] == 'KOR':
                    market = ".KS" if item['typeCode'] == "KOSPI" else ".KQ"
                    ticker = f"{code}{market}"
                else:
                    ticker = code
                results.append({'symbol': ticker, 'display_symbol': code, 'name': name})
            return results
    except Exception as e:
        print(f"Naver API Search Error: {e}")

    # 3. Yahoo Finance 폴백
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={keyword}&quotesCount=5"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        quotes = res.json().get('quotes', [])
        return [{'symbol': q.get('symbol'), 'display_symbol': q.get('symbol').replace('.KS','').replace('.KQ',''), 'name': q.get('shortname', q.get('symbol'))} for q in quotes if q.get('symbol')]
    except:
        return []

def get_stock_info(final_ticker: str, kor_name: str = None):
    # 이제 final_ticker는 .KS나 .KQ가 정확히 붙어있으므로 추측할 필요가 없습니다.
    icon = "🇰🇷" if ".KS" in final_ticker or ".KQ" in final_ticker else "🇺🇸"
    currency = "KRW" if icon == "🇰🇷" else "USD"
    
    ticker_obj = yf.Ticker(final_ticker)
    
    try:
        current_price = ticker_obj.fast_info.last_price
    except:
        return None

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
        if not hist.empty:
            chart_color = 'red' if hist['Close'].iloc[-1] < hist['Close'].iloc[0] else 'green'
            if currency == "KRW": chart_color = 'red' if hist['Close'].iloc[-1] > hist['Close'].iloc[0] else 'blue'
            chart_buf = generate_sparkline(hist, chart_color)
            
            recent_vol = hist['Volume'].tail(5).mean()
            avg_vol = hist['Volume'].mean()
            if recent_vol > avg_vol * 1.5: vol_score = 15
            elif recent_vol > avg_vol: vol_score = 5

        beta = info.get('beta', 1.0)
        relative_strength = "시장과 유사한 흐름"
        if beta > 1.2: relative_strength = "동종 업종 대비 높은 변동성 및 성장 기대치 (수급 활발)"
        elif beta < 0.8: relative_strength = "동종 업종 대비 방어적이고 안정적인 흐름"
        
        score = 20
        score += vol_score
        
        rec = info.get('recommendationKey', 'none')
        if rec == 'strong_buy': score += 20
        elif rec == 'buy': score += 10
        elif rec in ['underperform', 'sell']: score -= 10
            
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100))
            
        ma50, ma200 = info.get('fiftyDayAverage'), info.get('twoHundredDayAverage')
        if current_price and ma50 and current_price > ma50: score += 10
        if current_price and ma200 and current_price > ma200: score += 10
            
        pe_ratio = info.get('trailingPE', info.get('forwardPE'))
        if pe_ratio:
            if pe_ratio < 15: score += 10
            elif pe_ratio > 40: score -= 5
            
        score = max(0, min(100, score))
        
        related_tickers = "관련 데이터 없음"
        try:
            rec_url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{final_ticker}"
            rec_res = requests.get(rec_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2).json()
            recs = rec_res.get('finance', {}).get('result', [])
            if recs and recs[0].get('recommendedSymbols'):
                r_symbols = [r['symbol'] for r in recs[0]['recommendedSymbols'][:3]]
                related_tickers = ", ".join([s.replace('.KS','').replace('.KQ','') for s in r_symbols])
        except: pass

        return {
            "price": current_price, "open_price": open_price, "prev_close": prev_close,
            "high_52w": high_52w, "low_52w": low_52w, "growth_52w": growth_52w,
            "currency": currency, "icon": icon, "ticker": final_ticker.replace('.KS', '').replace('.KQ', ''),
            "name": name, "sector": info.get('sector', '분류 안됨'), 
            "exchange": EXCHANGE_MAP.get(info.get('exchange', ''), info.get('exchange', '알 수 없음')),
            "score": score, "relative_strength": relative_strength,
            "related_tickers": related_tickers, "chart_buf": chart_buf
        }
    except Exception as e:
        print(f"Error fetching detail: {e}")
        return None
