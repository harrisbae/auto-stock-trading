#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import os
from matplotlib.ticker import FuncFormatter

class BNFBollingerStrategy:
    """
    BNF (Bollinger No False Signal) 전략 구현 클래스
    일반적인 볼린저 밴드 전략의 단점인 조기 매매 신호를 개선한 전략입니다.
    """
    def __init__(self, symbol, start_date, end_date, initial_capital=10000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.data = None
        self.portfolio = None
        self.portfolio_bh = None
        
    def download_data(self):
        """주가 데이터 다운로드"""
        print(f"Downloading data for {self.symbol} from {self.start_date} to {self.end_date}...")
        self.data = yf.download(self.symbol, start=self.start_date, end=self.end_date)
        if self.data.empty:
            raise ValueError("No data downloaded, check your internet connection or date range.")
        print(f"Downloaded {len(self.data)} data points.")
        return self.data
    
    def calculate_indicators(self, window=20, std_dev=2):
        """볼린저 밴드 및 관련 지표 계산"""
        # 이동평균 계산
        self.data['MA'] = self.data['Close'].rolling(window=window).mean()
        
        # 표준편차 계산
        self.data['STD'] = self.data['Close'].rolling(window=window).std()
        
        # 볼린저 밴드 계산
        self.data['Upper'] = self.data['MA'] + (self.data['STD'] * std_dev)
        self.data['Lower'] = self.data['MA'] - (self.data['STD'] * std_dev)
        
        # %B 지표 계산
        close_array = self.data['Close'].values
        upper_array = self.data['Upper'].values
        lower_array = self.data['Lower'].values
        
        # %B 계산 (가격이 밴드 내에서 어디에 위치하는지를 0~1 사이의 값으로 표현)
        result = []
        for i in range(len(close_array)):
            denominator = upper_array[i] - lower_array[i]
            if denominator == 0 or np.isnan(denominator):
                result.append(np.nan)
            else:
                result.append((close_array[i] - lower_array[i]) / denominator)
        
        self.data['%B'] = result
        
        # MFI (Money Flow Index) 계산
        typical_price = (self.data['High'] + self.data['Low'] + self.data['Close']) / 3
        money_flow = typical_price * self.data['Volume']
        
        # 양/음의 자금 흐름 초기화
        pos_flow = np.zeros(len(self.data))
        neg_flow = np.zeros(len(self.data))
        
        # 자금 흐름 계산
        tp_array = typical_price.values
        mf_array = money_flow.values
        
        for i in range(1, len(tp_array)):
            curr_tp = tp_array[i] if not isinstance(tp_array[i], np.ndarray) else tp_array[i].item()
            prev_tp = tp_array[i-1] if not isinstance(tp_array[i-1], np.ndarray) else tp_array[i-1].item()
            curr_mf = mf_array[i] if not isinstance(mf_array[i], np.ndarray) else mf_array[i].item()
            
            if curr_tp > prev_tp:
                pos_flow[i] = curr_mf
            elif curr_tp < prev_tp:
                neg_flow[i] = curr_mf
        
        # pandas Series로 변환
        positive_flow = pd.Series(pos_flow, index=self.data.index)
        negative_flow = pd.Series(neg_flow, index=self.data.index)
        
        # MFI 계산
        positive_flow_sum = positive_flow.rolling(window=14).sum()
        negative_flow_sum = negative_flow.rolling(window=14).sum()
        
        # 0으로 나누는 것 방지
        money_ratio = positive_flow_sum / negative_flow_sum.replace(0, 1e-10)
        self.data['MFI'] = 100 - (100 / (1 + money_ratio))
        
        # BNF 전략을 위한 추가 지표
        # Band Width - 밴드의 너비 계산
        self.data['BandWidth'] = (self.data['Upper'] - self.data['Lower']) / self.data['MA']
        
        # NaN 값 제거
        self.data.dropna(inplace=True)
        
    def generate_standard_signals(self):
        """일반 볼린저 밴드 전략 매매 신호 생성"""
        # 신호 초기화
        self.data['StandardSignal'] = 0
        
        # 매수 신호 (%B < 0.2 and MFI < 20)
        self.data.loc[(self.data['%B'] < 0.2) & (self.data['MFI'] < 20), 'StandardSignal'] = 1
        
        # 매도 신호 (%B > 0.8 and MFI > 80)
        self.data.loc[(self.data['%B'] > 0.8) & (self.data['MFI'] > 80), 'StandardSignal'] = -1
        
    def generate_bnf_signals(self):
        """BNF 볼린저 밴드 전략 매매 신호 생성"""
        # 신호 초기화
        self.data['BNFSignal'] = 0
        
        # 추세 확인을 위한 지표
        self.data['Trend'] = 0
        
        # 추세 강도 확인 (이동평균선 기울기 개선)
        self.data['MASlope'] = self.data['MA'].pct_change(periods=3) * 100  # 3일 동안의 변화율(%)
        
        # 상승/하락 추세 감지를 위한 밴드폭 기준 및 이동평균 기울기
        band_width_mean = self.data['BandWidth'].rolling(10).mean().values  # 10일 밴드폭 평균
        
        # 상승 추세 정의 (MA 기울기가 양수이고 밴드폭 확장)
        up_trend = (self.data['MASlope'].values > 0.3) & (self.data['BandWidth'].values > band_width_mean)
        self.data['UpTrend'] = up_trend
        
        # 하락 추세 정의 (MA 기울기가 음수이고 밴드폭 확장)
        down_trend = (self.data['MASlope'].values < -0.3) & (self.data['BandWidth'].values > band_width_mean)
        self.data['DownTrend'] = down_trend
        
        # 횡보장 감지 (추세가 약한 구간)
        self.data['SideWays'] = (~self.data['UpTrend']) & (~self.data['DownTrend'])
        
        # 추가 지표: 과거 10일간 가격 범위 대비 현재 위치
        # 1에 가까울수록 10일 고점, 0에 가까울수록 10일 저점
        self.data['PriceRange'] = (self.data['Close'] - self.data['Close'].rolling(10).min()) / \
                               (self.data['Close'].rolling(10).max() - self.data['Close'].rolling(10).min())
        
        # 가격 반전 패턴 계산 - 시프트된 배열 생성
        close_array = self.data['Close'].values
        close_prev1 = np.roll(close_array, 1)  # 1일 전 가격 배열
        close_prev2 = np.roll(close_array, 2)  # 2일 전 가격 배열
        
        # 첫 2일 데이터는 roll로 인해 유효하지 않으므로 제외
        close_prev1[:2] = np.nan
        close_prev2[:2] = np.nan
        
        # 반등 및 반전 패턴 계산 (더 완화된 조건)
        price_reversal_up = np.zeros_like(close_array, dtype=bool)
        price_reversal_down = np.zeros_like(close_array, dtype=bool)
        
        # 인덱스 2부터 패턴 계산 (첫 2일은 제외)
        for i in range(2, len(close_array)):
            # 하락 후 반등: 종가가 2일 연속 상승
            price_reversal_up[i] = (close_array[i] > close_prev1[i])
            
            # 상승 후 반전: 종가가 2일 연속 하락
            price_reversal_down[i] = (close_array[i] < close_prev1[i])
        
        self.data['PriceReversalUp'] = price_reversal_up
        self.data['PriceReversalDown'] = price_reversal_down
        
        # BNF 매매 신호 생성 - 거래 빈도 증가 및 조건 개선
        for i in range(22, len(self.data)):  # 20일 이동평균 계산에 필요한 데이터 확보 후 시작
            # NaN 값 건너뛰기
            if np.isnan(self.data['%B'].iloc[i]) or np.isnan(self.data['MFI'].iloc[i]):
                continue
            
            # 추세와 밴드 위치에 따른 맞춤형 매매 로직
            if self.data['SideWays'].iloc[i]:  # 횡보장에서의 전략
                # 횡보장에서는 %B와 MFI 기반으로 하되, 더 민감하게 반응
                if (self.data['%B'].iloc[i] < 0.3 and
                    self.data['MFI'].iloc[i] < 40 and
                    self.data['PriceReversalUp'].iloc[i]):
                    self.data.loc[self.data.index[i], 'BNFSignal'] = 1
                    
                elif (self.data['%B'].iloc[i] > 0.7 and
                     self.data['MFI'].iloc[i] > 60 and
                     self.data['PriceReversalDown'].iloc[i]):
                    self.data.loc[self.data.index[i], 'BNFSignal'] = -1
                    
            elif self.data['UpTrend'].iloc[i]:  # 상승세에서의 전략
                # 상승세에서는 매도신호에 더 민감하게, 매수신호에 더 엄격하게
                if (self.data['%B'].iloc[i] < 0.2 and
                    self.data['MFI'].iloc[i] < 30 and
                    self.data['PriceReversalUp'].iloc[i] and
                    self.data['PriceRange'].iloc[i] < 0.2):  # 저점 근처에서만 매수
                    self.data.loc[self.data.index[i], 'BNFSignal'] = 1
                    
                elif (self.data['%B'].iloc[i] > 0.75 and  # 더 높은 밴드에서 매도
                     self.data['MFI'].iloc[i] > 70 and
                     self.data['PriceReversalDown'].iloc[i]):
                    self.data.loc[self.data.index[i], 'BNFSignal'] = -1
                
            elif self.data['DownTrend'].iloc[i]:  # 하락세에서의 전략
                # 하락세에서는 매수신호에 더 민감하게, 매도신호에 더 엄격하게
                if (self.data['%B'].iloc[i] < 0.3 and
                    self.data['MFI'].iloc[i] < 30 and
                    self.data['PriceReversalUp'].iloc[i]):
                    self.data.loc[self.data.index[i], 'BNFSignal'] = 1
                    
                elif (self.data['%B'].iloc[i] > 0.8 and  # 더 높은 밴드에서만 매도
                     self.data['MFI'].iloc[i] > 75 and
                     self.data['PriceReversalDown'].iloc[i] and
                     self.data['PriceRange'].iloc[i] > 0.8):  # 고점 근처에서만 매도
                    self.data.loc[self.data.index[i], 'BNFSignal'] = -1
        
    def backtest_strategy(self, strategy_type='standard'):
        """전략 백테스트 실행"""
        # 포트폴리오 초기화
        self.portfolio = pd.DataFrame(index=self.data.index)
        self.portfolio['Holdings'] = 0.0
        self.portfolio['Cash'] = float(self.initial_capital)
        self.portfolio['PositionValue'] = 0.0
        self.portfolio['TotalValue'] = float(self.initial_capital)
        self.portfolio['Return'] = 0.0
        
        # 첫 날 수익률은 0
        self.portfolio.loc[self.portfolio.index[0], 'Return'] = 0.0
        
        # 매매 기록
        trades = []
        position = 0
        
        # 신호 컬럼 결정
        signal_column = 'StandardSignal' if strategy_type == 'standard' else 'BNFSignal'
        
        # 백테스트 실행
        for i in range(1, len(self.data.index)):
            date = self.data.index[i]
            prev_date = self.data.index[i-1]
            price = self.data.loc[date, 'Close']  # Series에서 스칼라 값 추출
            if isinstance(price, pd.Series):
                price = price.iloc[0]
                
            signal = self.data.loc[date, signal_column]  # Series에서 스칼라 값 추출
            if isinstance(signal, pd.Series):
                signal = signal.iloc[0]
            
            # 보유 주식 및 현금 이월
            self.portfolio.loc[date, 'Holdings'] = self.portfolio.loc[prev_date, 'Holdings']
            self.portfolio.loc[date, 'Cash'] = self.portfolio.loc[prev_date, 'Cash']
            
            # 신호 처리
            if signal == 1 and position == 0:  # 매수 신호
                shares_to_buy = int(self.portfolio.loc[date, 'Cash'] // price)
                cost = shares_to_buy * price
                
                self.portfolio.loc[date, 'Holdings'] += float(shares_to_buy)
                self.portfolio.loc[date, 'Cash'] -= float(cost)
                
                position = 1
                trades.append((date, 'BUY', shares_to_buy, price, cost))
                
            elif signal == -1 and position == 1:  # 매도 신호
                shares_to_sell = self.portfolio.loc[date, 'Holdings']
                revenue = shares_to_sell * price
                
                self.portfolio.loc[date, 'Holdings'] = 0.0
                self.portfolio.loc[date, 'Cash'] += float(revenue)
                
                position = 0
                trades.append((date, 'SELL', shares_to_sell, price, revenue))
            
            # 포트폴리오 가치 업데이트
            self.portfolio.loc[date, 'PositionValue'] = self.portfolio.loc[date, 'Holdings'] * price
            self.portfolio.loc[date, 'TotalValue'] = self.portfolio.loc[date, 'PositionValue'] + self.portfolio.loc[date, 'Cash']
            
            # 일간 수익률 계산
            self.portfolio.loc[date, 'Return'] = self.portfolio.loc[date, 'TotalValue'] / self.portfolio.loc[prev_date, 'TotalValue'] - 1
        
        # 누적 수익률 계산
        self.portfolio['CumulativeReturn'] = (1 + self.portfolio['Return']).cumprod()
        
        # 매매 기록 저장
        self.trades = trades
        
        return self.portfolio
    
    def backtest_buy_and_hold(self):
        """매수 후 보유 전략 백테스트"""
        # 포트폴리오 초기화
        self.portfolio_bh = pd.DataFrame(index=self.data.index)
        
        # 첫 종가 가져오기
        close_series = self.data['Close']
        first_price = close_series.iloc[0]  # 스칼라 값 직접 가져오기
        
        # 주식 수량 및 비용 계산
        shares = self.initial_capital // first_price
        initial_cost = shares * first_price
        remaining_cash = self.initial_capital - initial_cost
        
        # 포트폴리오 초기화
        self.portfolio_bh['Holdings'] = float(shares)
        self.portfolio_bh['Cash'] = float(remaining_cash)
        self.portfolio_bh['PositionValue'] = 0.0
        self.portfolio_bh['TotalValue'] = 0.0
        self.portfolio_bh['Return'] = 0.0
        
        # 포트폴리오 가치 계산
        for date in self.portfolio_bh.index:
            close_price = self.data.loc[date, 'Close']
            if isinstance(close_price, pd.Series):
                close_price = close_price.iloc[0]
                
            self.portfolio_bh.loc[date, 'PositionValue'] = float(self.portfolio_bh.loc[date, 'Holdings']) * close_price
            self.portfolio_bh.loc[date, 'TotalValue'] = self.portfolio_bh.loc[date, 'PositionValue'] + self.portfolio_bh.loc[date, 'Cash']
        
        # 일간 수익률 계산
        self.portfolio_bh.loc[self.portfolio_bh.index[0], 'Return'] = 0.0
        for i in range(1, len(self.portfolio_bh.index)):
            current_date = self.portfolio_bh.index[i]
            prev_date = self.portfolio_bh.index[i-1]
            self.portfolio_bh.loc[current_date, 'Return'] = (
                self.portfolio_bh.loc[current_date, 'TotalValue'] / 
                self.portfolio_bh.loc[prev_date, 'TotalValue'] - 1
            )
        
        # 누적 수익률 계산
        self.portfolio_bh['CumulativeReturn'] = (1 + self.portfolio_bh['Return']).cumprod()
        
        return self.portfolio_bh
    
    def calculate_metrics(self, portfolio):
        """성능 지표 계산"""
        metrics = {}
        metrics['Final Portfolio Value'] = portfolio['TotalValue'].iloc[-1]
        metrics['Total Return'] = portfolio['TotalValue'].iloc[-1] / self.initial_capital - 1
        
        # 연간 수익률 계산
        days = (portfolio.index[-1] - portfolio.index[0]).days
        years = days / 365
        metrics['Annual Return'] = (1 + metrics['Total Return']) ** (1 / years) - 1
        
        # 최대 낙폭 계산
        roll_max = portfolio['TotalValue'].cummax()
        drawdown = (portfolio['TotalValue'] / roll_max) - 1
        metrics['Max Drawdown'] = drawdown.min()
        
        # 샤프 비율 계산
        risk_free_rate = 0.02  # 2% 무위험 수익률 가정
        excess_returns = portfolio['Return'] - risk_free_rate / 252
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / portfolio['Return'].std()
        metrics['Sharpe Ratio'] = sharpe_ratio
        
        # 매매 횟수 (buy_and_hold는 매매 기록이 없으므로 조건부 계산)
        if hasattr(self, 'trades'):
            metrics['Trade Count'] = len(self.trades)
        else:
            metrics['Trade Count'] = 1  # 매수 후 보유는 1회 매매
        
        return metrics
    
    def plot_comparison(self, save_path=None):
        """세 전략의 성능 비교 그래프 생성"""
        # 그래프 설정
        plt.rcParams['font.family'] = 'AppleGothic'  # macOS용 한글 폰트
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 18), gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # 달러 형식 포맷터
        def currency_formatter(x, pos):
            return f'${int(x):,}'
        
        # 첫 번째 그래프: 포트폴리오 가치 비교
        standard_portfolio = self.standard_portfolio if hasattr(self, 'standard_portfolio') else None
        bnf_portfolio = self.bnf_portfolio if hasattr(self, 'bnf_portfolio') else None
        bh_portfolio = self.portfolio_bh if hasattr(self, 'portfolio_bh') else None
        
        if standard_portfolio is not None:
            ax1.plot(standard_portfolio.index, standard_portfolio['TotalValue'], 
                    label='Standard Bollinger', color='blue')
        
        if bnf_portfolio is not None:
            ax1.plot(bnf_portfolio.index, bnf_portfolio['TotalValue'], 
                    label='BNF Bollinger', color='purple')
        
        if bh_portfolio is not None:
            ax1.plot(bh_portfolio.index, bh_portfolio['TotalValue'], 
                    label='Buy & Hold', color='green', linestyle='--')
        
        ax1.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        ax1.set_title(f'{self.symbol} - Strategy Comparison (5-Year Backtest)', fontsize=16)
        ax1.set_ylabel('Portfolio Value ($)', fontsize=14)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 성능 지표 텍스트 상자
        if hasattr(self, 'standard_metrics'):
            standard_text = (
                f"Standard Bollinger:\n"
                f"Final Value: ${self.standard_metrics['Final Portfolio Value']:,.2f}\n"
                f"Annual Return: {self.standard_metrics['Annual Return']:.2%}\n"
                f"Max Drawdown: {self.standard_metrics['Max Drawdown']:.2%}\n"
                f"Sharpe Ratio: {self.standard_metrics['Sharpe Ratio']:.2f}\n"
                f"Trades: {self.standard_metrics['Trade Count']}"
            )
            props = dict(boxstyle='round', facecolor='white', alpha=0.7)
            ax1.text(0.02, 0.20, standard_text, transform=ax1.transAxes, fontsize=10, 
                    verticalalignment='bottom', bbox=props)
        
        if hasattr(self, 'bnf_metrics'):
            bnf_text = (
                f"BNF Bollinger:\n"
                f"Final Value: ${self.bnf_metrics['Final Portfolio Value']:,.2f}\n"
                f"Annual Return: {self.bnf_metrics['Annual Return']:.2%}\n"
                f"Max Drawdown: {self.bnf_metrics['Max Drawdown']:.2%}\n"
                f"Sharpe Ratio: {self.bnf_metrics['Sharpe Ratio']:.2f}\n"
                f"Trades: {self.bnf_metrics['Trade Count']}"
            )
            props = dict(boxstyle='round', facecolor='white', alpha=0.7)
            ax1.text(0.25, 0.20, bnf_text, transform=ax1.transAxes, fontsize=10, 
                    verticalalignment='bottom', bbox=props)
        
        if hasattr(self, 'bh_metrics'):
            bh_text = (
                f"Buy & Hold:\n"
                f"Final Value: ${self.bh_metrics['Final Portfolio Value']:,.2f}\n"
                f"Annual Return: {self.bh_metrics['Annual Return']:.2%}\n"
                f"Max Drawdown: {self.bh_metrics['Max Drawdown']:.2%}\n"
                f"Sharpe Ratio: {self.bh_metrics['Sharpe Ratio']:.2f}"
            )
            props = dict(boxstyle='round', facecolor='white', alpha=0.7)
            ax1.text(0.48, 0.20, bh_text, transform=ax1.transAxes, fontsize=10, 
                    verticalalignment='bottom', bbox=props)
        
        # 두 번째 그래프: 볼린저 밴드
        ax2.plot(self.data.index, self.data['Close'], label='Price', color='black')
        ax2.plot(self.data.index, self.data['MA'], label=f'MA(20)', color='blue', alpha=0.7)
        ax2.plot(self.data.index, self.data['Upper'], label='Upper Band', color='red', linestyle='--', alpha=0.5)
        ax2.plot(self.data.index, self.data['Lower'], label='Lower Band', color='green', linestyle='--', alpha=0.5)
        
        # 매매 신호 마커 추가
        if hasattr(self, 'trades'):
            for trade in self.trades:
                date, action, shares, price, value = trade
                if action == 'BUY':
                    ax2.scatter(date, price, color='green', marker='^', s=100)
                else:  # SELL
                    ax2.scatter(date, price, color='red', marker='v', s=100)
        
        ax2.set_ylabel('Price ($)', fontsize=14)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)
        
        # 세 번째 그래프: %B 및 MFI 지표
        ax3.plot(self.data.index, self.data['%B'], label='%B', color='purple')
        ax3.plot(self.data.index, self.data['MFI'] / 100, label='MFI (scaled)', color='orange')
        
        # 임계값 수평선
        ax3.axhline(y=0.2, color='green', linestyle='--', alpha=0.7)
        ax3.axhline(y=0.8, color='red', linestyle='--', alpha=0.7)
        
        ax3.set_ylabel('Indicator Value', fontsize=14)
        ax3.set_xlabel('Date', fontsize=14)
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 그래프 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    
    def run_comparison(self):
        """세 가지 전략 백테스트 및 비교 실행"""
        # 데이터 다운로드 및 지표 계산
        self.download_data()
        self.calculate_indicators()
        
        # 일반 볼린저 밴드 전략 신호 생성 및 백테스트
        self.generate_standard_signals()
        self.standard_portfolio = self.backtest_strategy(strategy_type='standard')
        self.standard_metrics = self.calculate_metrics(self.standard_portfolio)
        
        # BNF 볼린저 밴드 전략 신호 생성 및 백테스트
        self.generate_bnf_signals()
        self.bnf_portfolio = self.backtest_strategy(strategy_type='bnf')
        self.bnf_metrics = self.calculate_metrics(self.bnf_portfolio)
        
        # 매수 후 보유 전략 백테스트
        self.backtest_buy_and_hold()
        self.bh_metrics = self.calculate_metrics(self.portfolio_bh)
        
        # 결과 출력
        self.print_results()
        
        # 결과 디렉토리 생성
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 그래프 저장
        current_date = datetime.now().strftime('%Y%m%d')
        save_path = f"results/bollinger_strategy_comparison_{self.symbol}_{current_date}.png"
        self.plot_comparison(save_path=save_path)
        
        return {
            'standard': self.standard_metrics,
            'bnf': self.bnf_metrics,
            'buy_and_hold': self.bh_metrics
        }
    
    def print_results(self):
        """백테스트 결과 출력"""
        print("\n=== Bollinger Bands Strategy Comparison ===")
        print(f"Symbol: {self.symbol}")
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        
        print("\n--- Standard Bollinger Strategy ---")
        print(f"Final Portfolio Value: ${self.standard_metrics['Final Portfolio Value']:,.2f}")
        print(f"Total Return: {self.standard_metrics['Total Return']:.2%}")
        print(f"Annual Return: {self.standard_metrics['Annual Return']:.2%}")
        print(f"Maximum Drawdown: {self.standard_metrics['Max Drawdown']:.2%}")
        print(f"Sharpe Ratio: {self.standard_metrics['Sharpe Ratio']:.2f}")
        print(f"Number of Trades: {self.standard_metrics['Trade Count']}")
        
        print("\n--- BNF Bollinger Strategy ---")
        print(f"Final Portfolio Value: ${self.bnf_metrics['Final Portfolio Value']:,.2f}")
        print(f"Total Return: {self.bnf_metrics['Total Return']:.2%}")
        print(f"Annual Return: {self.bnf_metrics['Annual Return']:.2%}")
        print(f"Maximum Drawdown: {self.bnf_metrics['Max Drawdown']:.2%}")
        print(f"Sharpe Ratio: {self.bnf_metrics['Sharpe Ratio']:.2f}")
        print(f"Number of Trades: {self.bnf_metrics['Trade Count']}")
        
        print("\n--- Buy & Hold Performance ---")
        print(f"Final Portfolio Value: ${self.bh_metrics['Final Portfolio Value']:,.2f}")
        print(f"Total Return: {self.bh_metrics['Total Return']:.2%}")
        print(f"Annual Return: {self.bh_metrics['Annual Return']:.2%}")
        print(f"Maximum Drawdown: {self.bh_metrics['Max Drawdown']:.2%}")
        print(f"Sharpe Ratio: {self.bh_metrics['Sharpe Ratio']:.2f}")


def run_comparison(symbol='SPY', years=5, initial_capital=10000):
    """
    표준 볼린저 밴드, BNF 볼린저 밴드, 매수 후 보유 전략의 백테스트 비교 실행
    
    Args:
        symbol (str): 주식 티커 심볼 (기본값: 'SPY')
        years (int): 백테스트 기간(년) (기본값: 5)
        initial_capital (int): 초기 투자금액 (기본값: 10000)
    
    Returns:
        dict: 각 전략별 성능 지표
    """
    # 날짜 범위 설정
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365 * years)).strftime('%Y-%m-%d')
    
    # BNF 전략 객체 생성 및 실행
    strategy = BNFBollingerStrategy(symbol, start_date, end_date, initial_capital)
    results = strategy.run_comparison()
    
    return strategy, results


if __name__ == "__main__":
    # SPY에 대한 5년 백테스트 실행
    strategy, results = run_comparison(symbol='SPY', years=5, initial_capital=10000) 