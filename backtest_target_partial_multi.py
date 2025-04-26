import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def backtest_partial_trading_strategies():
    """
    부분 매수/매도 전략을 5%와 10%, 20% 목표 수익률로 백테스팅합니다.
    
    - 매수/매도 신호: 볼린저 밴드 기반
    - 매수/매도 시 각각 20%씩 부분 매매
    - 목표 수익률 도달 시 20% 매도
    - 현재가는 평균 매수가로 재설정
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
    
    # 볼린저 밴드 계산
    # 기본 파라미터: MA25, 표준편차 2
    df['MA25'] = df['Close'].rolling(window=25).mean()
    df['STD'] = df['Close'].rolling(window=25).std()
    df['UpperBand'] = df['MA25'] + (2 * df['STD'])
    df['LowerBand'] = df['MA25'] - (2 * df['STD'])
    
    # 기존 MA20 유지 (비교 목적)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    # 유효한 데이터만 사용
    valid_df = df.dropna().copy()
    
    # 계산 편의를 위한 추가 컬럼
    valid_df['Date'] = valid_df.index
    
    # 볼린저 밴드 매수/매도 신호 계산
    # 볼린저 밴드 매수 신호: 종가가 하단 밴드 아래로 내려갈 때
    valid_df['BB_Buy_Signal'] = (valid_df['Close'] < valid_df['LowerBand']).astype(int)
    
    # 볼린저 밴드 매도 신호: 종가가 상단 밴드 위로 올라갈 때
    valid_df['BB_Sell_Signal'] = (valid_df['Close'] > valid_df['UpperBand']).astype(int)
    
    # 전략별 변수 초기화
    partial_ratio = 0.2  # 부분 매매 비율 20%
    target_gains = [0.05, 0.10, 0.20]  # 목표 수익률 5%, 10%, 20%
    
    # 포트폴리오 초기화
    class Portfolio:
        def __init__(self, initial_capital, target_gain):
            self.cash = initial_capital
            self.stock_units = 0
            self.avg_price = 0
            self.portfolio_value = initial_capital
            self.target_price = 0
            self.target_gain = target_gain
            self.positions = []  # 날짜, 가격, 거래유형 기록
            self.daily_values = []  # 날짜별 포트폴리오 가치 기록
        
        def buy(self, date, price, ratio=1.0):
            if self.cash <= 0:
                return
            
            amount = self.cash * ratio
            new_units = amount / price
            
            # 평균 매수가 계산
            if self.stock_units + new_units > 0:
                self.avg_price = (self.stock_units * self.avg_price + new_units * price) / (self.stock_units + new_units)
            else:
                self.avg_price = price  # 첫 매수 시 현재가격을 평균가로 설정
            
            self.stock_units += new_units
            self.cash -= amount
            
            # 목표가 설정 (평균 매수가 기준 목표 수익률 상승 목표)
            self.target_price = self.avg_price * (1 + self.target_gain)
            
            # 거래 기록
            self.positions.append({
                'date': date,
                'price': price,
                'type': 'buy',
                'ratio': ratio,
                'units': new_units,
                'cash': self.cash,
                'stock_units': self.stock_units,
                'avg_price': self.avg_price,
                'target_price': self.target_price
            })
        
        def sell(self, date, price, ratio=1.0):
            if self.stock_units <= 0:
                return
            
            units_to_sell = self.stock_units * ratio
            amount = units_to_sell * price
            
            self.stock_units -= units_to_sell
            self.cash += amount
            
            # 목표가 갱신 (남은 주식이 있는 경우)
            if self.stock_units > 0:
                # 매도 후에도 평균매수가와 목표가는 유지
                self.target_price = self.avg_price * (1 + self.target_gain)
            else:
                self.avg_price = 0
                self.target_price = 0
            
            # 거래 기록
            self.positions.append({
                'date': date,
                'price': price,
                'type': 'sell',
                'ratio': ratio,
                'units': units_to_sell,
                'cash': self.cash,
                'stock_units': self.stock_units,
                'avg_price': self.avg_price,
                'target_price': self.target_price
            })
        
        def update_value(self, date, price):
            self.portfolio_value = self.cash + self.stock_units * price
            self.daily_values.append({
                'date': date,
                'price': price,
                'cash': self.cash,
                'stock_units': self.stock_units,
                'portfolio_value': self.portfolio_value
            })
    
    # 포트폴리오 생성
    portfolios = {}
    for target_gain in target_gains:
        portfolios[f'BB_Buy_{int(target_gain*100)}'] = Portfolio(initial_capital, target_gain)
        portfolios[f'BB_Sell_{int(target_gain*100)}'] = Portfolio(initial_capital, target_gain)
    
    # 단순 매수홀드 포트폴리오
    portfolio_bh = Portfolio(initial_capital, 0)
    
    # 단순 매수홀드 전략 - 초기에 전액 투자
    portfolio_bh.buy(valid_df.index[0], valid_df['Close'].iloc[0])
    
    # 시뮬레이션 실행
    for i in range(1, len(valid_df)):
        date = valid_df.index[i]
        price = valid_df['Close'].iloc[i]
        bb_buy_signal = valid_df['BB_Buy_Signal'].iloc[i]
        bb_sell_signal = valid_df['BB_Sell_Signal'].iloc[i]
        
        for target_gain in target_gains:
            # 볼린저 밴드 매수 신호 전략
            portfolio_bb_buy = portfolios[f'BB_Buy_{int(target_gain*100)}']
            
            # 1. 매수 신호: 볼린저 밴드 하단 돌파
            if bb_buy_signal == 1:
                portfolio_bb_buy.buy(date, price, partial_ratio)
            
            # 2. 매도 신호: 목표 수익률 도달 또는 볼린저 밴드 상단 돌파
            elif (portfolio_bb_buy.target_price > 0 and price >= portfolio_bb_buy.target_price) or bb_sell_signal == 1:
                portfolio_bb_buy.sell(date, price, partial_ratio)
            
            # 볼린저 밴드 매도 신호 전략
            portfolio_bb_sell = portfolios[f'BB_Sell_{int(target_gain*100)}']
            
            # 1. 매수 신호: 볼린저 밴드 하단 돌파
            if bb_buy_signal == 1:
                portfolio_bb_sell.buy(date, price, partial_ratio)
            
            # 2. 매도 신호: 목표 수익률 도달 또는 볼린저 밴드 상단 돌파
            elif (portfolio_bb_sell.target_price > 0 and price >= portfolio_bb_sell.target_price) or bb_sell_signal == 1:
                portfolio_bb_sell.sell(date, price, partial_ratio)
            
            # 포트폴리오 가치 업데이트
            portfolio_bb_buy.update_value(date, price)
            portfolio_bb_sell.update_value(date, price)
        
        # 매수홀드 업데이트
        portfolio_bh.update_value(date, price)
    
    # 결과 분석을 위한 데이터프레임 생성
    portfolio_dfs = {}
    for key, portfolio in portfolios.items():
        portfolio_dfs[key] = pd.DataFrame(portfolio.daily_values)
    
    portfolio_bh_df = pd.DataFrame(portfolio_bh.daily_values)
    
    # 일별 수익률 계산
    for key, df in portfolio_dfs.items():
        df['Return'] = df['portfolio_value'].pct_change()
        df.loc[df.index[0], 'Return'] = 0
        df['Cum_Return'] = (1 + df['Return']).cumprod()
    
    portfolio_bh_df['Return'] = portfolio_bh_df['portfolio_value'].pct_change()
    portfolio_bh_df.loc[portfolio_bh_df.index[0], 'Return'] = 0
    portfolio_bh_df['Cum_Return'] = (1 + portfolio_bh_df['Return']).cumprod()
    
    # 최대 낙폭 (Maximum Drawdown) 계산
    def calculate_drawdown(cum_returns):
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns / rolling_max) - 1
        return drawdown.min()
    
    drawdowns = {}
    annual_returns = {}
    sharpe_ratios = {}
    trade_counts = {}
    
    # 테스트 기간 계산
    days = (valid_df.index[-1] - valid_df.index[0]).days
    
    # 각 포트폴리오의 성과 지표 계산
    for key, df in portfolio_dfs.items():
        drawdowns[key] = calculate_drawdown(df['Cum_Return'])
        annual_returns[key] = (df['Cum_Return'].iloc[-1] ** (365 / days)) - 1
        
        # 샤프 비율 계산
        risk_free_rate = 0.03  # 가정: 연간 3%
        daily_rf = (1 + risk_free_rate) ** (1/365) - 1
        sharpe_ratios[key] = (df['Return'].mean() - daily_rf) / df['Return'].std() * np.sqrt(252)
        
        # 거래 횟수 계산
        trade_counts[key] = len(portfolios[key].positions)
    
    # 매수홀드 성과 지표
    drawdowns['Buy_Hold'] = calculate_drawdown(portfolio_bh_df['Cum_Return'])
    annual_returns['Buy_Hold'] = (portfolio_bh_df['Cum_Return'].iloc[-1] ** (365 / days)) - 1
    
    # 샤프 비율 계산
    risk_free_rate = 0.03  # 가정: 연간 3%
    daily_rf = (1 + risk_free_rate) ** (1/365) - 1
    sharpe_ratios['Buy_Hold'] = (portfolio_bh_df['Return'].mean() - daily_rf) / portfolio_bh_df['Return'].std() * np.sqrt(252)
    
    # 결과 출력
    print("\n===== 볼린저 밴드 기반 부분 매수/매도 전략 백테스팅 결과 =====")
    print(f"테스트 기간: {valid_df.index[0].strftime('%Y-%m-%d')} ~ {valid_df.index[-1].strftime('%Y-%m-%d')} ({days}일)")
    print(f"초기 자본금: ${initial_capital:,.2f}")
    print(f"부분 매수/매도 비율: {partial_ratio*100:.1f}%")
    print(f"볼린저 밴드 설정: MA25, 표준편차 2")
    
    # 테이블 형식으로 결과 출력
    for target_gain in target_gains:
        print(f"\n=== 목표 수익률 {target_gain*100:.0f}% ===")
        print("\n1. 최종 포트폴리오 가치:")
        key_buy = f'BB_Buy_{int(target_gain*100)}'
        key_sell = f'BB_Sell_{int(target_gain*100)}'
        print(f"   - 볼린저 밴드 매수 전략: ${portfolio_dfs[key_buy]['portfolio_value'].iloc[-1]:,.2f} (수익: ${portfolio_dfs[key_buy]['portfolio_value'].iloc[-1] - initial_capital:,.2f})")
        print(f"   - 볼린저 밴드 매도 전략: ${portfolio_dfs[key_sell]['portfolio_value'].iloc[-1]:,.2f} (수익: ${portfolio_dfs[key_sell]['portfolio_value'].iloc[-1] - initial_capital:,.2f})")
    
    print(f"\n단순 매수홀드: ${portfolio_bh_df['portfolio_value'].iloc[-1]:,.2f} (수익: ${portfolio_bh_df['portfolio_value'].iloc[-1] - initial_capital:,.2f})")
    
    print("\n2. 연간 수익률:")
    for target_gain in target_gains:
        key_buy = f'BB_Buy_{int(target_gain*100)}'
        key_sell = f'BB_Sell_{int(target_gain*100)}'
        print(f"   - 볼린저 매수 {int(target_gain*100)}% 전략: {annual_returns[key_buy]*100:.2f}%")
        print(f"   - 볼린저 매도 {int(target_gain*100)}% 전략: {annual_returns[key_sell]*100:.2f}%")
    print(f"   - 단순 매수홀드: {annual_returns['Buy_Hold']*100:.2f}%")
    
    print("\n3. 최대 낙폭 (MDD):")
    for target_gain in target_gains:
        key_buy = f'BB_Buy_{int(target_gain*100)}'
        key_sell = f'BB_Sell_{int(target_gain*100)}'
        print(f"   - 볼린저 매수 {int(target_gain*100)}% 전략: {drawdowns[key_buy]*100:.2f}%")
        print(f"   - 볼린저 매도 {int(target_gain*100)}% 전략: {drawdowns[key_sell]*100:.2f}%")
    print(f"   - 단순 매수홀드: {drawdowns['Buy_Hold']*100:.2f}%")
    
    print("\n4. 샤프 비율 (Sharpe Ratio):")
    for target_gain in target_gains:
        key_buy = f'BB_Buy_{int(target_gain*100)}'
        key_sell = f'BB_Sell_{int(target_gain*100)}'
        print(f"   - 볼린저 매수 {int(target_gain*100)}% 전략: {sharpe_ratios[key_buy]:.3f}")
        print(f"   - 볼린저 매도 {int(target_gain*100)}% 전략: {sharpe_ratios[key_sell]:.3f}")
    print(f"   - 단순 매수홀드: {sharpe_ratios['Buy_Hold']:.3f}")
    
    print("\n5. 거래 횟수:")
    for target_gain in target_gains:
        key_buy = f'BB_Buy_{int(target_gain*100)}'
        key_sell = f'BB_Sell_{int(target_gain*100)}'
        print(f"   - 볼린저 매수 {int(target_gain*100)}% 전략: {trade_counts[key_buy]}회 (연평균: {trade_counts[key_buy]/(days/365):.1f}회)")
        print(f"   - 볼린저 매도 {int(target_gain*100)}% 전략: {trade_counts[key_sell]}회 (연평균: {trade_counts[key_sell]/(days/365):.1f}회)")
    
    # 최종 포지션 상태
    print("\n6. 최종 포지션 상태:")
    for target_gain in target_gains:
        key_buy = f'BB_Buy_{int(target_gain*100)}'
        key_sell = f'BB_Sell_{int(target_gain*100)}'
        print(f"   - 볼린저 매수 {int(target_gain*100)}% 전략: 현금 ${portfolios[key_buy].cash:.2f}, 주식 {portfolios[key_buy].stock_units:.4f}주, 평균가 ${portfolios[key_buy].avg_price:.2f}")
        print(f"   - 볼린저 매도 {int(target_gain*100)}% 전략: 현금 ${portfolios[key_sell].cash:.2f}, 주식 {portfolios[key_sell].stock_units:.4f}주, 평균가 ${portfolios[key_sell].avg_price:.2f}")
    
    # 결과 시각화
    plt.figure(figsize=(14, 15))
    
    # 목표 수익률 5% 그래프
    plt.subplot(3, 1, 1)
    plt.plot(portfolio_dfs['BB_Buy_5']['date'], portfolio_dfs['BB_Buy_5']['portfolio_value'], label='BB Buy 5% Strategy')
    plt.plot(portfolio_dfs['BB_Sell_5']['date'], portfolio_dfs['BB_Sell_5']['portfolio_value'], label='BB Sell 5% Strategy')
    plt.plot(portfolio_bh_df['date'], portfolio_bh_df['portfolio_value'], label='Buy & Hold')
    plt.title('Bollinger Bands Strategy - 5% Target Gain')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.legend()
    plt.grid(True)
    
    # 목표 수익률 10% 그래프
    plt.subplot(3, 1, 2)
    plt.plot(portfolio_dfs['BB_Buy_10']['date'], portfolio_dfs['BB_Buy_10']['portfolio_value'], label='BB Buy 10% Strategy')
    plt.plot(portfolio_dfs['BB_Sell_10']['date'], portfolio_dfs['BB_Sell_10']['portfolio_value'], label='BB Sell 10% Strategy')
    plt.plot(portfolio_bh_df['date'], portfolio_bh_df['portfolio_value'], label='Buy & Hold')
    plt.title('Bollinger Bands Strategy - 10% Target Gain')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.legend()
    plt.grid(True)
    
    # 목표 수익률 20% 그래프
    plt.subplot(3, 1, 3)
    plt.plot(portfolio_dfs['BB_Buy_20']['date'], portfolio_dfs['BB_Buy_20']['portfolio_value'], label='BB Buy 20% Strategy')
    plt.plot(portfolio_dfs['BB_Sell_20']['date'], portfolio_dfs['BB_Sell_20']['portfolio_value'], label='BB Sell 20% Strategy')
    plt.plot(portfolio_bh_df['date'], portfolio_bh_df['portfolio_value'], label='Buy & Hold')
    plt.title('Bollinger Bands Strategy - 20% Target Gain')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # 파일명에 현재 날짜 추가
    current_date = datetime.now().strftime('%Y%m%d')
    filename = f'backtest_bollinger_bands_multi_target_{current_date}.png'
    
    plt.savefig(filename)
    print(f"\n결과 그래프가 '{filename}' 파일로 저장되었습니다.")
    
    # 결론 도출
    print("\n===== 결론 =====")
    
    # 전략별 최고 성과
    best_strategy = max(portfolios.keys(), key=lambda k: portfolio_dfs[k]['portfolio_value'].iloc[-1])
    print(f"최고 성과 전략: {best_strategy}, 최종 가치: ${portfolio_dfs[best_strategy]['portfolio_value'].iloc[-1]:,.2f}")
    
    # 매수홀드와 비교
    if portfolio_dfs[best_strategy]['portfolio_value'].iloc[-1] > portfolio_bh_df['portfolio_value'].iloc[-1]:
        print(f"최고 성과 전략({best_strategy})이 매수홀드보다 {(portfolio_dfs[best_strategy]['portfolio_value'].iloc[-1] / portfolio_bh_df['portfolio_value'].iloc[-1] - 1) * 100:.2f}% 더 높은 수익을 냈습니다.")
    else:
        print(f"매수홀드 전략이 최고 성과 전략({best_strategy})보다 {(portfolio_bh_df['portfolio_value'].iloc[-1] / portfolio_dfs[best_strategy]['portfolio_value'].iloc[-1] - 1) * 100:.2f}% 더 높은 수익을 냈습니다.")
    
    # 위험 관리 분석
    best_drawdown = min(drawdowns.items(), key=lambda x: abs(x[1]))[0]
    print(f"최소 낙폭은 {best_drawdown} 전략에서 {drawdowns[best_drawdown]*100:.2f}%로 기록되었습니다.")
    
    # 샤프 비율 분석
    best_sharpe = max(sharpe_ratios.items(), key=lambda x: x[1])[0]
    print(f"최고 샤프 비율은 {best_sharpe} 전략에서 {sharpe_ratios[best_sharpe]:.3f}로 기록되었습니다.")

if __name__ == "__main__":
    backtest_partial_trading_strategies() 