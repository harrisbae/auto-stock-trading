import yfinance as yf
import pandas as pd
from src.config import config, TICKER, DATA_PERIOD, DATA_INTERVAL

def get_stock_data(ticker=None):
    """
    Yahoo Finance에서 주식 데이터를 가져옵니다.
    
    Args:
        ticker (str, optional): 주식 종목 티커 심볼. 지정하지 않으면 config에서 가져옴.
        
    Returns:
        pandas.DataFrame: 주식 데이터 DataFrame
    """
    try:
        # 티커 설정 (매개변수로 전달된 경우 우선 사용)
        used_ticker = ticker if ticker is not None else config.TICKER
        
        # 현재 설정된 티커 확인 (디버깅)
        print(f"데이터 가져오기: {used_ticker} 종목 데이터 다운로드 중...")
        
        # PLTR이 하드코딩되어 있는지 확인 (디버깅용)
        if used_ticker == 'PLTR' and ticker is not None and ticker != 'PLTR':
            print(f"경고: 실제 요청 티커({ticker})와 사용 티커(PLTR)가 다릅니다. 요청된 티커를 사용합니다.")
            used_ticker = ticker
        
        # 데이터 다운로드 - 확실하게 used_ticker 사용
        df = yf.download(
            tickers=used_ticker,  # 명시적으로 tickers 파라미터 지정
            period=config.DATA_PERIOD, 
            interval=config.DATA_INTERVAL,
            progress=False  # 진행 상황 표시 비활성화
        )
        
        if df.empty:
            raise ValueError(f"{used_ticker} 데이터를 가져오지 못했습니다.")
        
        # 멀티인덱스 컬럼인 경우 처리
        if isinstance(df.columns, pd.MultiIndex):
            print("멀티인덱스 컬럼 처리 중...")
            # 첫 번째 레벨만 유지
            df.columns = df.columns.get_level_values(0)
        
        print(f"데이터프레임 구조: {df.shape}")
        print(f"데이터프레임 컬럼: {list(df.columns)}")
        
        # 데이터 확인 (디버깅용)
        if not df.empty:
            print(f"{used_ticker} 데이터 성공적으로 로드됨: 최근 가격 ${df['Close'].iloc[-1]:.2f}")
        
        return df
    except Exception as e:
        print(f"주식 데이터 다운로드 중 오류 발생: {e}")
        return pd.DataFrame()  # 빈 데이터프레임 반환 