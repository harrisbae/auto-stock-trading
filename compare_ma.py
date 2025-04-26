import pandas as pd
import numpy as np
import yfinance as yf

def compare_ma_periods():
    """
    MA20과 MA25를 사용한 볼린저 밴드의 차이와 신호 발생 차이를 비교합니다.
    """
    # SPY 데이터 가져오기 (기간을 1년으로 늘림)
    ticker = 'SPY'
    df = yf.download(ticker, period='1y', interval='1d')
    print(f'데이터 행 수: {len(df)}')
    
    # 멀티인덱스 처리 - 레벨 1 제거
    df = df.droplevel('Ticker', axis=1)
    
    # MA20 기반 지표
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['UpperBand20'] = df['MA20'] + (2 * df['STD20'])
    df['LowerBand20'] = df['MA20'] - (2 * df['STD20'])
    
    # MA25 기반 지표
    df['MA25'] = df['Close'].rolling(window=25).mean()
    df['STD25'] = df['Close'].rolling(window=25).std()
    df['UpperBand25'] = df['MA25'] + (2 * df['STD25'])
    df['LowerBand25'] = df['MA25'] - (2 * df['STD25'])
    
    # %B 계산 - 안전하게 처리
    df['%B20'] = np.nan
    mask20 = (~df['UpperBand20'].isna()) & (~df['LowerBand20'].isna()) & ((df['UpperBand20'] - df['LowerBand20']) > 1e-10)
    df.loc[mask20, '%B20'] = (df.loc[mask20, 'Close'] - df.loc[mask20, 'LowerBand20']) / (df.loc[mask20, 'UpperBand20'] - df.loc[mask20, 'LowerBand20'])
    
    df['%B25'] = np.nan
    mask25 = (~df['UpperBand25'].isna()) & (~df['LowerBand25'].isna()) & ((df['UpperBand25'] - df['LowerBand25']) > 1e-10)
    df.loc[mask25, '%B25'] = (df.loc[mask25, 'Close'] - df.loc[mask25, 'LowerBand25']) / (df.loc[mask25, 'UpperBand25'] - df.loc[mask25, 'LowerBand25'])
    
    # 신호 생성
    df['Signal20'] = 'Hold'
    df.loc[df['%B20'] < 0.2, 'Signal20'] = 'Buy'
    df.loc[df['%B20'] > 0.8, 'Signal20'] = 'Sell'
    
    df['Signal25'] = 'Hold'
    df.loc[df['%B25'] < 0.2, 'Signal25'] = 'Buy'
    df.loc[df['%B25'] > 0.8, 'Signal25'] = 'Sell'
    
    # 신호 차이 계산
    df['SignalDiff'] = df['Signal20'] != df['Signal25']
    
    # 유효한 데이터 필터링
    valid_mask = (~df['%B20'].isna()) & (~df['%B25'].isna())
    valid_df = df[valid_mask].copy()
    
    print(f"\n유효한 데이터 행 수: {len(valid_df)}")
    
    # 결과 출력
    print('\n최근 20일 유효 데이터 비교:')
    cols_to_show = ['Close', '%B20', '%B25', 'Signal20', 'Signal25']
    
    # 최근 유효한 데이터 20개 출력
    print(valid_df[cols_to_show].tail(20))
    
    # 신호 차이 분석
    diff_count = valid_df['SignalDiff'].sum()
    valid_days = len(valid_df)
    
    # 0으로 나누기 방지
    if valid_days > 0:
        diff_percent = diff_count / valid_days * 100
    else:
        diff_percent = 0
    
    print(f'\n신호 차이가 나는 날의 수: {diff_count} / {valid_days} 유효일 ({diff_percent:.2f}%)')
    
    # 신호 유형별 카운트
    buy_count20 = (valid_df['Signal20'] == 'Buy').sum()
    sell_count20 = (valid_df['Signal20'] == 'Sell').sum()
    hold_count20 = (valid_df['Signal20'] == 'Hold').sum()
    
    buy_count25 = (valid_df['Signal25'] == 'Buy').sum()
    sell_count25 = (valid_df['Signal25'] == 'Sell').sum()
    hold_count25 = (valid_df['Signal25'] == 'Hold').sum()
    
    print('\n신호 유형 통계:')
    print(f'MA20 기반: Buy({buy_count20}), Sell({sell_count20}), Hold({hold_count20})')
    print(f'MA25 기반: Buy({buy_count25}), Sell({sell_count25}), Hold({hold_count25})')
    
    # 각 신호별 차이 분석
    buy_diff = buy_count20 - buy_count25
    sell_diff = sell_count20 - sell_count25
    hold_diff = hold_count20 - hold_count25
    
    # 0으로 나누기 방지
    if valid_days > 0:
        buy_diff_percent = buy_diff / valid_days * 100
        sell_diff_percent = sell_diff / valid_days * 100
        hold_diff_percent = hold_diff / valid_days * 100
    else:
        buy_diff_percent = sell_diff_percent = hold_diff_percent = 0
    
    print('\n신호 차이 분석:')
    print(f'Buy 신호 차이 (MA20 - MA25): {buy_diff} ({buy_diff_percent:.2f}%)')
    print(f'Sell 신호 차이 (MA20 - MA25): {sell_diff} ({sell_diff_percent:.2f}%)')
    print(f'Hold 신호 차이 (MA20 - MA25): {hold_diff} ({hold_diff_percent:.2f}%)')
    
    # 날짜별 신호 전환 분석
    signal_changes = valid_df[valid_df['SignalDiff']]
    
    print('\n날짜별 신호 전환 (최대 10개):')
    for idx, row in signal_changes.head(10).iterrows():
        print(f"{idx.strftime('%Y-%m-%d')}: MA20 = {row['Signal20']}, MA25 = {row['Signal25']}")
    
    # 0으로 나누기 방지
    if valid_days > 0:
        conclusion_percent = diff_count / valid_days * 100
    else:
        conclusion_percent = 0
        
    print(f'\n결론: MA 기간이 20일에서 25일로 변경됨에 따라 신호 발생에 {conclusion_percent:.2f}%의 차이가 있습니다.')

if __name__ == "__main__":
    compare_ma_periods() 