#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import os
import matplotlib as mpl

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # macOS용 한글 폰트
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

class SimpleBacktest:
    def __init__(self, symbol, start_date, end_date=None, initial_capital=10000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.initial_capital = initial_capital
        self.data = None
        
    def download_data(self):
        """주가 데이터 다운로드"""
        print(f"{self.symbol} data downloading... ({self.start_date} ~ {self.end_date})")
        self.data = yf.download(self.symbol, start=self.start_date, end=self.end_date)
        if self.data.empty:
            raise ValueError("Failed to download data. Check your internet connection or date range.")
        print(f"{len(self.data)} data points downloaded.")
        return self.data
    
    def calculate_returns(self):
        """수익률 계산"""
        # 주가 데이터가 없으면 다운로드
        if self.data is None or self.data.empty:
            self.download_data()
            
        # 첫 주가와 마지막 주가
        first_price = self.data['Close'].iloc[0]
        last_price = self.data['Close'].iloc[-1]
        
        # 단순 매수 후 보유 전략 계산
        shares = self.initial_capital / first_price
        final_value = shares * last_price
        total_return = (final_value / self.initial_capital) - 1
        
        # 연간 수익률 계산
        days = (self.data.index[-1] - self.data.index[0]).days
        years = days / 365
        annual_return = (1 + total_return) ** (1 / years) - 1
        
        # 최대 낙폭 계산
        peak = self.data['Close'].cummax()
        drawdown = (self.data['Close'] / peak) - 1
        max_drawdown = drawdown.min()
        
        # Helper function to safely convert pandas Series to float
        def safe_float(value, multiplier=1.0):
            if hasattr(value, 'iloc'):
                return float(value.iloc[0] * multiplier)
            return float(value * multiplier)
        
        # Use safe conversion to avoid FutureWarning with Series objects
        return {
            'symbol': self.symbol,
            'initial_capital': float(self.initial_capital),
            'final_value': safe_float(final_value),
            'total_return': safe_float(total_return, 100),  # 백분율로 변환
            'annual_return': safe_float(annual_return, 100),  # 백분율로 변환
            'max_drawdown': safe_float(max_drawdown, 100),  # 백분율로 변환
            'first_price': safe_float(first_price),
            'last_price': safe_float(last_price),
            'start_date': self.data.index[0].strftime('%Y-%m-%d'),
            'end_date': self.data.index[-1].strftime('%Y-%m-%d'),
        }

def run_multiple_backtests(symbols, start_date, end_date=None, initial_capital=10000):
    """여러 종목의 백테스트를 한번에 실행"""
    results = []
    
    for symbol in symbols:
        print(f"\n========== {symbol} Backtest Running ==========")
        backtest = SimpleBacktest(symbol, start_date, end_date, initial_capital)
        try:
            results.append(backtest.calculate_returns())
        except Exception as e:
            print(f"Error: {e}")
    
    # 결과를 데이터프레임으로 변환
    results_df = pd.DataFrame(results)
    
    # 결과가 없으면 종료
    if len(results) == 0:
        print("All backtests failed.")
        return None
    
    # 안전하게 정렬 - 데이터 문제로 정렬에 실패하면 정렬 없이 진행
    try:
        results_df = results_df.sort_values('annual_return', ascending=False)
    except Exception as e:
        print(f"Error during sorting: {e}")
        print("Continuing without sorting.")
    
    # 결과 출력
    print("\n========== Backtest Results Summary ==========")
    cols_to_display = ['symbol', 'total_return', 'annual_return', 'max_drawdown', 'final_value']
    try:
        print(results_df[cols_to_display].to_string(index=False))
    except Exception as e:
        print(f"Result output error: {e}")
        # 대안으로 각 종목별 결과를 직접 출력
        for idx, row in results_df.iterrows():
            try:
                print(f"{row['symbol']}: Total Return {row['total_return']:.2f}%, Annual {row['annual_return']:.2f}%, Max Drawdown {row['max_drawdown']:.2f}%")
            except:
                print(f"Error while printing results for symbol at index {idx}")
    
    # 결과 저장 디렉토리 생성
    if not os.path.exists('results'):
        os.makedirs('results')
    
    # 결과 저장 (CSV 및 마크다운)
    results_df.to_csv('results/backtest_results.csv', index=False)
    
    with open('results/backtest_results.md', 'w', encoding='utf-8') as f:
        f.write("# Backtest Results Summary\n\n")
        f.write(f"Test Period: {start_date} ~ {end_date if end_date else 'Present'}\n")
        f.write(f"Initial Capital: ${initial_capital:,}\n\n")
        f.write("## Performance by Symbol\n\n")
        f.write(results_df.to_markdown(index=False))
        
        # 추가 분석
        best_performer = results_df.iloc[0]['symbol']
        worst_performer = results_df.iloc[-1]['symbol']
        avg_return = results_df['annual_return'].mean()
        
        f.write("\n\n## Analysis and Conclusion\n\n")
        f.write(f"1. **Best Performer**: {best_performer} (Annual Return: {results_df.iloc[0]['annual_return']:.2f}%)\n")
        f.write(f"2. **Worst Performer**: {worst_performer} (Annual Return: {results_df.iloc[-1]['annual_return']:.2f}%)\n")
        f.write(f"3. **Average Annual Return**: {avg_return:.2f}%\n")
    
    # 그래프 생성 및 저장
    plt.figure(figsize=(12, 8))
    
    # 연간 수익률 그래프
    plt.subplot(2, 1, 1)
    bars = plt.bar(results_df['symbol'], results_df['annual_return'])
    plt.axhline(y=avg_return, color='r', linestyle='--', alpha=0.7, label=f'Average: {avg_return:.2f}%')
    plt.ylabel('Annual Return (%)')
    plt.title('Annual Return Comparison by Symbol')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    # 색상 설정
    for i, bar in enumerate(bars):
        if results_df.iloc[i]['annual_return'] > 0:
            bar.set_color('green')
        else:
            bar.set_color('red')
    
    # 최대 낙폭 그래프
    plt.subplot(2, 1, 2)
    try:
        bars = plt.bar(results_df['symbol'], results_df['max_drawdown'])
        plt.ylabel('Max Drawdown (%)')
        plt.title('Max Drawdown Comparison by Symbol')
        plt.grid(axis='y', alpha=0.3)
        
        # 색상 설정 (낙폭은 음수이므로 항상 빨간색)
        for bar in bars:
            bar.set_color('red')
    except Exception as e:
        print(f"Error during drawdown graph creation: {e}")
    
    plt.tight_layout()
    plt.savefig('results/backtest_performance_comparison.png', dpi=300)
    
    return results_df

if __name__ == '__main__':
    # main.sh에서 추출한 종목 목록
    symbols = ['SPY', 'SCHD', 'O', 'JEPQ', 'BIL', 'SGOV', 'TLT', 'TLTW']
    
    # 백테스트 실행 (2020년부터 현재까지)
    results = run_multiple_backtests(
        symbols=symbols,
        start_date='2020-01-01',
        end_date=None,
        initial_capital=10000
    ) 