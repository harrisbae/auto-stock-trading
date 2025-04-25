import pandas as pd
import numpy as np
from src.config import MA_PERIOD, BOLLINGER_BANDS_STD, MFI_PERIOD

def calculate_bollinger_bands(df):
    """
    볼린저 밴드 및 %B 지표를 계산합니다.
    
    Args:
        df (pandas.DataFrame): 주식 데이터
        
    Returns:
        pandas.DataFrame: 볼린저 밴드가 추가된 데이터
    """
    # 디버깅: 데이터프레임 구조 확인
    print("데이터프레임 구조:", df.shape)
    print("데이터프레임 컬럼:", df.columns.tolist())
    
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=MA_PERIOD).mean()
    df['STD'] = df['Close'].rolling(window=MA_PERIOD).std()
    df['UpperBand'] = df['MA20'] + (BOLLINGER_BANDS_STD * df['STD'])
    df['LowerBand'] = df['MA20'] - (BOLLINGER_BANDS_STD * df['STD'])
    
    # 간단한 방식으로 계산
    try:
        b_values = []
        for i in range(len(df)):
            close = df['Close'].iloc[i]
            lower = df['LowerBand'].iloc[i]
            upper = df['UpperBand'].iloc[i]
            
            if pd.isna(lower) or pd.isna(upper) or upper == lower:
                b_values.append(np.nan)
            else:
                b_value = (close - lower) / (upper - lower)
                b_values.append(b_value)
        
        df['%B'] = b_values
    except Exception as e:
        print(f"볼린저 밴드 계산 중 오류 발생: {e}")
        # 오류 발생 시 %B 열을 NaN으로 초기화
        df['%B'] = np.nan
    
    return df

def calculate_mfi(df, period=MFI_PERIOD):
    """
    Money Flow Index (MFI) 지표를 계산합니다.
    
    Args:
        df (pandas.DataFrame): 주식 데이터
        period (int, optional): MFI 계산 기간
        
    Returns:
        pandas.DataFrame: MFI가 추가된 데이터
    """
    df = df.copy()
    
    try:
        # Typical Price 계산
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        
        # Positive/Negative Money Flow 계산
        positive_flow = []
        negative_flow = []
        
        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(money_flow.iloc[i])
                negative_flow.append(0)
            else:
                positive_flow.append(0)
                negative_flow.append(money_flow.iloc[i])
        
        # 첫 번째 인덱스는 계산할 수 없으므로 0으로 설정
        positive_flow.insert(0, 0)
        negative_flow.insert(0, 0)
        
        # Money Flow Ratio 계산
        positive_mf = pd.Series(positive_flow, index=df.index).rolling(window=period).sum()
        negative_mf = pd.Series(negative_flow, index=df.index).rolling(window=period).sum()
        
        # MFI 계산 (0으로 나누는 오류 방지)
        mfi_values = []
        for i in range(len(df)):
            pos = positive_mf.iloc[i]
            neg = negative_mf.iloc[i]
            
            if pd.isna(pos) or pd.isna(neg) or (pos + neg) == 0:
                mfi_values.append(np.nan)
            else:
                mfi_value = 100 * (pos / (pos + neg))
                mfi_values.append(mfi_value)
        
        df['MFI'] = mfi_values
    except Exception as e:
        print(f"MFI 계산 중 오류 발생: {e}")
        # 오류 발생 시 MFI 열을 NaN으로 초기화
        df['MFI'] = np.nan
    
    return df

def add_all_indicators(df):
    """
    모든 기술적 지표를 데이터프레임에 추가합니다.
    
    Args:
        df (pandas.DataFrame): 주식 데이터
        
    Returns:
        pandas.DataFrame: 지표가 추가된 데이터
    """
    df = calculate_bollinger_bands(df)
    df = calculate_mfi(df)
    return df 