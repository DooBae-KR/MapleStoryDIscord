import yfinance as yf
import requests

KOR_TICKER_MAP = {
    "애플": "AAPL", "엔비디아": "NVDA", "테슬라": "TSLA",
    "마이크로소프트": "MSFT", "마소": "MSFT", "구글": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "페이스북": "META", "넷플릭스": "NFLX",
    "암드": "AMD", "티큐": "TQQQ", "에센피": "SPY", "나스닥": "QQQ",
    "삼전": "005930"
}

# 거래소 영문 코드를 친숙한 한글로 변환
EXCHANGE_MAP = {
    "KSC": "코스피 (KOSPI)",
    "KOE": "코스닥 (KOSDAQ)",
    "NMS": "나스닥 (NASDAQ)",
    "NYQ": "뉴욕증권거래소 (NYSE)",
    "ASE": "아멕스 (AMEX)"
}

def search_stock(keyword: str):
    keyword_upper = keyword.upper()
    
    for kor_name, ticker in KOR_TICKER_MAP.items():
        if keyword_upper in kor_name or kor_name in keyword_upper:
            return [{'symbol': ticker, 'display_symbol': ticker, 'name': kor_name}]

    try:
        naver_url = f"https://ac.finance.naver.com/ac?q={keyword}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(naver_url, headers=headers, timeout=3)
        data = res.json()
        
        if data.get('items') and len(data['items'][0]) > 0:
            results = []
            for item in data['items'][0][:5]:
                name = item[0]
                ticker = item[1]
                results.append({'symbol': ticker, 'display_symbol': ticker, 'name': name})
            return results
    except Exception as e:
        pass

    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={keyword}&quotesCount=5&newsCount=0"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        quotes = data.get('quotes', [])
        
        results = []
        for q in quotes:
            sym = q.get('symbol')
            if sym:
                name = q.get('shortname', q.get('longname', sym))
                display_sym = sym.replace('.KS', '').replace('.KQ', '')
                results.append({'symbol': sym, 'display_symbol': display_sym, 'name': name})
                
        return results
    except Exception as e:
        return []

def get_stock_info(query_ticker: str, kor_name: str = None):
    icon = "🇺🇸"
    currency = "USD"
    
    if query_ticker.isdigit() and len(query_ticker) == 6:
        try_tickers = [f"{query_ticker}.KS", f"{query_ticker}.KQ"]
    else:
        try_tickers = [query_ticker]
        
    if ".KS" in query_ticker or ".KQ" in query_ticker:
        icon = "🇰🇷"
        currency = "KRW"
        
    info = None
    ticker_obj = None
    final_query_ticker = query_ticker
    current_price = None

    for tk in try_tickers:
        temp_ticker = yf.Ticker(tk)
        try:
            temp_price = temp_ticker.fast_info.last_price
            if temp_price:
                ticker_obj = temp_ticker
                final_query_ticker = tk
                current_price = temp_price
                if ".KS" in tk or ".KQ" in tk:
                    icon = "🇰🇷"
                    currency = "KRW"
                break
        except Exception:
            continue

    if not ticker_obj or not current_price:
        return None

    try:
        info = ticker_obj.info
        
        # 이름 우선순위: 넘겨받은 한글이름 > yfinance 이름 > 티커
        name = kor_name if kor_name else info.get('shortName', final_query_ticker.replace('.KS', '').replace('.KQ', ''))
        
        sector = info.get('sector', '정보 없음')
        industry = info.get('industry', '정보 없음')
        
        # 거래소 정보
        raw_exchange = info.get('exchange', '')
        exchange = EXCHANGE_MAP.get(raw_exchange, raw_exchange)
        if not exchange and "KS" in final_query_ticker: exchange = "코스피 (KOSPI)"
        if not exchange and "KQ" in final_query_ticker: exchange = "코스닥 (KOSDAQ)"

        # 가격 정보 상세 (시가, 종가, 최고최저가)
        open_price = info.get('regularMarketOpen')
        prev_close = info.get('previousClose')
        high_52w = info.get('fiftyTwoWeekHigh')
        low_52w = info.get('fiftyTwoWeekLow')
        
        # --- [상대적 가치평가 및 모멘텀 기반 투자 점수 로직 (100점 만점)] ---
        score = 30  # 기본 점수 30점
        
        # 1. 애널리스트 투자의견 (최대 +20)
        rec = info.get('recommendationKey', 'none')
        if rec == 'strong_buy': score += 20
        elif rec == 'buy': score += 10
        elif rec in ['underperform', 'sell']: score -= 10
            
        # 2. 목표가 업사이드 (최대 +20)
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100))
            
        # 3. 기술적 모멘텀 (최대 +20)
        ma50 = info.get('fiftyDayAverage')
        ma200 = info.get('twoHundredDayAverage')
        if current_price and ma50 and current_price > ma50: score += 10 # 단기 상승추세
        if current_price and ma200 and current_price > ma200: score += 10 # 장기 상승추세
            
        # 4. 상대적 가치평가 (PER) (최대 +10)
        pe_ratio = info.get('trailingPE', info.get('forwardPE'))
        if pe_ratio:
            if pe_ratio < 15: score += 10 # 저평가
            elif pe_ratio < 25: score += 5  # 적정
            elif pe_ratio > 50: score -= 5  # 고평가
            
        score = max(0, min(100, score)) # 0 ~ 100 제한
        display_ticker = final_query_ticker.replace('.KS', '').replace('.KQ', '')
        
        return {
            "price": current_price,
            "open_price": open_price,
            "prev_close": prev_close,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "currency": currency,
            "icon": icon,
            "ticker": display_ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "exchange": exchange,
            "score": score
        }
    except Exception as e:
        print(f"Error fetching detailed data: {e}")
        return None
