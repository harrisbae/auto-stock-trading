import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import os
import sys
import matplotlib.font_manager as fm

# Add the project root to the Python path to import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators import add_all_indicators

# 한글 폰트 설정
# macOS 일반적인 한글 폰트 경로들
font_paths = [
    '/Library/Fonts/AppleGothic.ttf',               # 애플고딕
    '/Library/Fonts/AppleSDGothicNeo.ttc',          # 애플 SD 고딕 Neo
    '/System/Library/Fonts/AppleSDGothicNeo.ttc',   # 시스템 폰트 경로
    '/Library/Fonts/NanumGothic.ttf',               # 나눔고딕 (설치된 경우)
    '/Library/Fonts/NanumBarunGothic.ttf',          # 나눔바른고딕 (설치된 경우)
    '/System/Library/Fonts/Supplemental/AppleGothic.ttf'  # 보조 폰트 경로
]

# 사용 가능한 폰트 찾기
font_found = False
for font_path in font_paths:
    if os.path.exists(font_path):
        plt.rcParams['font.family'] = 'AppleGothic, Arial'
        fm.fontManager.addfont(font_path)
        print(f"한글 폰트 설정: {font_path}")
        font_found = True
        break

if not font_found:
    print("한글 폰트를 찾을 수 없습니다. 시스템에 한글 폰트를 설치해주세요.")
    
# 폰트 캐시 초기화 (필요한 경우)
fm.findfont(fm.FontProperties(family=['sans-serif']))

# 더 많은 시간 단위 데이터를 가져오기 위해 기간 확장
END_DATE = datetime.now()
# 30일로 확장 (주말 포함, 실제 거래일은 약 20-22일)
START_DATE = END_DATE - timedelta(days=30)
# 티커 기본 설정
TICKER = "SPY"
INITIAL_CAPITAL = 10000
COMMISSION = 0.001  # 0.1% commission per trade

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
        
        # 데이터가 충분한지 확인
        if len(data) < 30:
            print(f"경고: 데이터가 충분하지 않습니다. 받은 데이터 수: {len(data)}행")
            print("더 많은 데이터를 얻기 위해 기간을 확장합니다.")
        
        return data
    except Exception as e:
        print(f"데이터 다운로드 오류: {e}")
        return pd.DataFrame()

def add_hourly_indicators(df):
    """시간 단위 데이터에 기술적 지표 추가"""
    if df.empty:
        print("지표를 추가할 데이터가 없습니다.")
        return df
    
    try:
        # 시간 단위에 맞게 기간 조정
        # 일 단위의 25일은 시간 단위로 하면 25시간으로 적용
        # 데이터가 부족한 경우 윈도우 크기 조정
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
        
        # 200시간 이동평균선 (데이터가 부족하면 더 작은 윈도우 사용)
        sma_window = min(200, max(window_size, len(df) // 2))
        df['SMA200'] = df['Close'].rolling(window=sma_window).mean()
        
        return df
    except Exception as e:
        print(f"지표 추가 오류: {e}")
        return df

def run_backtest(df, params):
    """시간 단위 데이터로 백테스트 실행"""
    if df.empty:
        print("백테스트를 실행할 데이터가 없습니다.")
        return {
            'equity_curve': [INITIAL_CAPITAL],
            'buy_signals': [],
            'sell_signals': [],
            'trades': [],
            'parameters': params,
            'total_return': 0,
            'max_drawdown': 0,
            'trade_count': 0,
            'win_rate': 0,
            'final_value': INITIAL_CAPITAL,
        }
    
    # 전략 파라미터 추출
    buy_b_threshold = params.get('buy_b_threshold', 0.2)
    buy_mfi_threshold = params.get('buy_mfi_threshold', 20)
    sell_b_threshold = params.get('sell_b_threshold', 0.8)
    sell_mfi_threshold = params.get('sell_mfi_threshold', 80)
    use_mfi_filter = params.get('use_mfi_filter', True)
    
    # 포트폴리오 변수 초기화
    cash = INITIAL_CAPITAL
    shares = 0
    equity = []
    buy_signals = []
    sell_signals = []
    trades = []
    
    # 데이터 순회
    for i in range(len(df)):
        date = df.index[i]
        current_price = df['Close'].iloc[i]
        b_value = df['%B'].iloc[i] if not pd.isna(df['%B'].iloc[i]) else 0.5
        mfi_value = df['MFI'].iloc[i] if not pd.isna(df['MFI'].iloc[i]) else 50
        
        # 매수 신호 확인
        buy_signal = False
        sell_signal = False
        
        if shares == 0:  # 보유 주식이 없을 때만 매수 신호 확인
            if b_value <= buy_b_threshold:
                if not use_mfi_filter or (use_mfi_filter and mfi_value <= buy_mfi_threshold):
                    buy_signal = True
        
        elif shares > 0:  # 보유 주식이 있을 때만 매도 신호 확인
            if b_value >= sell_b_threshold:
                if not use_mfi_filter or (use_mfi_filter and mfi_value >= sell_mfi_threshold):
                    sell_signal = True
        
        # 매수 실행
        if buy_signal:
            shares_to_buy = int(cash / current_price)
            cost = shares_to_buy * current_price * (1 + COMMISSION)
            
            if shares_to_buy > 0 and cost <= cash:
                cash -= cost
                shares += shares_to_buy
                
                trades.append({
                    'date': date,
                    'type': 'buy',
                    'price': current_price,
                    'shares': shares_to_buy,
                    'value': shares_to_buy * current_price
                })
                
                buy_signals.append(i)
                print(f"매수: {date} - {shares_to_buy}주 @ ${current_price:.2f}, B값: {b_value:.4f}, MFI: {mfi_value:.2f}")
        
        # 매도 실행
        if sell_signal:
            cash += shares * current_price * (1 - COMMISSION)
            
            trades.append({
                'date': date,
                'type': 'sell',
                'price': current_price,
                'shares': shares,
                'value': shares * current_price
            })
            
            sell_signals.append(i)
            print(f"매도: {date} - {shares}주 @ ${current_price:.2f}, B값: {b_value:.4f}, MFI: {mfi_value:.2f}")
            
            shares = 0
        
        # 현재 자산 가치 추적
        equity.append(cash + shares * current_price)
    
    # 결과가 없는 경우 처리
    if not equity:
        print("경고: 자산 가치 데이터가 생성되지 않았습니다.")
        equity = [INITIAL_CAPITAL]
    
    # 마지막 포지션 종료
    if shares > 0:
        final_price = df['Close'].iloc[-1]
        cash += shares * final_price * (1 - COMMISSION)
        
        trades.append({
            'date': df.index[-1],
            'type': 'sell',
            'price': final_price,
            'shares': shares,
            'value': shares * final_price,
            'reason': 'backtest_end'
        })
        
        print(f"최종 청산: {df.index[-1]} - {shares}주 @ ${final_price:.2f}")
        shares = 0
        
        # 최종 자산 가치 업데이트
        equity[-1] = cash
    
    # 결과 계산
    total_return = (equity[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # 거래 빈도 계산
    trade_count = len(trades)
    won_trades = sum(1 for i in range(0, len(trades), 2) if i+1 < len(trades) and trades[i+1]['price'] > trades[i]['price'])
    lost_trades = sum(1 for i in range(0, len(trades), 2) if i+1 < len(trades) and trades[i+1]['price'] <= trades[i]['price'])
    win_rate = won_trades / (won_trades + lost_trades) * 100 if (won_trades + lost_trades) > 0 else 0
    
    # 최대 낙폭 계산
    drawdowns = []
    max_equity = equity[0]
    
    for current_equity in equity:
        if current_equity > max_equity:
            max_equity = current_equity
        if max_equity > 0:
            drawdown = (max_equity - current_equity) / max_equity * 100
            drawdowns.append(drawdown)
    
    max_drawdown = max(drawdowns) if drawdowns else 0
    
    # 결과 반환
    results = {
        'equity_curve': equity,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'trades': trades,
        'parameters': params,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'trade_count': trade_count,
        'win_rate': win_rate,
        'final_value': equity[-1],
    }
    
    return results

def plot_results(df, result, title=None):
    """백테스트 결과 시각화"""
    if df.empty or not result['equity_curve']:
        print("시각화할 데이터가 없습니다.")
        return
    
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        # 가격 차트와 지표
        ax1.plot(df.index, df['Close'], label='종가', color='black', alpha=0.75)
        
        if 'MA25' in df.columns:
            ax1.plot(df.index, df['MA25'], label='이동평균선', color='blue', alpha=0.6)
        
        if 'UpperBand' in df.columns and 'LowerBand' in df.columns:
            ax1.plot(df.index, df['UpperBand'], color='green', linestyle='--', alpha=0.6, label='상단밴드')
            ax1.plot(df.index, df['LowerBand'], color='red', linestyle='--', alpha=0.6, label='하단밴드')
        
        # 매수/매도 신호 표시
        for idx in result['buy_signals']:
            if idx < len(df):
                ax1.scatter(df.index[idx], df['Close'].iloc[idx], color='green', marker='^', s=100)
        
        for idx in result['sell_signals']:
            if idx < len(df):
                ax1.scatter(df.index[idx], df['Close'].iloc[idx], color='red', marker='v', s=100)
        
        # 자산 가치 변화
        # 데이터프레임 길이와 자산 가치 배열 길이 맞추기
        equity_data = result['equity_curve']
        if len(equity_data) > len(df):
            equity_data = equity_data[:len(df)]
        elif len(equity_data) < len(df):
            # 부족한 부분은 마지막 값으로 채움
            equity_data = equity_data + [equity_data[-1]] * (len(df) - len(equity_data))
        
        ax2.plot(df.index, equity_data, label='포트폴리오 가치', color='purple')
        
        # 그래프 설정
        params = result['parameters']
        params_str = ", ".join([f"{k}: {v}" for k, v in params.items()])
        
        # 성과 지표
        performance = f"수익률: {result['total_return']:.2f}%, 승률: {result['win_rate']:.2f}%, 거래: {result['trade_count']}"
        
        ax1.set_title(f"{TICKER} 시간 단위 백테스트 ({performance})\n{params_str}")
        ax1.set_ylabel('가격 ($)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        ax2.set_xlabel('날짜')
        ax2.set_ylabel('포트폴리오 가치 ($)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        return fig
    except Exception as e:
        print(f"시각화 오류: {e}")
        return None

def main():
    """메인 실행 함수"""
    global TICKER  # 전역 변수 TICKER를 사용
    
    # 1. 터미널 인자가 있으면 티커 설정
    if len(sys.argv) > 1:
        TICKER = sys.argv[1]
    
    print(f"설정된 Webhook URL: {os.environ.get('SLACK_WEBHOOK_URL', 'https://ho...EDIQY')}")
    
    # 2. 시간 단위 데이터 다운로드
    df = download_hourly_data(TICKER, START_DATE, END_DATE)
    
    if df.empty:
        print("데이터를 받지 못했습니다.")
        return
    
    # 3. 기술적 지표 추가
    df = add_hourly_indicators(df)
    
    # 4. 결측치 제거
    df = df.dropna()
    
    # 5. 데이터가 있는지 확인
    if len(df) == 0:
        print("처리 후 데이터가 없습니다.")
        return
    
    print(f"\n백테스트 시작: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')} (시간 단위)")
    print(f"최종 데이터 크기: {df.shape}")
    
    # 6. 전략 파라미터 설정
    strategy_params = [
        {
            'name': 'Default Strategy (No MFI)',
            'buy_b_threshold': 0.2,
            'sell_b_threshold': 0.8,
            'buy_mfi_threshold': 20,
            'sell_mfi_threshold': 80,
            'use_mfi_filter': False
        },
        {
            'name': 'More Aggressive B Values',
            'buy_b_threshold': 0.3,
            'sell_b_threshold': 0.7,
            'buy_mfi_threshold': 30,
            'sell_mfi_threshold': 70,
            'use_mfi_filter': False
        },
        {
            'name': 'Extreme B Values',
            'buy_b_threshold': 0.1,
            'sell_b_threshold': 0.9,
            'buy_mfi_threshold': 10,
            'sell_mfi_threshold': 90,
            'use_mfi_filter': False
        }
    ]
    
    # 7. 각 전략으로 백테스트 실행
    results = []
    
    for params in strategy_params:
        print(f"\n전략 '{params['name']}' 실행 중...")
        result = run_backtest(df, params)
        result['name'] = params['name']
        results.append(result)
        
        # 각 전략별 결과 출력
        print(f"전략 '{params['name']}' 결과:")
        print(f"총 수익률: {result['total_return']:.2f}%")
        print(f"최대 낙폭: {result['max_drawdown']:.2f}%")
        print(f"거래 횟수: {result['trade_count']}")
        print(f"승률: {result['win_rate']:.2f}%")
        print(f"최종 자산: ${result['final_value']:.2f}")
        
        # 차트 그리기
        fig = plot_results(df, result, title=f"{TICKER} 시간 단위 백테스트: {params['name']}")
        if fig:
            # 각 전략별로 다른 파일명 사용
            strategy_name_for_file = params['name'].replace(' ', '_').replace('(', '').replace(')', '')
            save_path = f"backtest/results/{TICKER}_{strategy_name_for_file}_backtest.png"
            fig.savefig(save_path)
            plt.close(fig)
            print(f"결과 차트가 {save_path}에 저장되었습니다.")
    
    # 8. 결과 비교
    print("\n전략 비교 결과:")
    # 수익률 기준으로 정렬
    sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    
    for i, result in enumerate(sorted_results):
        print(f"{i+1}. {result['name']}: {result['total_return']:.2f}% (승률: {result['win_rate']:.2f}%, 거래: {result['trade_count']})")
    
    best_strategy = sorted_results[0]
    print(f"\n최적 전략: {best_strategy['name']} (수익률: {best_strategy['total_return']:.2f}%)")
    
    # 9. 보고서 생성
    create_summary_report(results, df)
    
    return results

def create_summary_report(results, df):
    """백테스트 결과 요약 보고서 생성"""
    try:
        report_path = f"backtest/results/{TICKER}_hourly_backtest_report.md"
        
        with open(report_path, 'w') as f:
            f.write(f"# {TICKER} 시간 단위 백테스트 결과 요약\n\n")
            f.write(f"백테스트 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}\n")
            f.write(f"데이터 포인트: {len(df)}개\n\n")
            
            # 최적 전략의 차트 이미지 포함
            best_strategy = max(results, key=lambda x: x['total_return'])
            strategy_name_for_file = best_strategy['name'].replace(' ', '_').replace('(', '').replace(')', '')
            chart_path = f"backtest/results/{TICKER}_{strategy_name_for_file}_backtest.png"
            
            # 상대 경로로 이미지 링크 추가
            relative_chart_path = os.path.basename(chart_path)
            f.write(f"![{TICKER} 백테스트 차트]({relative_chart_path})\n\n")
            
            f.write("## 전략별 성과\n\n")
            f.write("| 순위 | 전략 | 총 수익률 | 최대 낙폭 | 거래 횟수 | 승률 | 최종 자산 |\n")
            f.write("|------|------|-----------|-----------|-----------|------|----------|\n")
            
            # 수익률 기준으로 결과 정렬
            sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
            
            for rank, result in enumerate(sorted_results, 1):
                f.write(f"| {rank} | {result['name']} | {result['total_return']:.2f}% | ")
                f.write(f"{result['max_drawdown']:.2f}% | {result['trade_count']} | ")
                f.write(f"{result['win_rate']:.2f}% | ${result['final_value']:.2f} |\n")
            
            f.write("\n## 최적 전략 파라미터\n\n")
            for key, value in best_strategy['parameters'].items():
                f.write(f"- **{key}**: {value}\n")
            
            f.write("\n## 거래 기록\n\n")
            if best_strategy['trades']:
                f.write("| 날짜 | 유형 | 가격 | 수량 | 거래액 |\n")
                f.write("|------|------|------|------|--------|\n")
                
                for trade in best_strategy['trades']:
                    trade_date = trade['date'].strftime('%Y-%m-%d %H:%M')
                    trade_type = "매수" if trade['type'] == 'buy' else "매도"
                    f.write(f"| {trade_date} | {trade_type} | ${trade['price']:.2f} | ")
                    f.write(f"{trade['shares']} | ${trade['value']:.2f} |\n")
            else:
                f.write("거래 내역이 없습니다.\n")
                
            # 모든 전략의 차트 링크 추가
            f.write("\n## 모든 전략의 차트\n\n")
            for result in results:
                strategy_name = result['name']
                strategy_name_for_file = strategy_name.replace(' ', '_').replace('(', '').replace(')', '')
                chart_path = f"{TICKER}_{strategy_name_for_file}_backtest.png"
                f.write(f"### {strategy_name}\n\n")
                f.write(f"![{strategy_name} 차트]({chart_path})\n\n")
        
        print(f"결과 요약 보고서가 {report_path}에 저장되었습니다.")
    except Exception as e:
        print(f"보고서 생성 오류: {e}")

if __name__ == "__main__":
    main() 