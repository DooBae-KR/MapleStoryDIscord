import yfinance as yf
import requests

def search_stock(keyword: str):
    """
    종목명 또는 키워드(예: '삼성', '애플', 'AAPL')로 주식을 검색하여
    연관된 종목 리스트를 반환합니다.
    """
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={keyword}&quotesCount=5&newsCount=0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        quotes = data.get('quotes', [])
        
        results = []
        for q in quotes:
            sym = q.get('symbol')
            # 펀드/지수 등 주식이 아닌 항목 필터링 목적이지만 일단 심볼이 있으면 가져옴
            if sym:
                name = q.get('shortname', q.get('longname', sym))
                # 화면에 예쁘게 보여주기 위해 .KS / .KQ 제거 (예: 005930.KS -> 005930)
                display_sym = sym.replace('.KS', '').replace('.KQ', '')
                results.append({'symbol': sym, 'display_symbol': display_sym, 'name': name})
                
        return results
    except Exception as e:
        print(f"Search API Error: {e}")
        return []

def get_stock_info(query_ticker: str):
    """
    종목 티커(예: AAPL, 005930.KS)를 받아 세부 분석 정보를 반환합니다.
    """
    icon = "🇺🇸"
    currency = "USD"
    
    # 6자리 숫자만 들어오면 한국 코스피로 간주
    if query_ticker.isdigit() and len(query_ticker) == 6:
        query_ticker = f"{query_ticker}.KS"
        
    if ".KS" in query_ticker or ".KQ" in query_ticker:
        icon = "🇰🇷"
        currency = "KRW"
        
    ticker = yf.Ticker(query_ticker)
    
    try:
        info = ticker.info
        current_price = info.get('currentPrice', info.get('regularMarketPrice'))
        
        if current_price is None:
            current_price = ticker.fast_info.last_price
            
        name = info.get('shortName', query_ticker)
        sector = info.get('sector', '섹터 정보 없음')
        industry = info.get('industry', '업종 정보 없음')
        
        # --- [투자 분석 점수 계산 로직 (100점 만점)] ---
        score = 50
        
        rec = info.get('recommendationKey', 'none')
        rec_points = {'strong_buy': 20, 'buy': 10, 'hold': 0, 'underperform': -5, 'sell': -10}
        score += rec_points.get(rec, 0)
        
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100))
            
        ma50 = info.get('fiftyDayAverage')
        if current_price and ma50 and current_price > ma50:
            score += 10
            
        score = max(0, min(100, score))
        
        # 화면 출력용 깔끔한 티커
        display_ticker = query_ticker.replace('.KS', '').replace('.KQ', '')
        
        return {
            "price": current_price,
            "currency": currency,
            "icon": icon,
            "ticker": display_ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "score": score
        }
    except Exception as e:
        print(f"Error fetching data for {query_ticker}: {e}")
        return None
