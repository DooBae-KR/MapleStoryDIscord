import yfinance as yf
import requests

# 주요 해외 주식 및 줄임말 등 네이버에서 잘 못 잡는 특수 키워드만 최소한으로 남겨둡니다.
KOR_TICKER_MAP = {
    "애플": "AAPL", "엔비디아": "NVDA", "테슬라": "TSLA",
    "마이크로소프트": "MSFT", "마소": "MSFT", "구글": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "페이스북": "META", "넷플릭스": "NFLX",
    "암드": "AMD", "티큐": "TQQQ", "에센피": "SPY", "나스닥": "QQQ",
    "삼전": "005930" # 흔히 쓰는 줄임말 예외 처리
}

def search_stock(keyword: str):
    """
    1. 예외 사전(해외/줄임말) 검색
    2. 네이버 금융 검색 API를 통해 한글 종목명 -> 종목코드 변환 (국내 코스피/코스닥 전 종목)
    3. 둘 다 실패시 야후 파이낸스 영문 검색
    """
    keyword_upper = keyword.upper()
    
    # 1. 예외 사전 우선 검색 (해외 주식 및 줄임말)
    for kor_name, ticker in KOR_TICKER_MAP.items():
        if keyword_upper in kor_name or kor_name in keyword_upper:
            return [{'symbol': ticker, 'display_symbol': ticker, 'name': kor_name}]

    # 2. 네이버 금융 자동완성 API를 활용한 국내 주식 검색
    try:
        # 네이버 금융 자동완성 API (q: 검색어)
        naver_url = f"https://ac.finance.naver.com/ac?q={keyword}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(naver_url, headers=headers, timeout=3)
        data = res.json()
        
        # 네이버 검색 결과가 존재하면 (data['items'][0] 에 결과 리스트가 담김)
        if data.get('items') and len(data['items'][0]) > 0:
            results = []
            for item in data['items'][0][:5]:  # 최대 5개 가져옴
                name = item[0]     # 종목명 (예: 삼성전자)
                ticker = item[1]   # 종목코드 (예: 005930)
                
                # 네이버는 코스피/코스닥을 구별해주진 않지만 숫자로 반환함.
                # yfinance에서 국내 주식은 보통 .KS (코스피) 나 .KQ (코스닥) 가 필요합니다.
                # 이 로직을 단순화하기 위해 fetcher에서 처리하도록 코드로만 넘깁니다.
                results.append({'symbol': ticker, 'display_symbol': ticker, 'name': name})
            return results
            
    except Exception as e:
        print(f"Naver Search API Error: {e}")

    # 3. 네이버에서도 못 찾으면 야후 파이낸스 글로벌 검색으로 폴백
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
        print(f"Yahoo Search API Error: {e}")
        return []

def get_stock_info(query_ticker: str):
    icon = "🇺🇸"
    currency = "USD"
    
    # 한국 주식 티커(6자리) 처리 로직 고도화
    if query_ticker.isdigit() and len(query_ticker) == 6:
        # yfinance는 코스피(.KS)와 코스닥(.KQ)을 구분해야 데이터를 줍니다.
        # 일단 코스피(.KS)로 찔러보고 에러가 나면 코스닥(.KQ)으로 다시 시도하는 로직 적용
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

    # 코스피 -> 코스닥 순으로 데이터를 시도합니다.
    for tk in try_tickers:
        temp_ticker = yf.Ticker(tk)
        try:
            # 빠른 가격 조회를 통해 해당 티커가 유효한지(상장되어 있는지) 확인
            temp_price = temp_ticker.fast_info.last_price
            if temp_price:
                ticker_obj = temp_ticker
                final_query_ticker = tk
                current_price = temp_price
                
                # 한국 주식으로 확인되었을 경우 아이콘 변경
                if ".KS" in tk or ".KQ" in tk:
                    icon = "🇰🇷"
                    currency = "KRW"
                break
        except Exception:
            continue

    if not ticker_obj or not current_price:
        return None

    try:
        # 상세 정보 조회
        info = ticker_obj.info
        
        # 이름, 섹터 처리
        name = info.get('shortName')
        if not name or name == final_query_ticker:
            # yfinance에서 이름을 못 가져올 경우를 대비해 ticker 문자열 정리
            name = final_query_ticker.replace('.KS', '').replace('.KQ', '')
            
        sector = info.get('sector', '섹터 정보 없음')
        industry = info.get('industry', '업종 정보 없음')
        
        # 점수 계산
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
        display_ticker = final_query_ticker.replace('.KS', '').replace('.KQ', '')
        
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
        print(f"Error fetching detailed data for {final_query_ticker}: {e}")
        return None
