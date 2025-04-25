import yfinance as yf
import pandas as pd
from src.config import config, TICKER, DATA_PERIOD, DATA_INTERVAL

def get_stock_data():
    """
    Yahoo Finance에서 주식 데이터를 가져옵니다.
    
    Returns:
        pandas.DataFrame: 주식 데이터 DataFrame
    """
    try:
        # 현재 설정된 티커 확인 (디버깅)
        print(f"데이터 가져오기: 현재 설정된 티커 = {config.TICKER}")
        
        # 데이터 다운로드
        df = yf.download(config.TICKER, period=config.DATA_PERIOD, interval=config.DATA_INTERVAL)
        
        if df.empty:
            raise ValueError(f"{config.TICKER} 데이터를 가져오지 못했습니다.")
        
        # 멀티인덱스 컬럼인 경우 처리
        if isinstance(df.columns, pd.MultiIndex):
            print("멀티인덱스 컬럼 처리 중...")
            # 첫 번째 레벨만 유지
            df.columns = df.columns.get_level_values(0)
        
        return df
    except Exception as e:
        print(f"주식 데이터 다운로드 중 오류 발생: {e}")
        return None 