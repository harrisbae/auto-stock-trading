import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import os
import sys

# Add the project root to the Python path to import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators import add_all_indicators

# 최근 3일간의 시간 단위 데이터 가져오기 설정
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3)  # 주말 제외하면 대략 1-2일 데이터
TICKER = "SPY"  # 기본 티커 설정

def download_hourly_data(ticker, start_date, end_date):
    """시간 단위 데이터 다운로드"""
    print(f"Downloading {ticker} hourly data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    try:
        # 시간 단위 데이터 설정 (interval="1h")
        data = yf.download(ticker, start=start_date, end=end_date, interval="1h")
        
        # 다중 인덱스 열 있는 경우 평탄화
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        
        # 데이터프레임 정보 출력
        print(f"데이터프레임 구조: {data.shape}")
        print(f"데이터프레임 컬럼: {list(data.columns)}")
        
        return data
    except Exception as e:
        print(f"데이터 다운로드 오류: {e}")
        return pd.DataFrame()

def add_hourly_indicators(df):
    """시간 단위 데이터에 볼린저 밴드 지표 추가"""
    if df.empty:
        print("지표를 추가할 데이터가 없습니다.")
        return df
    
    try:
        # 시간 단위에 맞게 기간 조정
        window_size = min(25, max(5, len(df) // 4))
        print(f"이동평균 윈도우 크기: {window_size}")
        
        # 이동평균선
        df['MA25'] = df['Close'].rolling(window=window_size).mean()
        
        # 볼린저 밴드
        df['STD'] = df['Close'].rolling(window=window_size).std()
        df['UpperBand'] = df['MA25'] + 2 * df['STD']
        df['LowerBand'] = df['MA25'] - 2 * df['STD']
        
        # %B 계산
        df['%B'] = (df['Close'] - df['LowerBand']) / (df['UpperBand'] - df['LowerBand'])
        
        # MFI 계산 (Money Flow Index)
        mfi_window = min(14, max(5, len(df) // 6))
        print(f"MFI 윈도우 크기: {mfi_window}")
        
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        
        positive_flow = money_flow.copy()
        negative_flow = money_flow.copy()
        
        # 양의 흐름과 음의 흐름 구분
        positive_flow[typical_price < typical_price.shift(1)] = 0
        negative_flow[typical_price > typical_price.shift(1)] = 0
        
        # MFI 기간 합계
        positive_mf_sum = positive_flow.rolling(window=mfi_window).sum()
        negative_mf_sum = negative_flow.rolling(window=mfi_window).sum()
        
        # MFI 계산
        money_ratio = positive_mf_sum / negative_mf_sum
        df['MFI'] = 100 - (100 / (1 + money_ratio))
        
        return df
    except Exception as e:
        print(f"지표 추가 오류: {e}")
        return df

def show_hourly_data():
    """시간 단위 데이터를 가져와서 표시"""
    # 1. 시간 단위 데이터 다운로드
    df = download_hourly_data(TICKER, START_DATE, END_DATE)
    
    if df.empty:
        print("데이터를 받지 못했습니다.")
        return
    
    # 2. 기술적 지표 추가
    df = add_hourly_indicators(df)
    
    # 3. 결측치 제거
    df = df.dropna()
    
    # 4. 데이터가 있는지 확인
    if len(df) == 0:
        print("처리 후 데이터가 없습니다.")
        return
    
    # 5. 시간 단위 데이터 표시
    print(f"\n{TICKER} 시간 단위 데이터 ({START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')})")
    print("=" * 100)
    
    # 5-1. 원본 데이터 표시
    pd.set_option('display.max_rows', None)  # 모든 행 표시
    pd.set_option('display.width', 200)      # 출력 너비 설정
    pd.set_option('display.float_format', '{:.2f}'.format)  # 소수점 2자리까지 표시
    
    # 5-2. 데이터프레임 가공
    # 표시할 컬럼 선택
    display_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'MA25', 'UpperBand', 'LowerBand', '%B', 'MFI']
    # 가능한 컬럼만 선택
    display_columns = [col for col in display_columns if col in df.columns]
    
    # 날짜 시간 인덱스 처리
    df_display = df[display_columns].copy()
    df_display.index = df_display.index.strftime('%Y-%m-%d %H:%M')
    
    # 매수/매도 신호 추가
    df_display['매수신호'] = (df['%B'] <= 0.1)
    df_display['매도신호'] = (df['%B'] >= 0.9)
    
    # 최근 데이터부터 표시 (역순)
    print(df_display.iloc[::-1])
    
    # 5-3. 매수/매도 신호 표시
    buy_signals = df[df['%B'] <= 0.1].index.strftime('%Y-%m-%d %H:%M').tolist()
    sell_signals = df[df['%B'] >= 0.9].index.strftime('%Y-%m-%d %H:%M').tolist()
    
    print("\n매수 신호 발생 시점:")
    if buy_signals:
        for i, signal_time in enumerate(buy_signals):
            b_value = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], '%B']
            price = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], 'Close']
            print(f"{i+1}. {signal_time} - 가격: ${price:.2f}, %B: {b_value:.4f}")
    else:
        print("매수 신호가 없습니다.")
    
    print("\n매도 신호 발생 시점:")
    if sell_signals:
        for i, signal_time in enumerate(sell_signals):
            b_value = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], '%B']
            price = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], 'Close']
            print(f"{i+1}. {signal_time} - 가격: ${price:.2f}, %B: {b_value:.4f}")
    else:
        print("매도 신호가 없습니다.")
    
    # 6. 지표 요약 정보
    print("\n현재 기술적 지표 상태:")
    latest_data = df.iloc[-1]
    print(f"현재 가격: ${latest_data['Close']:.2f}")
    print(f"볼린저 밴드 상단: ${latest_data['UpperBand']:.2f}")
    print(f"볼린저 밴드 중앙: ${latest_data['MA25']:.2f}")
    print(f"볼린저 밴드 하단: ${latest_data['LowerBand']:.2f}")
    print(f"%B 값: {latest_data['%B']:.4f}")
    
    if 'MFI' in latest_data:
        print(f"MFI: {latest_data['MFI']:.2f}")
    
    # 7. 시그널 판단
    latest_b = latest_data['%B']
    signal = "관망"
    
    if latest_b <= 0.1:
        signal = "매수"
    elif latest_b >= 0.9:
        signal = "매도"
    elif latest_b <= 0.2:
        signal = "매수 고려"
    elif latest_b >= 0.8:
        signal = "매도 고려"
    
    print(f"\n현재 시그널: {signal}")
    
    # 8. 보고서 파일로 저장
    report_path = f"backtest/results/{TICKER}_hourly_data_report.txt"
    
    with open(report_path, 'w') as f:
        f.write(f"{TICKER} 시간 단위 데이터 보고서 ({START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')})\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("시간별 데이터:\n")
        f.write(df_display.iloc[::-1].to_string() + "\n\n")
        
        f.write("매수 신호 발생 시점:\n")
        if buy_signals:
            for i, signal_time in enumerate(buy_signals):
                b_value = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], '%B']
                price = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], 'Close']
                f.write(f"{i+1}. {signal_time} - 가격: ${price:.2f}, %B: {b_value:.4f}\n")
        else:
            f.write("매수 신호가 없습니다.\n")
        
        f.write("\n매도 신호 발생 시점:\n")
        if sell_signals:
            for i, signal_time in enumerate(sell_signals):
                b_value = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], '%B']
                price = df.loc[df.index[df.index.strftime('%Y-%m-%d %H:%M') == signal_time].tolist()[0], 'Close']
                f.write(f"{i+1}. {signal_time} - 가격: ${price:.2f}, %B: {b_value:.4f}\n")
        else:
            f.write("매도 신호가 없습니다.\n")
        
        f.write("\n현재 기술적 지표 상태:\n")
        f.write(f"현재 가격: ${latest_data['Close']:.2f}\n")
        f.write(f"볼린저 밴드 상단: ${latest_data['UpperBand']:.2f}\n")
        f.write(f"볼린저 밴드 중앙: ${latest_data['MA25']:.2f}\n")
        f.write(f"볼린저 밴드 하단: ${latest_data['LowerBand']:.2f}\n")
        f.write(f"%B 값: {latest_data['%B']:.4f}\n")
        
        if 'MFI' in latest_data:
            f.write(f"MFI: {latest_data['MFI']:.2f}\n")
        
        f.write(f"\n현재 시그널: {signal}\n")
    
    print(f"\n상세 보고서가 {report_path}에 저장되었습니다.")

if __name__ == "__main__":
    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        TICKER = sys.argv[1]
    
    show_hourly_data() 