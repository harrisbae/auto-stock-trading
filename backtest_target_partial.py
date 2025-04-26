import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def backtest_partial_trading_strategies():
    """
    부분 매수/매도 전략을 백테스팅합니다.
    
    - 매수/매도 신호 발생 시 각각 20%씩 매수/매도
    - 목표 수익률 도달 시 20% 매도
    - 현재가는 평균 매수가로 설정
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
    
    # 계산 편의를 위한 추가 컬럼
    valid_df['Date'] = valid_df.index
    
    # 전략별 변수 초기화
    buy_threshold_20 = 0.95  # MA20 아래 5% 지점 매수
    buy_threshold_25 = 0.96  # MA25 아래 4% 지점 매수
    target_gain = 0.05  # 목표 수익률 5%
    partial_ratio = 0.2  # 부분 매수/매도 비율 20%
    
    # 포트폴리오 초기화
    class Portfolio:
        def __init__(self, initial_capital):
            self.cash = initial_capital
            self.stock_units = 0
            self.avg_price = 0
            self.portfolio_value = initial_capital
            self.target_price = 0
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
            
            self.stock_units += new_units
            self.cash -= amount
            
            # 목표가 설정 (평균 매수가 기준 5% 상승 목표)
            self.target_price = self.avg_price * (1 + target_gain)
            
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
                self.target_price = self.avg_price * (1 + target_gain)
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
    portfolio_20 = Portfolio(initial_capital)
    portfolio_25 = Portfolio(initial_capital)
    portfolio_bh = Portfolio(initial_capital)
    
    # 단순 매수홀드 전략 - 초기에 전액 투자
    portfolio_bh.buy(valid_df.index[0], valid_df['Close'].iloc[0])
    
    # 시뮬레이션 실행
    for i in range(1, len(valid_df)):
        date = valid_df.index[i]
        price = valid_df['Close'].iloc[i]
        ma20 = valid_df['MA20'].iloc[i]
        ma25 = valid_df['MA25'].iloc[i]
        
        # MA20 전략
        # 1. 매수 신호: MA20 아래 5% 지점
        if price < ma20 * buy_threshold_20:
            portfolio_20.buy(date, price, partial_ratio)
        
        # 2. 목표가 도달 시 20% 매도
        elif portfolio_20.target_price > 0 and price >= portfolio_20.target_price:
            portfolio_20.sell(date, price, partial_ratio)
        
        # MA25 전략
        # 1. 매수 신호: MA25 아래 4% 지점
        if price < ma25 * buy_threshold_25:
            portfolio_25.buy(date, price, partial_ratio)
        
        # 2. 목표가 도달 시 20% 매도
        elif portfolio_25.target_price > 0 and price >= portfolio_25.target_price:
            portfolio_25.sell(date, price, partial_ratio)
        
        # 포트폴리오 가치 업데이트
        portfolio_20.update_value(date, price)
        portfolio_25.update_value(date, price)
        portfolio_bh.update_value(date, price)
    
    # 결과 분석을 위한 데이터프레임 생성
    portfolio_20_df = pd.DataFrame(portfolio_20.daily_values)
    portfolio_25_df = pd.DataFrame(portfolio_25.daily_values)
    portfolio_bh_df = pd.DataFrame(portfolio_bh.daily_values)
    
    # 일별 수익률 계산
    portfolio_20_df['Return'] = portfolio_20_df['portfolio_value'].pct_change()
    portfolio_25_df['Return'] = portfolio_25_df['portfolio_value'].pct_change()
    portfolio_bh_df['Return'] = portfolio_bh_df['portfolio_value'].pct_change()
    
    # 첫날 수익률은 NaN이므로 0으로 설정
    portfolio_20_df['Return'].iloc[0] = 0
    portfolio_25_df['Return'].iloc[0] = 0
    portfolio_bh_df['Return'].iloc[0] = 0
    
    # 누적 수익률 계산
    portfolio_20_df['Cum_Return'] = (1 + portfolio_20_df['Return']).cumprod()
    portfolio_25_df['Cum_Return'] = (1 + portfolio_25_df['Return']).cumprod()
    portfolio_bh_df['Cum_Return'] = (1 + portfolio_bh_df['Return']).cumprod()
    
    # 최대 낙폭 (Maximum Drawdown) 계산
    def calculate_drawdown(cum_returns):
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns / rolling_max) - 1
        return drawdown.min()
    
    max_dd_20 = calculate_drawdown(portfolio_20_df['Cum_Return'])
    max_dd_25 = calculate_drawdown(portfolio_25_df['Cum_Return'])
    max_dd_bh = calculate_drawdown(portfolio_bh_df['Cum_Return'])
    
    # 연간 수익률 계산
    days = (valid_df.index[-1] - valid_df.index[0]).days
    annual_return_20 = (portfolio_20_df['Cum_Return'].iloc[-1] ** (365 / days)) - 1
    annual_return_25 = (portfolio_25_df['Cum_Return'].iloc[-1] ** (365 / days)) - 1
    annual_return_bh = (portfolio_bh_df['Cum_Return'].iloc[-1] ** (365 / days)) - 1
    
    # 샤프 비율 (Sharpe Ratio) 계산
    risk_free_rate = 0.03  # 가정: 연간 3%
    daily_rf = (1 + risk_free_rate) ** (1/365) - 1
    
    sharpe_20 = (portfolio_20_df['Return'].mean() - daily_rf) / portfolio_20_df['Return'].std() * np.sqrt(252)
    sharpe_25 = (portfolio_25_df['Return'].mean() - daily_rf) / portfolio_25_df['Return'].std() * np.sqrt(252)
    sharpe_bh = (portfolio_bh_df['Return'].mean() - daily_rf) / portfolio_bh_df['Return'].std() * np.sqrt(252)
    
    # 거래 횟수 계산
    trades_20 = len([p for p in portfolio_20.positions])
    trades_25 = len([p for p in portfolio_25.positions])
    
    # 결과 출력
    print("\n===== 부분 매수/매도 전략 백테스팅 결과 =====")
    print(f"테스트 기간: {valid_df.index[0].strftime('%Y-%m-%d')} ~ {valid_df.index[-1].strftime('%Y-%m-%d')} ({days}일)")
    print(f"초기 자본금: ${initial_capital:,.2f}")
    print(f"목표 수익률: {target_gain*100:.1f}%")
    print(f"부분 매수/매도 비율: {partial_ratio*100:.1f}%")
    print(f"MA20 매수 기준: MA20 아래 {(1-buy_threshold_20)*100:.1f}%")
    print(f"MA25 매수 기준: MA25 아래 {(1-buy_threshold_25)*100:.1f}%")
    
    print("\n1. 최종 포트폴리오 가치:")
    print(f"   - MA20 부분 매매 전략: ${portfolio_20_df['portfolio_value'].iloc[-1]:,.2f} (수익: ${portfolio_20_df['portfolio_value'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - MA25 부분 매매 전략: ${portfolio_25_df['portfolio_value'].iloc[-1]:,.2f} (수익: ${portfolio_25_df['portfolio_value'].iloc[-1] - initial_capital:,.2f})")
    print(f"   - 단순 매수홀드: ${portfolio_bh_df['portfolio_value'].iloc[-1]:,.2f} (수익: ${portfolio_bh_df['portfolio_value'].iloc[-1] - initial_capital:,.2f})")
    
    print("\n2. 연간 수익률:")
    print(f"   - MA20 부분 매매 전략: {annual_return_20*100:.2f}%")
    print(f"   - MA25 부분 매매 전략: {annual_return_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {annual_return_bh*100:.2f}%")
    
    print("\n3. 최대 낙폭 (MDD):")
    print(f"   - MA20 부분 매매 전략: {max_dd_20*100:.2f}%")
    print(f"   - MA25 부분 매매 전략: {max_dd_25*100:.2f}%")
    print(f"   - 단순 매수홀드: {max_dd_bh*100:.2f}%")
    
    print("\n4. 샤프 비율 (Sharpe Ratio):")
    print(f"   - MA20 부분 매매 전략: {sharpe_20:.3f}")
    print(f"   - MA25 부분 매매 전략: {sharpe_25:.3f}")
    print(f"   - 단순 매수홀드: {sharpe_bh:.3f}")
    
    print("\n5. 거래 횟수:")
    print(f"   - MA20 부분 매매 전략: {trades_20}회 (연평균: {trades_20/(days/365):.1f}회)")
    print(f"   - MA25 부분 매매 전략: {trades_25}회 (연평균: {trades_25/(days/365):.1f}회)")
    
    # 현재 포지션 상태
    print("\n6. 최종 포지션 상태:")
    print(f"   - MA20 전략: 현금 ${portfolio_20.cash:.2f}, 주식 {portfolio_20.stock_units:.4f}주, 평균가 ${portfolio_20.avg_price:.2f}")
    print(f"   - MA25 전략: 현금 ${portfolio_25.cash:.2f}, 주식 {portfolio_25.stock_units:.4f}주, 평균가 ${portfolio_25.avg_price:.2f}")
    
    print("\n===== 결론 =====")
    if portfolio_20_df['portfolio_value'].iloc[-1] > portfolio_25_df['portfolio_value'].iloc[-1]:
        winner = "MA20 부분 매매"
        margin = (portfolio_20_df['portfolio_value'].iloc[-1] / portfolio_25_df['portfolio_value'].iloc[-1] - 1) * 100
    else:
        winner = "MA25 부분 매매"
        margin = (portfolio_25_df['portfolio_value'].iloc[-1] / portfolio_20_df['portfolio_value'].iloc[-1] - 1) * 100
    
    print(f"테스트 기간 동안 {winner} 전략이 {margin:.2f}% 더 높은 수익을 냈습니다.")
    
    if sharpe_20 > sharpe_25:
        print(f"위험 조정 수익률(샤프 비율)은 MA20 부분 매매 전략이 더 높습니다 ({sharpe_20:.3f} vs {sharpe_25:.3f}).")
    else:
        print(f"위험 조정 수익률(샤프 비율)은 MA25 부분 매매 전략이 더 높습니다 ({sharpe_25:.3f} vs {sharpe_20:.3f}).")
    
    if trades_20 > trades_25:
        print(f"MA20 부분 매매 전략은 거래가 더 빈번하여 ({trades_20}회 vs {trades_25}회) 거래 비용이 더 클 수 있습니다.")
    else:
        print(f"MA25 부분 매매 전략은 거래가 더 빈번하여 ({trades_25}회 vs {trades_20}회) 거래 비용이 더 클 수 있습니다.")
    
    try:
        # 결과 시각화
        plt.figure(figsize=(14, 7))
        plt.plot(portfolio_20_df['date'], portfolio_20_df['portfolio_value'], label='MA20 Partial Strategy')
        plt.plot(portfolio_25_df['date'], portfolio_25_df['portfolio_value'], label='MA25 Partial Strategy')
        plt.plot(portfolio_bh_df['date'], portfolio_bh_df['portfolio_value'], label='Buy & Hold')
        plt.title('Partial Trading Strategy (20% Position Change)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True)
        plt.savefig('backtest_partial_trading_results.png')
        print("\n결과 그래프가 'backtest_partial_trading_results.png' 파일로 저장되었습니다.")
    except Exception as e:
        print(f"\n그래프 생성에 실패했습니다: {e}")
    
if __name__ == "__main__":
    backtest_partial_trading_strategies() 