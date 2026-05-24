import yfinance as yf

def get_stock_info(ticker_symbol: str):
    """
    종목 코드를 받아 현재가와 국가 아이콘을 반환합니다.
    한국 주식(숫자 6자리)일 경우 뒤에 .KS를 붙여서 검색합니다.
    """
    # 한국 주식은 보통 6자리 숫자입니다 (예: 삼성전자 005930)
    is_korean = ticker_symbol.isdigit() and len(ticker_symbol) == 6
    
    query_ticker = ticker_symbol.upper()
    icon = "🇺🇸"
    
    if is_korean:
        query_ticker = f"{ticker_symbol}.KS"  # 코스피 기준 (코스닥은 .KQ)
        icon = "🇰🇷"
        
    ticker = yf.Ticker(query_ticker)
    
    try:
        # yfinance의 fast_info를 사용하면 가볍게 현재가를 가져올 수 있습니다.
        data = ticker.fast_info
        current_price = data.last_price
        
        currency = "KRW" if is_korean else "USD"
        
        return {
            "price": current_price,
            "currency": currency,
            "icon": icon,
            "ticker": ticker_symbol.upper()
        }
    except Exception as e:
        return None
