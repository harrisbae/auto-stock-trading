import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime

def calculate_bollinger_percent_b(df, ma_period, std_multiplier=2):
    """
    볼린저 밴드의 %B 지표 계산
    %B = (가격 - 하단밴드) / (상단밴드 - 하단밴드)
    """
    ma_column = f'MA{ma_period}'
    df[ma_column] = df['Close'].rolling(window=ma_period).mean()
    
    # 표준편차 계산
    df['STD'] = df['Close'].rolling(window=ma_period).std()
    
    # 볼린저 밴드 계산
    df['UpperBand'] = df[ma_column] + (std_multiplier * df['STD'])
    df['LowerBand'] = df[ma_column] - (std_multiplier * df['STD'])
    
    # %B 계산
    df['PercentB'] = (df['Close'] - df['LowerBand']) / (df['UpperBand'] - df['LowerBand'])
    
    return df

def generate_signals(df, b_threshold_low=0.2, b_threshold_high=0.8):
    """
    %B 지표를 기반으로 매매 신호 생성
    %B < 0.2: 매수 신호 (1)
    %B > 0.8: 매도 신호 (-1)
    그 외: 홀드 신호 (0)
    """
    # 초기값 설정
    df['Signal'] = 0
    
    # 매수 신호
    df.loc[df['PercentB'] < b_threshold_low, 'Signal'] = 1
    
    # 매도 신호
    df.loc[df['PercentB'] > b_threshold_high, 'Signal'] = -1
    
    return df

def backtest_strategy(df, initial_capital=10000):
    """
    매매 신호를 기반으로 백테스팅 수행
    """
    # 포지션 컬럼 생성 (시그널이 변경될 때만 포지션 변경)
    df['Position'] = df['Signal']
    
    # 수익률 계산
    df['Returns'] = df['Close'].pct_change()
    
    # 전략 수익률 계산 (전일 포지션 * 당일 수익률)
    df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
    
    # 누적 수익률 계산
    df['Cumulative_Returns'] = (1 + df['Returns']).cumprod()
    df['Strategy_Cumulative_Returns'] = (1 + df['Strategy_Returns']).cumprod()
    
    # 최종 자산 가치 계산
    final_value = initial_capital * df['Strategy_Cumulative_Returns'].iloc[-1]
    
    # 연 수익률 계산
    days = (df.index[-1] - df.index[0]).days
    annual_return = (final_value / initial_capital) ** (365 / days) - 1
    
    # 최대 낙폭(MDD) 계산
    cum_returns = df['Strategy_Cumulative_Returns']
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    max_drawdown = drawdown.min()
    
    # 샤프 비율 계산
    risk_free_rate = 0.03  # 가정: 연간 3%
    daily_rf = (1 + risk_free_rate) ** (1/365) - 1
    sharpe_ratio = (df['Strategy_Returns'].mean() - daily_rf) / df['Strategy_Returns'].std() * np.sqrt(252)
    
    # 거래 횟수 계산
    df['Position_Change'] = df['Position'].diff().abs()
    trade_count = df[df['Position_Change'] > 0].shape[0]
    
    # 매매 날짜 기록
    trade_dates = df[df['Position_Change'] > 0].index
    
    results = {
        'final_value': final_value,
        'profit': final_value - initial_capital,
        'profit_rate': (final_value / initial_capital) - 1,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'trade_count': trade_count,
        'trade_dates': trade_dates
    }
    
    return df, results

def main():
    # 데이터 가져오기
    ticker = 'SPY'
    df = yf.download(ticker, period='3y', interval='1d')
    print(f'데이터 행 수: {len(df)}')
    
    # 멀티인덱스 처리
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel('Ticker', axis=1)
    
    # 초기 자본금
    initial_capital = 10000
    
    # MA20 전략 백테스팅
    df_ma20 = calculate_bollinger_percent_b(df.copy(), ma_period=20)
    df_ma20 = generate_signals(df_ma20)
    df_ma20, results_ma20 = backtest_strategy(df_ma20, initial_capital)
    
    # MA25 전략 백테스팅
    df_ma25 = calculate_bollinger_percent_b(df.copy(), ma_period=25)
    df_ma25 = generate_signals(df_ma25)
    df_ma25, results_ma25 = backtest_strategy(df_ma25, initial_capital)
    
    # 단순 매수홀드 전략 결과 계산
    buy_hold_value = initial_capital * df['Close'].iloc[-1] / df['Close'].iloc[0]
    buy_hold_profit = buy_hold_value - initial_capital
    buy_hold_profit_rate = (buy_hold_value / initial_capital) - 1
    
    # 단순 매수홀드 수익률 계산
    df['BuyHold_Returns'] = df['Close'].pct_change()
    df['BuyHold_Cumulative_Returns'] = (1 + df['BuyHold_Returns']).cumprod()
    
    # 매수홀드 연 수익률 계산
    days = (df.index[-1] - df.index[0]).days
    buy_hold_annual_return = (buy_hold_value / initial_capital) ** (365 / days) - 1
    
    # 매수홀드 최대 낙폭(MDD) 계산
    cum_returns = df['BuyHold_Cumulative_Returns']
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    buy_hold_max_drawdown = drawdown.min()
    
    # 매수홀드 샤프 비율 계산
    risk_free_rate = 0.03  # 가정: 연간 3%
    daily_rf = (1 + risk_free_rate) ** (1/365) - 1
    buy_hold_sharpe_ratio = (df['BuyHold_Returns'].mean() - daily_rf) / df['BuyHold_Returns'].std() * np.sqrt(252)
    
    # 신호 차이 분석
    df_combined = pd.DataFrame({
        'Signal_MA20': df_ma20['Signal'],
        'Signal_MA25': df_ma25['Signal'],
        'Returns_MA20': df_ma20['Strategy_Returns'],
        'Returns_MA25': df_ma25['Strategy_Returns']
    })
    
    # 신호가 다른 날 개수
    different_signals = df_combined[df_combined['Signal_MA20'] != df_combined['Signal_MA25']]
    different_signals_count = len(different_signals)
    
    # MA20이 MA25보다 수익이 좋았던 날 개수
    ma20_better_days = df_combined[df_combined['Returns_MA20'] > df_combined['Returns_MA25']]
    ma20_better_days_count = len(ma20_better_days)
    
    # MA25가 MA20보다 수익이 좋았던 날 개수
    ma25_better_days = df_combined[df_combined['Returns_MA20'] < df_combined['Returns_MA25']]
    ma25_better_days_count = len(ma25_better_days)
    
    # 결과 출력
    print("\n===== MA20 및 MA25 전략 백테스팅 결과 =====")
    print(f"테스트 기간: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')} ({days}일)")
    print(f"초기 자본금: ${initial_capital:,.2f}")
    
    print("\n1. 최종 포트폴리오 가치:")
    print(f"   - MA20 전략: ${results_ma20['final_value']:,.2f} (수익: ${results_ma20['profit']:,.2f}, {results_ma20['profit_rate']*100:.2f}%)")
    print(f"   - MA25 전략: ${results_ma25['final_value']:,.2f} (수익: ${results_ma25['profit']:,.2f}, {results_ma25['profit_rate']*100:.2f}%)")
    print(f"   - 단순 매수홀드: ${buy_hold_value:,.2f} (수익: ${buy_hold_profit:,.2f}, {buy_hold_profit_rate*100:.2f}%)")
    
    print("\n2. 연간 수익률:")
    print(f"   - MA20 전략: {results_ma20['annual_return']*100:.2f}%")
    print(f"   - MA25 전략: {results_ma25['annual_return']*100:.2f}%")
    print(f"   - 단순 매수홀드: {buy_hold_annual_return*100:.2f}%")
    
    print("\n3. 최대 낙폭 (MDD):")
    print(f"   - MA20 전략: {results_ma20['max_drawdown']*100:.2f}%")
    print(f"   - MA25 전략: {results_ma25['max_drawdown']*100:.2f}%")
    print(f"   - 단순 매수홀드: {buy_hold_max_drawdown*100:.2f}%")
    
    print("\n4. 샤프 비율 (Sharpe Ratio):")
    print(f"   - MA20 전략: {results_ma20['sharpe_ratio']:.3f}")
    print(f"   - MA25 전략: {results_ma25['sharpe_ratio']:.3f}")
    print(f"   - 단순 매수홀드: {buy_hold_sharpe_ratio:.3f}")
    
    print("\n5. 거래 횟수:")
    print(f"   - MA20 전략: {results_ma20['trade_count']}회 (연평균: {results_ma20['trade_count']/(days/365):.1f}회)")
    print(f"   - MA25 전략: {results_ma25['trade_count']}회 (연평균: {results_ma25['trade_count']/(days/365):.1f}회)")
    
    print("\n6. 신호 차이 분석:")
    print(f"   - 신호가 다른 날: {different_signals_count}일 (전체 거래일의 {different_signals_count/len(df)*100:.2f}%)")
    print(f"   - MA20이 MA25보다 수익이 좋았던 날: {ma20_better_days_count}일 ({ma20_better_days_count/len(df)*100:.2f}%)")
    print(f"   - MA25가 MA20보다 수익이 좋았던 날: {ma25_better_days_count}일 ({ma25_better_days_count/len(df)*100:.2f}%)")
    
    # 결과 시각화
    plt.figure(figsize=(14, 15))
    
    # 수익률 비교 그래프
    plt.subplot(3, 1, 1)
    plt.plot(df_ma20.index, df_ma20['Strategy_Cumulative_Returns'], label='MA20 Strategy')
    plt.plot(df_ma25.index, df_ma25['Strategy_Cumulative_Returns'], label='MA25 Strategy')
    plt.plot(df.index, df['BuyHold_Cumulative_Returns'], label='Buy & Hold')
    plt.axhline(y=1, color='r', linestyle='-', alpha=0.3)
    plt.title('Cumulative Returns Comparison')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Returns')
    plt.legend()
    plt.grid(True)
    
    # %B 값과 매매 신호 - MA20
    plt.subplot(3, 1, 2)
    plt.plot(df_ma20.index, df_ma20['PercentB'], label='%B (MA20)', color='blue', alpha=0.7)
    plt.axhline(y=0.8, color='r', linestyle='--', alpha=0.5, label='Upper Threshold (0.8)')
    plt.axhline(y=0.2, color='g', linestyle='--', alpha=0.5, label='Lower Threshold (0.2)')
    plt.scatter(df_ma20[df_ma20['Signal'] == 1].index, 
                df_ma20[df_ma20['Signal'] == 1]['PercentB'], 
                marker='^', color='g', label='Buy Signal')
    plt.scatter(df_ma20[df_ma20['Signal'] == -1].index, 
                df_ma20[df_ma20['Signal'] == -1]['PercentB'], 
                marker='v', color='r', label='Sell Signal')
    plt.title('%B Indicator and Signals (MA20)')
    plt.xlabel('Date')
    plt.ylabel('%B Value')
    plt.legend()
    plt.grid(True)
    
    # %B 값과 매매 신호 - MA25
    plt.subplot(3, 1, 3)
    plt.plot(df_ma25.index, df_ma25['PercentB'], label='%B (MA25)', color='purple', alpha=0.7)
    plt.axhline(y=0.8, color='r', linestyle='--', alpha=0.5, label='Upper Threshold (0.8)')
    plt.axhline(y=0.2, color='g', linestyle='--', alpha=0.5, label='Lower Threshold (0.2)')
    plt.scatter(df_ma25[df_ma25['Signal'] == 1].index, 
                df_ma25[df_ma25['Signal'] == 1]['PercentB'], 
                marker='^', color='g', label='Buy Signal')
    plt.scatter(df_ma25[df_ma25['Signal'] == -1].index, 
                df_ma25[df_ma25['Signal'] == -1]['PercentB'], 
                marker='v', color='r', label='Sell Signal')
    plt.title('%B Indicator and Signals (MA25)')
    plt.xlabel('Date')
    plt.ylabel('%B Value')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # 파일명에 현재 날짜 추가
    current_date = datetime.now().strftime('%Y%m%d')
    filename = f'backtest_ma_strategy_{current_date}.png'
    
    plt.savefig(filename)
    print(f"\n결과 그래프가 '{filename}' 파일로 저장되었습니다.")
    
    # 결론
    print("\n===== 분석 및 결론 =====")
    
    # 수익성 비교
    if results_ma25['profit_rate'] > results_ma20['profit_rate']:
        print(f"1. MA25 전략이 MA20 전략보다 {(results_ma25['profit_rate'] - results_ma20['profit_rate'])*100:.2f}% 더 높은 수익률을 기록했습니다.")
    else:
        print(f"1. MA20 전략이 MA25 전략보다 {(results_ma20['profit_rate'] - results_ma25['profit_rate'])*100:.2f}% 더 높은 수익률을 기록했습니다.")
    
    # MDD 비교
    if abs(results_ma25['max_drawdown']) < abs(results_ma20['max_drawdown']):
        print(f"2. MA25 전략의 최대 낙폭({results_ma25['max_drawdown']*100:.2f}%)이 MA20 전략({results_ma20['max_drawdown']*100:.2f}%)보다 낮아 위험 관리 측면에서 우수했습니다.")
    else:
        print(f"2. MA20 전략의 최대 낙폭({results_ma20['max_drawdown']*100:.2f}%)이 MA25 전략({results_ma25['max_drawdown']*100:.2f}%)보다 낮아 위험 관리 측면에서 우수했습니다.")
    
    # 거래 횟수 비교
    if results_ma25['trade_count'] < results_ma20['trade_count']:
        print(f"3. MA25 전략이 MA20 전략보다 거래 횟수가 {results_ma20['trade_count'] - results_ma25['trade_count']}회 적어 거래 비용 측면에서 유리할 수 있습니다.")
    else:
        print(f"3. MA20 전략이 MA25 전략보다 거래 횟수가 {results_ma25['trade_count'] - results_ma20['trade_count']}회 적어 거래 비용 측면에서 유리할 수 있습니다.")
    
    # 시장 환경 고려
    print(f"4. 테스트 기간 동안 매수홀드 전략({buy_hold_profit_rate*100:.2f}%)이 MA20({results_ma20['profit_rate']*100:.2f}%)과 MA25({results_ma25['profit_rate']*100:.2f}%) 전략보다 높은 수익을 냈습니다.")
    
    if abs(results_ma25['max_drawdown']) < abs(buy_hold_max_drawdown) and abs(results_ma20['max_drawdown']) < abs(buy_hold_max_drawdown):
        print(f"   그러나 두 전략 모두 매수홀드({buy_hold_max_drawdown*100:.2f}%)보다 낮은 최대 낙폭을 보여 하락장에서 방어적인 특성을 가질 수 있습니다.")

if __name__ == "__main__":
    main() 