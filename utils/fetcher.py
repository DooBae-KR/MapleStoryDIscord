import yfinance as yf
import requests

# 한글 검색어 사전: 자주 찾는 기업들의 한글 이름과 티커를 매핑합니다.
KOR_TICKER_MAP = {
    # 해외 주식
    "애플": "AAPL",
    "엔비디아": "NVDA",
    "테슬라": "TSLA",
    "마이크로소프트": "MSFT",
    "마소": "MSFT",
    "구글": "GOOGL",
    "알파벳": "GOOGL",
    "아마존": "AMZN",
    "메타": "META",
    "페이스북": "META",
    "넷플릭스": "NFLX",
    "암드": "AMD",
    "티큐": "TQQQ",
    "에센피": "SPY",
    "나스닥": "QQQ",
    # 국내 주식
    "삼성전자": "005930",
    "삼성": "005930",
    "하이닉스": "000660",
    "SK하이닉스": "000660",
    "현대차": "005380",
    "기아": "000270",
    "카카오": "035720",
    "네이버": "035420",
    "NAVER": "035420",
    "에코프로": "086520",
    "에코프로비엠": "247540",
    "포스코": "005490",
    "POSCO홀딩스": "005490",
    "셀트리온": "068270"
}

def search_stock(keyword: str):
    """
    종목명 또는 키워드로 주식을 검색합니다.
    1. 먼저 한글 사전에 등록된 종목인지 확인합니다.
    2. 사전에 없으면 야후 파이낸스 검색 API를 사용합니다.
    """
    keyword_upper = keyword.upper()
    
    # 1. 한글 사전 검색 (완전 일치 또는 포함)
    for kor_name, ticker in KOR_TICKER_MAP.items():
        if keyword_upper in kor_name or kor_name in keyword_upper:
            # 사전에 있으면 해당 티커를 강제로 최상단 결과로 반환
            return [{'symbol': ticker, 'display_symbol': ticker, 'name': kor_name}]

    # 2. 사전에 없는 경우 야후 파이낸스 API 검색 (영문, 티커 등)
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={keyword}&quotesCount=5&newsCount=0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
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
        print(f"Search API Error: {e}")
        return []

def get_stock_info(query_ticker: str):
    icon = "🇺🇸"
    currency = "USD"
    
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
