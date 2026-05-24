import yfinance as yf
import requests
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

KOR_TICKER_MAP = {
    "애플": "AAPL", "엔비디아": "NVDA", "테슬라": "TSLA",
    "마이크로소프트": "MSFT", "마소": "MSFT", "구글": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "페이스북": "META", "넷플릭스": "NFLX",
    "암드": "AMD", "티큐": "TQQQ", "에센피": "SPY", "나스닥": "QQQ",
    "삼전": "005930"
}

EXCHANGE_MAP = {
    "KSC": "코스피 (KOSPI)", "KOE": "코스닥 (KOSDAQ)",
    "NMS": "나스닥 (NASDAQ)", "NYQ": "뉴욕증권거래소 (NYSE)"
}

def search_stock(keyword: str):
    keyword_upper = keyword.upper()
    for kor_name, ticker in KOR_TICKER_MAP.items():
        if keyword_upper in kor_name or kor_name in keyword_upper:
            return [{'symbol': ticker, 'display_symbol': ticker, 'name': kor_name}]

    try:
        naver_url = f"https://ac.finance.naver.com/ac?q={keyword}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8"
        res = requests.get(naver_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        data = res.json()
        if data.get('items') and len(data['items'][0]) > 0:
            return [{'symbol': i[1], 'display_symbol': i[1], 'name': i[0]} for i in data['items'][0][:5]]
    except:
        pass

    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={keyword}&quotesCount=5"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        quotes = res.json().get('quotes', [])
        return [{'symbol': q.get('symbol'), 'display_symbol': q.get('symbol').replace('.KS','').replace('.KQ',''), 'name': q.get('shortname', q.get('symbol'))} for q in quotes if q.get('symbol')]
    except:
        return []

def generate_sparkline(hist, color='green'):
    """주가 차트 이미지를 메모리에 그려서 반환합니다 (한글 폰트 깨짐 방지를 위해 글자 생략)"""
    try:
        plt.figure(figsize=(6, 2.5))
        plt.plot(hist.index, hist['Close'], color=color, linewidth=2)
        plt.fill_between(hist.index, hist['Close'].min(), hist['Close'], color=color, alpha=0.1)
        plt.axis('off') # 깔끔한 선만 보이게
        plt.margins(0)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        buf.seek(0)
        plt.close()
        return buf
    except:
        return None

def get_stock_info(query_ticker: str, kor_name: str = None):
    icon, currency = "🇺🇸", "USD"
    if query_ticker.isdigit() and len(query_ticker) == 6:
        try_tickers = [f"{query_ticker}.KS", f"{query_ticker}.KQ"]
    else:
        try_tickers = [query_ticker]
        
    ticker_obj, current_price, final_ticker = None, None, query_ticker

    for tk in try_tickers:
        temp = yf.Ticker(tk)
        try:
            if temp.fast_info.last_price:
                ticker_obj, final_ticker, current_price = temp, tk, temp.fast_info.last_price
                if ".KS" in tk or ".KQ" in tk: icon, currency = "🇰🇷", "KRW"
                break
        except: continue

    if not ticker_obj: return None

    try:
        info = ticker_obj.info
        name = kor_name if kor_name else info.get('shortName', final_ticker.replace('.KS', '').replace('.KQ', ''))
        
        # 기본 가격 데이터
        open_price = info.get('regularMarketOpen')
        prev_close = info.get('previousClose')
        high_52w = info.get('fiftyTwoWeekHigh')
        low_52w = info.get('fiftyTwoWeekLow')
        
        # 52주 변동폭 (저점 대비 성장률)
        growth_52w = 0
        if current_price and low_52w:
            growth_52w = ((current_price - low_52w) / low_52w) * 100
            
        # 히스토리 데이터 로드 (차트 및 수급 분석용)
        hist = ticker_obj.history(period="3mo")
        chart_buf = None
        vol_score = 0
        if not hist.empty:
            chart_color = 'red' if hist['Close'].iloc[-1] < hist['Close'].iloc[0] else 'green' # 한국은 상승이 빨간색이지만 글로벌 기준 적용
            if currency == "KRW": chart_color = 'red' if hist['Close'].iloc[-1] > hist['Close'].iloc[0] else 'blue'
            chart_buf = generate_sparkline(hist, chart_color)
            
            # 최근 5일 거래량 vs 3달 평균 거래량 (자본 유입/기관 수급 프록시)
            recent_vol = hist['Volume'].tail(5).mean()
            avg_vol = hist['Volume'].mean()
            if recent_vol > avg_vol * 1.5: vol_score = 15  # 자본 유입 급등
            elif recent_vol > avg_vol: vol_score = 5

        # 상대 성장치 (동종업계 비교를 위한 프록시)
        # 무료 API 한계로 베타(시장 대비 민감도)를 활용해 시장 대비 상대 강도 유추
        beta = info.get('beta', 1.0)
        relative_strength = "시장과 유사한 흐름"
        if beta > 1.2: relative_strength = "동종 업종 및 시장 대비 높은 변동성 및 성장 기대치"
        elif beta < 0.8: relative_strength = "동종 업종 대비 방어적이고 안정적인 흐름"
        
        # --- [미래 가치, 수급, 모멘텀 기반 종합 점수 계산] ---
        score = 20 # 기본 20점
        score += vol_score # 수급/자본 흐름 점수 (최대 15)
        
        rec = info.get('recommendationKey', 'none')
        if rec == 'strong_buy': score += 20
        elif rec == 'buy': score += 10
        elif rec in ['underperform', 'sell']: score -= 10
            
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100)) # 업사이드 (최대 20)
            
        ma50, ma200 = info.get('fiftyDayAverage'), info.get('twoHundredDayAverage')
        if current_price and ma50 and current_price > ma50: score += 10
        if current_price and ma200 and current_price > ma200: score += 10
            
        pe_ratio = info.get('trailingPE', info.get('forwardPE'))
        if pe_ratio:
            if pe_ratio < 15: score += 10 # 저평가 가치투자
            elif pe_ratio > 40: score -= 5 # 미래가치 선반영 (고평가)
            
        score = max(0, min(100, score))
        
        # 수혜주 / 관련 주식 (야후 API 추천 항목)
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
            "exchange": EXCHANGE_MAP.get(info.get('exchange', ''), info.get('exchange', '')),
            "score": score, "relative_strength": relative_strength,
            "related_tickers": related_tickers, "chart_buf": chart_buf
        }
    except Exception as e:
        print(f"Error: {e}")
        return None
