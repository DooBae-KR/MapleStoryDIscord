import yfinance as yf

def get_stock_info(ticker_symbol: str):
    is_korean = ticker_symbol.isdigit() and len(ticker_symbol) == 6
    query_ticker = ticker_symbol.upper()
    icon = "🇺🇸"
    
    if is_korean:
        query_ticker = f"{ticker_symbol}.KS"
        icon = "🇰🇷"
        
    ticker = yf.Ticker(query_ticker)
    
    try:
        # fast_info 대신 상세 정보가 담긴 info를 사용 (업종, 섹터, 애널리스트 분석 데이터 등)
        info = ticker.info
        
        # 현재가 추출
        current_price = info.get('currentPrice', info.get('regularMarketPrice'))
        if current_price is None:
            # info에서 실패할 경우 fast_info로 폴백
            current_price = ticker.fast_info.last_price
            
        currency = "KRW" if is_korean else "USD"
        name = info.get('shortName', ticker_symbol.upper())
        sector = info.get('sector', '섹터 정보 없음')
        industry = info.get('industry', '업종 정보 없음')
        
        # --- [투자 분석 점수 계산 로직 (100점 만점)] ---
        score = 50  # 기본 점수 50점 시작
        
        # 1. 애널리스트 추천 (최대 +20점 ~ -10점)
        rec = info.get('recommendationKey', 'none')
        rec_points = {'strong_buy': 20, 'buy': 10, 'hold': 0, 'underperform': -5, 'sell': -10}
        score += rec_points.get(rec, 0)
        
        # 2. 목표 주가 대비 업사이드 (최대 +20점)
        target_price = info.get('targetMeanPrice')
        if current_price and target_price and current_price < target_price:
            upside = (target_price - current_price) / current_price
            score += min(20, int(upside * 100)) # 1%당 1점, 최대 20점
            
        # 3. 50일 이동평균선 모멘텀 단기 추세 (최대 +10점)
        ma50 = info.get('fiftyDayAverage')
        if current_price and ma50 and current_price > ma50:
            score += 10  # 현재가가 50일 이평선보다 높으면 상승 추세로 판단
            
        # 점수 보정 (0 ~ 100점 사이)
        score = max(0, min(100, score))
        
        return {
            "price": current_price,
            "currency": currency,
            "icon": icon,
            "ticker": ticker_symbol.upper(),
            "name": name,
            "sector": sector,
            "industry": industry,
            "score": score
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
