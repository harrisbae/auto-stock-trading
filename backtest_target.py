import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def backtest_target_strategies():
    """
    MA20과 MA25 기준 5% 목표가 전략을 백테스팅하여 성과를 비교합니다.
    
    두 전략 모두 이동평균선을 기준으로 5% 상하방 밴드를 설정하고:
    - 가격이 하단밴드(-5%) 도달 시 매수
    - 가격이 상단밴드(+5%) 도달 시 매도
    - 그 외에는 포지션 유지
    """
    # 데이터 가져오기 (3년치 데이터로 충분한 백테스팅)
    ticker = 'SPY'
    df = yf.download(ticker, period='3y', interval='1d')
    print(f'데이터 행 수: {len(df)}')
    
    # 멀티인덱스 처리
    df = df.droplevel('Ticker', axis=1)
    
    # 초기 자본금
    initial_capital = 10000
    
    # MA20 기반 지표
    df['MA20'] = df['Close'].rolling(window=20).mean()
    # 5% 밴드 계산 (상단: MA * 1.05, 하단: MA * 0.95)
    df['UpperBand20'] = df['MA20'] * 1.05
    df['LowerBand20'] = df['MA20'] * 0.95
    
    # MA25 기반 지표
    df['MA25'] = df['Close'].rolling(window=25).mean()
    # 5% 밴드 계산 (상단: MA * 1.05, 하단: MA * 0.95)
    df['UpperBand25'] = df['MA25'] * 1.05
    df['LowerBand25'] = df['MA25'] * 0.95
    
    # 유효한 데이터만 사용
    valid_df = df.dropna(subset=['MA20', 'MA25']).copy()
    
    # 신호 생성
    # 초기 포지션은 중립(0)으로 시작
    valid_df['Position20'] = 0
    valid_df['Position25'] = 0
    
    # 밴드 기반 매매 신호 생성 (이전 포지션을 기준으로 상태 전이)
    for i in range(1, len(valid_df)):
        # MA20 전략 신호
        prev_pos20 = valid_df['Position20'].iloc[i-1]
        price = valid_df['Close'].iloc[i]
        upper20 = valid_df['UpperBand20'].iloc[i]
        lower20 = valid_df['LowerBand20'].iloc[i]
        ma20 = valid_df['MA20'].iloc[i]
        
        # 이전 포지션이 중립(0)인 경우
        if prev_pos20 == 0:
            if price <= lower20:  # 하단밴드 도달 시 매수
                valid_df.loc[valid_df.index[i], 'Position20'] = 1
            elif price >= upper20:  # 상단밴드 도달 시 매도
                valid_df.loc[valid_df.index[i], 'Position20'] = -1
            else:  # 그 외에는 현재 포지션 유지
                valid_df.loc[valid_df.index[i], 'Position20'] = 0
        # 이전 포지션이 롱(1)인 경우
        elif prev_pos20 == 1:
            if price >= ma20:  # 이동평균선 이상 도달 시 청산 (이익실현)
                valid_df.loc[valid_df.index[i], 'Position20'] = 0
            else:  # 그 외에는 현재 포지션 유지
                valid_df.loc[valid_df.index[i], 'Position20'] = 1
        # 이전 포지션이 숏(-1)인 경우
        elif prev_pos20 == -1:
            if price <= ma20:  # 이동평균선 이하 도달 시 청산 (이익실현)
                valid_df.loc[valid_df.index[i], 'Position20'] = 0
            else:  # 그 외에는 현재 포지션 유지
                valid_df.loc[valid_df.index[i], 'Position20'] = -1
        
        # MA25 전략 신호 (MA20과 동일한 로직)
        prev_pos25 = valid_df['Position25'].iloc[i-1]
        upper25 = valid_df['UpperBand25'].iloc[i]
        lower25 = valid_df['LowerBand25'].iloc[i]
        ma25 = valid_df['MA25'].iloc[i]
        
        # 이전 포지션이 중립(0)인 경우
        if prev_pos25 == 0:
            if price <= lower25:  # 하단밴드 도달 시 매수
                valid_df.loc[valid_df.index[i], 'Position25'] = 1
            elif price >= upper25:  # 상단밴드 도달 시 매도
                valid_df.loc[valid_df.index[i], 'Position25'] = -1
            else:  # 그 외에는 현재 포지션 유지
                valid_df.loc[valid_df.index[i], 'Position25'] = 0
        # 이전 포지션이 롱(1)인 경우
        elif prev_pos25 == 1:
            if price >= ma25:  # 이동평균선 이상 도달 시 청산 (이익실현)
                valid_df.loc[valid_df.index[i], 'Position25'] = 0
            else:  # 그 외에는 현재 포지션 유지
                valid_df.loc[valid_df.index[i], 'Position25'] = 1
        # 이전 포지션이 숏(-1)인 경우
        elif prev_pos25 == -1:
            if price <= ma25:  # 이동평균선 이하 도달 시 청산 (이익실현)
                valid_df.loc[valid_df.index[i], 'Position25'] = 0
            else:  # 그 외에는 현재 포지션 유지
                valid_df.loc[valid_df.index[i], 'Position25'] = -1
    
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
    print("\n===== 목표가 전략 백테스팅 결과 =====")
    print(f"테스트 기간: {valid_df.index[0].strftime('%Y-%m-%d')} ~ {valid_df.index[-1].strftime('%Y-%m-%d')} ({days}일)")
    print(f"초기 자본금: ${initial_capital:,.2f}")
    
    print("\n1. 최종 포트폴리오 가치:")
    print(f"   - MA20 5% 전략: ${valid_df['Portfolio_20'].iloc[-1]:,.2f} (수익: ${valid_df['Portfolio_20'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - MA25 5% 전략: ${valid_df['Portfolio_25'].iloc[-1]:,.2f} (수익: ${valid_df['Portfolio_25'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - 단순 매수홀드: ${valid_df['Buy_Hold'].iloc[-1]:,.2f} (수익: ${valid_df['Buy_Hold'].iloc[-1] - initial_capital:,.2f})")
    
    print("\n2. 연간 수익률:")
    print(f"   - MA20 5% 전략: {annual_return_20*100:.2f}%")
    print(f"   - MA25 5% 전략: {annual_return_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {annual_return_bh*100:.2f}%")
    
    print("\n3. 최대 낙폭 (MDD):")
    print(f"   - MA20 5% 전략: {max_dd_20*100:.2f}%")
    print(f"   - MA25 5% 전략: {max_dd_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {max_dd_bh*100:.2f}%")
    
    print("\n4. 샤프 비율 (Sharpe Ratio):")
    print(f"   - MA20 5% 전략: {sharpe_20:.3f}")
    print(f"   - MA25 5% 전략: {sharpe_25:.3f}")
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
    print(f"   - MA20 5% 전략: {trades_20}회 (연평균: {trades_20/(days/365):.1f}회)")
    print(f"   - MA25 5% 전략: {trades_25}회 (연평균: {trades_25/(days/365):.1f}회)")
    
    print("\n===== 결론 =====")
    if valid_df['Portfolio_20'].iloc[-1] > valid_df['Portfolio_25'].iloc[-1]:
        winner = "MA20 5%"
        margin = (valid_df['Portfolio_20'].iloc[-1] / valid_df['Portfolio_25'].iloc[-1] - 1) * 100
    else:
        winner = "MA25 5%"
        margin = (valid_df['Portfolio_25'].iloc[-1] / valid_df['Portfolio_20'].iloc[-1] - 1) * 100
    
    print(f"테스트 기간 동안 {winner} 전략이 {margin:.2f}% 더 높은 수익을 냈습니다.")
    
    if sharpe_20 > sharpe_25:
        print(f"위험 조정 수익률(샤프 비율)은 MA20 5% 전략이 더 높습니다 ({sharpe_20:.3f} vs {sharpe_25:.3f}).")
    else:
        print(f"위험 조정 수익률(샤프 비율)은 MA25 5% 전략이 더 높습니다 ({sharpe_25:.3f} vs {sharpe_20:.3f}).")
    
    if trades_20 > trades_25:
        print(f"MA20 5% 전략은 거래가 더 빈번하여 ({trades_20}회 vs {trades_25}회) 거래 비용이 더 클 수 있습니다.")
    else:
        print(f"MA25 5% 전략은 거래가 더 빈번하여 ({trades_25}회 vs {trades_20}회) 거래 비용이 더 클 수 있습니다.")
    
    try:
        # 결과 시각화
        plt.figure(figsize=(14, 7))
        plt.plot(valid_df.index, valid_df['Portfolio_20'], label='MA20 5% Strategy')
        plt.plot(valid_df.index, valid_df['Portfolio_25'], label='MA25 5% Strategy')
        plt.plot(valid_df.index, valid_df['Buy_Hold'], label='Buy & Hold')
        plt.title('MA20 5% vs MA25 5% vs Buy & Hold Strategy Comparison')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True)
        plt.savefig('backtest_target_results.png')
        print("\n결과 그래프가 'backtest_target_results.png' 파일로 저장되었습니다.")
    except Exception as e:
        print(f"\n그래프 생성에 실패했습니다: {e}")
    
if __name__ == "__main__":
    backtest_target_strategies() 