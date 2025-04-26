import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def backtest_strategies():
    """
    MA20과 MA25 기반 전략을 백테스팅하여 성과를 비교합니다.
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
    
    # 유효한 데이터만 사용
    valid_df = df.dropna(subset=['%B20', '%B25']).copy()
    
    # 포지션 설정 (1: 매수, -1: 매도, 0: 현금)
    valid_df['Position20'] = 0
    valid_df['Position25'] = 0
    
    # MA20 전략 포지션
    valid_df.loc[valid_df['Signal20'] == 'Buy', 'Position20'] = 1
    valid_df.loc[valid_df['Signal20'] == 'Sell', 'Position20'] = -1
    
    # MA25 전략 포지션
    valid_df.loc[valid_df['Signal25'] == 'Buy', 'Position25'] = 1
    valid_df.loc[valid_df['Signal25'] == 'Sell', 'Position25'] = -1
    
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
    print("\n===== 백테스팅 결과 =====")
    print(f"테스트 기간: {valid_df.index[0].strftime('%Y-%m-%d')} ~ {valid_df.index[-1].strftime('%Y-%m-%d')} ({days}일)")
    print(f"초기 자본금: ${initial_capital:,.2f}")
    
    print("\n1. 최종 포트폴리오 가치:")
    print(f"   - MA20 전략: ${valid_df['Portfolio_20'].iloc[-1]:,.2f} (수익: ${valid_df['Portfolio_20'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - MA25 전략: ${valid_df['Portfolio_25'].iloc[-1]:,.2f} (수익: ${valid_df['Portfolio_25'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - 단순 매수홀드: ${valid_df['Buy_Hold'].iloc[-1]:,.2f} (수익: ${valid_df['Buy_Hold'].iloc[-1] - initial_capital:,.2f})")
    
    print("\n2. 연간 수익률:")
    print(f"   - MA20 전략: {annual_return_20*100:.2f}%")
    print(f"   - MA25 전략: {annual_return_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {annual_return_bh*100:.2f}%")
    
    print("\n3. 최대 낙폭 (MDD):")
    print(f"   - MA20 전략: {max_dd_20*100:.2f}%")
    print(f"   - MA25 전략: {max_dd_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {max_dd_bh*100:.2f}%")
    
    print("\n4. 샤프 비율 (Sharpe Ratio):")
    print(f"   - MA20 전략: {sharpe_20:.3f}")
    print(f"   - MA25 전략: {sharpe_25:.3f}")
    print(f"   - 단순 매수홀드: {sharpe_bh:.3f}")
    
    # 신호 분석
    signal_changes = (valid_df['Signal20'] != valid_df['Signal25']).sum()
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
    print(f"   - MA20 전략: {trades_20}회 (연평균: {trades_20/(days/365):.1f}회)")
    print(f"   - MA25 전략: {trades_25}회 (연평균: {trades_25/(days/365):.1f}회)")
    
    print("\n===== 결론 =====")
    if valid_df['Portfolio_20'].iloc[-1] > valid_df['Portfolio_25'].iloc[-1]:
        winner = "MA20"
        margin = (valid_df['Portfolio_20'].iloc[-1] / valid_df['Portfolio_25'].iloc[-1] - 1) * 100
    else:
        winner = "MA25"
        margin = (valid_df['Portfolio_25'].iloc[-1] / valid_df['Portfolio_20'].iloc[-1] - 1) * 100
    
    print(f"테스트 기간 동안 {winner} 전략이 {margin:.2f}% 더 높은 수익을 냈습니다.")
    
    if sharpe_20 > sharpe_25:
        print(f"위험 조정 수익률(샤프 비율)은 MA20 전략이 더 높습니다 ({sharpe_20:.3f} vs {sharpe_25:.3f}).")
    else:
        print(f"위험 조정 수익률(샤프 비율)은 MA25 전략이 더 높습니다 ({sharpe_25:.3f} vs {sharpe_20:.3f}).")
    
    if trades_20 > trades_25:
        print(f"MA20 전략은 거래가 더 빈번하여 ({trades_20}회 vs {trades_25}회) 거래 비용이 더 클 수 있습니다.")
    else:
        print(f"MA25 전략은 거래가 더 빈번하여 ({trades_25}회 vs {trades_20}회) 거래 비용이 더 클 수 있습니다.")
    
    try:
        # 결과 시각화 (matplotlib가 설치되어 있는 경우)
        plt.figure(figsize=(14, 7))
        plt.plot(valid_df.index, valid_df['Portfolio_20'], label='MA20 Strategy')
        plt.plot(valid_df.index, valid_df['Portfolio_25'], label='MA25 Strategy')
        plt.plot(valid_df.index, valid_df['Buy_Hold'], label='Buy & Hold')
        plt.title('MA20 vs MA25 vs Buy & Hold Strategy Comparison')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True)
        plt.savefig('backtest_results.png')
        print("\n결과 그래프가 'backtest_results.png' 파일로 저장되었습니다.")
    except:
        print("\n그래프 생성에 실패했습니다. matplotlib가 설치되어 있는지 확인하세요.")
    
if __name__ == "__main__":
    backtest_strategies() 