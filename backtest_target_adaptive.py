import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def backtest_adaptive_target_strategies():
    """
    적응형 목표가 전략을 백테스팅합니다.
    
    - 초기 목표가는 현재가로 설정
    - 매도 후 새로운 목표가는 매수 시점의 가격으로 설정
    - 목표 수익률은 5%로 설정
    """
    # 데이터 가져오기 (3년치 데이터로 충분한 백테스팅)
    ticker = 'SPY'
    df = yf.download(ticker, period='3y', interval='1d')
    print(f'데이터 행 수: {len(df)}')
    
    # 멀티인덱스 처리
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel('Ticker', axis=1)
    
    # 초기 자본금
    initial_capital = 10000
    
    # MA20 및 MA25 계산
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA25'] = df['Close'].rolling(window=25).mean()
    
    # 유효한 데이터만 사용
    valid_df = df.dropna(subset=['MA20', 'MA25']).copy()
    
    # 전략별 변수 초기화
    valid_df['Position20'] = 0  # 포지션 (1: 매수, 0: 중립, -1: 매도)
    valid_df['Position25'] = 0  # 포지션 (1: 매수, 0: 중립, -1: 매도)
    
    # 적응형 목표가 변수 초기화
    buy_price_20 = None  # MA20 전략 매수 가격
    sell_price_20 = None  # MA20 전략 매도 가격
    buy_price_25 = None  # MA25 전략 매수 가격
    sell_price_25 = None  # MA25 전략 매도 가격
    
    target_gain = 0.05  # 목표 수익률 5%
    
    # MA20 전략은 MA 아래 5% 지점을 매수 포인트로 사용
    buy_threshold_20 = 0.95
    # MA25 전략은 MA 아래 4% 지점을 매수 포인트로 사용하여 차별화
    buy_threshold_25 = 0.96
    
    # 시뮬레이션 실행
    for i in range(1, len(valid_df)):
        price = valid_df['Close'].iloc[i]
        prev_price = valid_df['Close'].iloc[i-1]
        prev_pos20 = valid_df['Position20'].iloc[i-1]
        prev_pos25 = valid_df['Position25'].iloc[i-1]
        ma20 = valid_df['MA20'].iloc[i]
        ma25 = valid_df['MA25'].iloc[i]
        
        # MA20 전략 로직
        if prev_pos20 == 0:  # 중립 상태
            if price < ma20 * buy_threshold_20:  # MA20 아래 5% 지점 도달 시 매수
                valid_df.loc[valid_df.index[i], 'Position20'] = 1
                buy_price_20 = price
                sell_price_20 = price * (1 + target_gain)  # 매수가 기준 목표가 설정
            else:
                valid_df.loc[valid_df.index[i], 'Position20'] = 0
        elif prev_pos20 == 1:  # 매수 상태
            if price >= sell_price_20:  # 목표가 도달 시 매도
                valid_df.loc[valid_df.index[i], 'Position20'] = 0
                buy_price_20 = None
                sell_price_20 = None
            else:
                valid_df.loc[valid_df.index[i], 'Position20'] = 1
        
        # MA25 전략 로직
        if prev_pos25 == 0:  # 중립 상태
            if price < ma25 * buy_threshold_25:  # MA25 아래 4% 지점 도달 시 매수 (차별화된 매수 포인트)
                valid_df.loc[valid_df.index[i], 'Position25'] = 1
                buy_price_25 = price
                sell_price_25 = price * (1 + target_gain)  # 매수가 기준 목표가 설정
            else:
                valid_df.loc[valid_df.index[i], 'Position25'] = 0
        elif prev_pos25 == 1:  # 매수 상태
            if price >= sell_price_25:  # 목표가 도달 시 매도
                valid_df.loc[valid_df.index[i], 'Position25'] = 0
                buy_price_25 = None
                sell_price_25 = None
            else:
                valid_df.loc[valid_df.index[i], 'Position25'] = 1
    
    # 수익률 계산
    valid_df['Return'] = valid_df['Close'].pct_change()
    
    # 각 전략의 일별 수익률
    valid_df['Strategy20_Return'] = valid_df['Position20'].shift(1) * valid_df['Return']
    valid_df['Strategy25_Return'] = valid_df['Position25'].shift(1) * valid_df['Return']
    
    # 누적 수익률 계산
    valid_df['Cum_Return'] = (1 + valid_df['Return']).cumprod()
    valid_df['Cum_Strategy20'] = (1 + valid_df['Strategy20_Return']).cumprod()
    valid_df['Cum_Strategy25'] = (1 + valid_df['Strategy25_Return']).cumprod()
    
    # 포트폴리오 가치 계산
    valid_df['Portfolio_20'] = initial_capital * valid_df['Cum_Strategy20']
    valid_df['Portfolio_25'] = initial_capital * valid_df['Cum_Strategy25']
    valid_df['Buy_Hold'] = initial_capital * valid_df['Cum_Return']
    
    # 성과 지표 계산
    # 1. 연간 수익률
    days = (valid_df.index[-1] - valid_df.index[0]).days
    annual_return_20 = (valid_df['Cum_Strategy20'].iloc[-1] ** (365 / days)) - 1
    annual_return_25 = (valid_df['Cum_Strategy25'].iloc[-1] ** (365 / days)) - 1
    annual_return_bh = (valid_df['Cum_Return'].iloc[-1] ** (365 / days)) - 1
    
    # 2. 최대 낙폭 (Maximum Drawdown)
    def calculate_drawdown(cum_returns):
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns / rolling_max) - 1
        return drawdown.min()
    
    max_dd_20 = calculate_drawdown(valid_df['Cum_Strategy20'])
    max_dd_25 = calculate_drawdown(valid_df['Cum_Strategy25'])
    max_dd_bh = calculate_drawdown(valid_df['Cum_Return'])
    
    # 3. 샤프 비율 (Sharpe Ratio)
    risk_free_rate = 0.03  # 가정: 연간 3%
    daily_rf = (1 + risk_free_rate) ** (1/365) - 1
    
    sharpe_20 = (valid_df['Strategy20_Return'].mean() - daily_rf) / valid_df['Strategy20_Return'].std() * np.sqrt(252)
    sharpe_25 = (valid_df['Strategy25_Return'].mean() - daily_rf) / valid_df['Strategy25_Return'].std() * np.sqrt(252)
    sharpe_bh = (valid_df['Return'].mean() - daily_rf) / valid_df['Return'].std() * np.sqrt(252)
    
    # 결과 출력
    print("\n===== 적응형 목표가 전략 백테스팅 결과 =====")
    print(f"테스트 기간: {valid_df.index[0].strftime('%Y-%m-%d')} ~ {valid_df.index[-1].strftime('%Y-%m-%d')} ({days}일)")
    print(f"초기 자본금: ${initial_capital:,.2f}")
    print(f"목표 수익률: {target_gain*100:.1f}%")
    print(f"MA20 매수 기준: MA20 아래 {(1-buy_threshold_20)*100:.1f}%")
    print(f"MA25 매수 기준: MA25 아래 {(1-buy_threshold_25)*100:.1f}%")
    
    print("\n1. 최종 포트폴리오 가치:")
    print(f"   - MA20 적응형 전략: ${valid_df['Portfolio_20'].iloc[-1]:,.2f} (수익: ${valid_df['Portfolio_20'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - MA25 적응형 전략: ${valid_df['Portfolio_25'].iloc[-1]:,.2f} (수익: ${valid_df['Portfolio_25'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - 단순 매수홀드: ${valid_df['Buy_Hold'].iloc[-1]:,.2f} (수익: ${valid_df['Buy_Hold'].iloc[-1] - initial_capital:,.2f})")
    
    print("\n2. 연간 수익률:")
    print(f"   - MA20 적응형 전략: {annual_return_20*100:.2f}%")
    print(f"   - MA25 적응형 전략: {annual_return_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {annual_return_bh*100:.2f}%")
    
    print("\n3. 최대 낙폭 (MDD):")
    print(f"   - MA20 적응형 전략: {max_dd_20*100:.2f}%")
    print(f"   - MA25 적응형 전략: {max_dd_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {max_dd_bh*100:.2f}%")
    
    print("\n4. 샤프 비율 (Sharpe Ratio):")
    print(f"   - MA20 적응형 전략: {sharpe_20:.3f}")
    print(f"   - MA25 적응형 전략: {sharpe_25:.3f}")
    print(f"   - 단순 매수홀드: {sharpe_bh:.3f}")
    
    # 신호 분석
    signal_changes = (valid_df['Position20'] != valid_df['Position25']).sum()
    print(f"\n5. 신호 차이 발생 횟수: {signal_changes}회 ({signal_changes/len(valid_df)*100:.2f}%)")
    
    # 수익성 차이 분석
    better_days = (valid_df['Strategy20_Return'] > valid_df['Strategy25_Return']).sum()
    worse_days = (valid_df['Strategy20_Return'] < valid_df['Strategy25_Return']).sum()
    print(f"\n6. MA20이 MA25보다 수익이 좋았던 날: {better_days}일 ({better_days/len(valid_df)*100:.2f}%)")
    print(f"   MA20이 MA25보다 수익이 나빴던 날: {worse_days}일 ({worse_days/len(valid_df)*100:.2f}%)")
    
    # 거래 횟수 계산
    trades_20 = (valid_df['Position20'] != valid_df['Position20'].shift(1)).sum()
    trades_25 = (valid_df['Position25'] != valid_df['Position25'].shift(1)).sum()
    print(f"\n7. 거래 횟수:")
    print(f"   - MA20 적응형 전략: {trades_20}회 (연평균: {trades_20/(days/365):.1f}회)")
    print(f"   - MA25 적응형 전략: {trades_25}회 (연평균: {trades_25/(days/365):.1f}회)")
    
    print("\n===== 결론 =====")
    if valid_df['Portfolio_20'].iloc[-1] > valid_df['Portfolio_25'].iloc[-1]:
        winner = "MA20 적응형"
        margin = (valid_df['Portfolio_20'].iloc[-1] / valid_df['Portfolio_25'].iloc[-1] - 1) * 100
    else:
        winner = "MA25 적응형"
        margin = (valid_df['Portfolio_25'].iloc[-1] / valid_df['Portfolio_20'].iloc[-1] - 1) * 100
    
    print(f"테스트 기간 동안 {winner} 전략이 {margin:.2f}% 더 높은 수익을 냈습니다.")
    
    if sharpe_20 > sharpe_25:
        print(f"위험 조정 수익률(샤프 비율)은 MA20 적응형 전략이 더 높습니다 ({sharpe_20:.3f} vs {sharpe_25:.3f}).")
    else:
        print(f"위험 조정 수익률(샤프 비율)은 MA25 적응형 전략이 더 높습니다 ({sharpe_25:.3f} vs {sharpe_20:.3f}).")
    
    if trades_20 > trades_25:
        print(f"MA20 적응형 전략은 거래가 더 빈번하여 ({trades_20}회 vs {trades_25}회) 거래 비용이 더 클 수 있습니다.")
    else:
        print(f"MA25 적응형 전략은 거래가 더 빈번하여 ({trades_25}회 vs {trades_20}회) 거래 비용이 더 클 수 있습니다.")
    
    try:
        # 결과 시각화
        plt.figure(figsize=(14, 7))
        plt.plot(valid_df.index, valid_df['Portfolio_20'], label='MA20 Adaptive Strategy')
        plt.plot(valid_df.index, valid_df['Portfolio_25'], label='MA25 Adaptive Strategy')
        plt.plot(valid_df.index, valid_df['Buy_Hold'], label='Buy & Hold')
        plt.title('Adaptive Target Strategy (5% Target Return)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True)
        plt.savefig('backtest_adaptive_target_results.png')
        print("\n결과 그래프가 'backtest_adaptive_target_results.png' 파일로 저장되었습니다.")
    except Exception as e:
        print(f"\n그래프 생성에 실패했습니다: {e}")
    
if __name__ == "__main__":
    backtest_adaptive_target_strategies() 