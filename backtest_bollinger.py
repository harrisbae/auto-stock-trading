#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import os
from matplotlib.ticker import FuncFormatter

class BollingerStrategy:
    def __init__(self, symbol, start_date, end_date, initial_capital=10000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.data = None
        self.portfolio = None
        self.portfolio_bh = None
        
    def download_data(self):
        """Download stock data from Yahoo Finance"""
        print(f"Downloading data for {self.symbol} from {self.start_date} to {self.end_date}...")
        self.data = yf.download(self.symbol, start=self.start_date, end=self.end_date)
        if self.data.empty:
            raise ValueError("No data downloaded, check your internet connection or date range.")
        print(f"Downloaded {len(self.data)} data points.")
        
    def calculate_indicators(self, window=20, std_dev=2):
        """Calculate Bollinger Bands and related indicators"""
        # Calculate moving average
        self.data['MA'] = self.data['Close'].rolling(window=window).mean()
        
        # Calculate standard deviation
        self.data['STD'] = self.data['Close'].rolling(window=window).std()
        
        # Calculate Bollinger Bands
        self.data['Upper'] = self.data['MA'] + (self.data['STD'] * std_dev)
        self.data['Lower'] = self.data['MA'] - (self.data['STD'] * std_dev)
        
        # Calculate %B indicator using a simple approach
        # Manually calculate numerator and denominator as numpy arrays
        close_array = self.data['Close'].values
        upper_array = self.data['Upper'].values
        lower_array = self.data['Lower'].values
        
        # Calculate %B
        result = []
        for i in range(len(close_array)):
            denominator = upper_array[i] - lower_array[i]
            if denominator == 0 or np.isnan(denominator):
                result.append(np.nan)
            else:
                result.append((close_array[i] - lower_array[i]) / denominator)
        
        # Assign the result to a new column
        self.data['%B'] = result
        
        # Calculate MFI (Money Flow Index)
        typical_price = (self.data['High'] + self.data['Low'] + self.data['Close']) / 3
        money_flow = typical_price * self.data['Volume']
        
        # Initialize arrays for positive and negative flow with zeros
        pos_flow = np.zeros(len(self.data))
        neg_flow = np.zeros(len(self.data))
        
        # Calculate flows using numpy arrays
        tp_array = typical_price.values
        mf_array = money_flow.values
        
        # Calculate flows starting from index 1
        for i in range(1, len(tp_array)):
            # Extract single values to avoid deprecation warning
            curr_tp = float(tp_array[i]) if isinstance(tp_array[i], np.ndarray) else tp_array[i]
            prev_tp = float(tp_array[i-1]) if isinstance(tp_array[i-1], np.ndarray) else tp_array[i-1]
            curr_mf = float(mf_array[i]) if isinstance(mf_array[i], np.ndarray) else mf_array[i]
            
            if curr_tp > prev_tp:
                pos_flow[i] = curr_mf
            elif curr_tp < prev_tp:
                neg_flow[i] = curr_mf
        
        # Convert back to pandas Series
        positive_flow = pd.Series(pos_flow, index=self.data.index)
        negative_flow = pd.Series(neg_flow, index=self.data.index)
        
        # Calculate the MFI
        positive_flow_sum = positive_flow.rolling(window=14).sum()
        negative_flow_sum = negative_flow.rolling(window=14).sum()
        
        # Avoid division by zero
        money_ratio = positive_flow_sum / negative_flow_sum.replace(0, 1e-10)
        self.data['MFI'] = 100 - (100 / (1 + money_ratio))
        
        # Drop NaN values
        self.data.dropna(inplace=True)
        
    def generate_signals(self):
        """Generate buy/sell signals based on Bollinger Bands"""
        # Initialize signal column
        self.data['Signal'] = 0
        
        # Buy signal (%B < 0.2 and MFI < 20)
        self.data.loc[(self.data['%B'] < 0.2) & (self.data['MFI'] < 20), 'Signal'] = 1
        
        # Sell signal (%B > 0.8 and MFI > 80)
        self.data.loc[(self.data['%B'] > 0.8) & (self.data['MFI'] > 80), 'Signal'] = -1
        
    def backtest(self):
        """Run backtest of the Bollinger Bands strategy"""
        # Create portfolio dataframe
        self.portfolio = pd.DataFrame(index=self.data.index)
        self.portfolio['Holdings'] = 0.0
        self.portfolio['Cash'] = float(self.initial_capital)
        self.portfolio['PositionValue'] = 0.0
        self.portfolio['TotalValue'] = float(self.initial_capital)
        self.portfolio['Return'] = 0.0
        
        # Set the first day's return to 0
        self.portfolio.loc[self.portfolio.index[0], 'Return'] = 0.0
        
        # Track trades
        trades = []
        position = 0
        
        # Run backtest
        for i in range(1, len(self.data.index)):
            date = self.data.index[i]
            prev_date = self.data.index[i-1]
            price = self.data.loc[date, 'Close'].iloc[0]  # Get the scalar value
            signal = self.data.loc[date, 'Signal'].iloc[0]  # Get the scalar value
            
            # Carry forward holdings and cash
            self.portfolio.loc[date, 'Holdings'] = self.portfolio.loc[prev_date, 'Holdings']
            self.portfolio.loc[date, 'Cash'] = self.portfolio.loc[prev_date, 'Cash']
            
            # Process signals
            if signal == 1 and position == 0:  # Buy signal
                shares_to_buy = int(self.portfolio.loc[date, 'Cash'] // price)
                cost = shares_to_buy * price
                
                self.portfolio.loc[date, 'Holdings'] += float(shares_to_buy)
                self.portfolio.loc[date, 'Cash'] -= float(cost)
                
                position = 1
                trades.append((date, 'BUY', shares_to_buy, price, cost))
                
            elif signal == -1 and position == 1:  # Sell signal
                shares_to_sell = self.portfolio.loc[date, 'Holdings']
                revenue = shares_to_sell * price
                
                self.portfolio.loc[date, 'Holdings'] = 0.0
                self.portfolio.loc[date, 'Cash'] += float(revenue)
                
                position = 0
                trades.append((date, 'SELL', shares_to_sell, price, revenue))
            
            # Update portfolio value
            self.portfolio.loc[date, 'PositionValue'] = self.portfolio.loc[date, 'Holdings'] * price
            self.portfolio.loc[date, 'TotalValue'] = self.portfolio.loc[date, 'PositionValue'] + self.portfolio.loc[date, 'Cash']
            
            # Calculate daily return
            self.portfolio.loc[date, 'Return'] = self.portfolio.loc[date, 'TotalValue'] / self.portfolio.loc[prev_date, 'TotalValue'] - 1
        
        # Calculate cumulative returns
        self.portfolio['CumulativeReturn'] = (1 + self.portfolio['Return']).cumprod()
        
        # Store trades
        self.trades = trades
        
        # Buy and Hold strategy for comparison
        self.backtest_buy_and_hold()
        
    def backtest_buy_and_hold(self):
        """Run backtest for buy and hold strategy"""
        # Create portfolio dataframe
        self.portfolio_bh = pd.DataFrame(index=self.data.index)
        # Access first Close price with proper Series to scalar conversion
        close_series = self.data['Close']
        first_price = close_series.iloc[0]  # Get scalar value directly without float conversion
        shares = self.initial_capital // first_price
        initial_cost = shares * first_price
        remaining_cash = self.initial_capital - initial_cost
        
        # Initialize all columns as float to avoid dtype issues
        self.portfolio_bh['Holdings'] = float(shares)
        self.portfolio_bh['Cash'] = float(remaining_cash)
        self.portfolio_bh['PositionValue'] = 0.0
        self.portfolio_bh['TotalValue'] = 0.0
        self.portfolio_bh['Return'] = 0.0
        
        # Calculate position value for each date
        for date in self.portfolio_bh.index:
            close_price = float(self.data.loc[date, 'Close'].iloc[0])  # Get scalar price
            self.portfolio_bh.loc[date, 'PositionValue'] = float(self.portfolio_bh.loc[date, 'Holdings']) * close_price
            self.portfolio_bh.loc[date, 'TotalValue'] = self.portfolio_bh.loc[date, 'PositionValue'] + self.portfolio_bh.loc[date, 'Cash']
        
        # Calculate daily returns - first day's return is 0, then use pct_change with fill_method=None
        self.portfolio_bh.loc[self.portfolio_bh.index[0], 'Return'] = 0.0
        for i in range(1, len(self.portfolio_bh.index)):
            current_date = self.portfolio_bh.index[i]
            prev_date = self.portfolio_bh.index[i-1]
            self.portfolio_bh.loc[current_date, 'Return'] = (
                self.portfolio_bh.loc[current_date, 'TotalValue'] / 
                self.portfolio_bh.loc[prev_date, 'TotalValue'] - 1
            )
        
        # Calculate cumulative returns
        self.portfolio_bh['CumulativeReturn'] = (1 + self.portfolio_bh['Return']).cumprod()
        
    def calculate_metrics(self):
        """Calculate performance metrics"""
        # Calculate metrics for strategy
        self.metrics = {}
        self.metrics['Final Portfolio Value'] = self.portfolio['TotalValue'].iloc[-1]
        self.metrics['Total Return'] = self.portfolio['TotalValue'].iloc[-1] / self.initial_capital - 1
        self.metrics['Annual Return'] = (1 + self.metrics['Total Return']) ** (252 / len(self.portfolio)) - 1
        
        # Calculate Maximum Drawdown
        roll_max = self.portfolio['TotalValue'].cummax()
        drawdown = (self.portfolio['TotalValue'] / roll_max) - 1
        self.metrics['Max Drawdown'] = drawdown.min()
        
        # Calculate Sharpe Ratio
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        excess_returns = self.portfolio['Return'] - risk_free_rate / 252
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / self.portfolio['Return'].std()
        self.metrics['Sharpe Ratio'] = sharpe_ratio
        
        # Calculate trade count
        self.metrics['Trade Count'] = len(self.trades)
        
        # Calculate metrics for buy and hold
        self.metrics_bh = {}
        self.metrics_bh['Final Portfolio Value'] = self.portfolio_bh['TotalValue'].iloc[-1]
        self.metrics_bh['Total Return'] = self.portfolio_bh['TotalValue'].iloc[-1] / self.initial_capital - 1
        self.metrics_bh['Annual Return'] = (1 + self.metrics_bh['Total Return']) ** (252 / len(self.portfolio_bh)) - 1
        
        # Calculate Maximum Drawdown for buy and hold
        roll_max_bh = self.portfolio_bh['TotalValue'].cummax()
        drawdown_bh = (self.portfolio_bh['TotalValue'] / roll_max_bh) - 1
        self.metrics_bh['Max Drawdown'] = drawdown_bh.min()
        
        # Calculate Sharpe Ratio for buy and hold
        excess_returns_bh = self.portfolio_bh['Return'] - risk_free_rate / 252
        sharpe_ratio_bh = np.sqrt(252) * excess_returns_bh.mean() / self.portfolio_bh['Return'].std()
        self.metrics_bh['Sharpe Ratio'] = sharpe_ratio_bh
        
        # Calculate trade count for buy and hold
        self.metrics_bh['Trade Count'] = 1  # Just buy at the beginning
        
    def plot_results(self, save_path=None):
        """Plot backtest results"""
        # Set up the figure
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 16), gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # Format x-axis dates
        plt.rcParams.update({'font.size': 12})
        
        # Plot 1: Portfolio Performance
        ax1.plot(self.portfolio.index, self.portfolio['TotalValue'], label='Bollinger Strategy', color='blue')
        ax1.plot(self.portfolio_bh.index, self.portfolio_bh['TotalValue'], label='Buy & Hold', color='green', linestyle='--')
        
        # Add y-axis formatter for dollar amounts
        def currency_formatter(x, pos):
            return f'${int(x):,}'
        
        ax1.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        
        # Add labels and title
        ax1.set_title(f'{self.symbol} - Bollinger Bands Strategy Backtest', fontsize=16)
        ax1.set_ylabel('Portfolio Value ($)', fontsize=14)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # Annotate with metrics
        strategy_text = (
            f"Bollinger Strategy:\n"
            f"Final Value: ${self.metrics['Final Portfolio Value']:,.2f}\n"
            f"Annual Return: {self.metrics['Annual Return']:.2%}\n"
            f"Max Drawdown: {self.metrics['Max Drawdown']:.2%}\n"
            f"Sharpe Ratio: {self.metrics['Sharpe Ratio']:.2f}\n"
            f"Trades: {self.metrics['Trade Count']}"
        )
        
        bh_text = (
            f"Buy & Hold:\n"
            f"Final Value: ${self.metrics_bh['Final Portfolio Value']:,.2f}\n"
            f"Annual Return: {self.metrics_bh['Annual Return']:.2%}\n"
            f"Max Drawdown: {self.metrics_bh['Max Drawdown']:.2%}\n"
            f"Sharpe Ratio: {self.metrics_bh['Sharpe Ratio']:.2f}"
        )
        
        # Add text box with metrics
        props = dict(boxstyle='round', facecolor='white', alpha=0.7)
        ax1.text(0.02, 0.15, strategy_text, transform=ax1.transAxes, fontsize=12, 
                 verticalalignment='bottom', bbox=props)
        ax1.text(0.25, 0.15, bh_text, transform=ax1.transAxes, fontsize=12, 
                 verticalalignment='bottom', bbox=props)
        
        # Plot 2: Bollinger Bands
        ax2.plot(self.data.index, self.data['Close'], label='Price', color='black')
        ax2.plot(self.data.index, self.data['MA'], label=f'MA({20})', color='blue', alpha=0.7)
        ax2.plot(self.data.index, self.data['Upper'], label='Upper Band', color='red', linestyle='--', alpha=0.5)
        ax2.plot(self.data.index, self.data['Lower'], label='Lower Band', color='green', linestyle='--', alpha=0.5)
        
        # Add buy/sell markers
        for trade in self.trades:
            date, action, shares, price, value = trade
            if action == 'BUY':
                ax2.scatter(date, price, color='green', marker='^', s=100)
            else:  # SELL
                ax2.scatter(date, price, color='red', marker='v', s=100)
                
        ax2.set_ylabel('Price ($)', fontsize=14)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: %B and MFI indicators
        ax3.plot(self.data.index, self.data['%B'], label='%B', color='purple')
        ax3.plot(self.data.index, self.data['MFI'] / 100, label='MFI (scaled)', color='orange')
        
        # Add horizontal lines for thresholds
        ax3.axhline(y=0.2, color='green', linestyle='--', alpha=0.7)
        ax3.axhline(y=0.8, color='red', linestyle='--', alpha=0.7)
        
        ax3.set_ylabel('Indicator Value', fontsize=14)
        ax3.set_xlabel('Date', fontsize=14)
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save or show the figure
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
            
    def print_results(self):
        """Print backtest results"""
        print("\n=== Bollinger Bands Strategy Backtest Results ===")
        print(f"Symbol: {self.symbol}")
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        
        print("\n--- Performance Metrics ---")
        print(f"Final Portfolio Value: ${self.metrics['Final Portfolio Value']:,.2f}")
        print(f"Total Return: {self.metrics['Total Return']:.2%}")
        print(f"Annual Return: {self.metrics['Annual Return']:.2%}")
        print(f"Maximum Drawdown: {self.metrics['Max Drawdown']:.2%}")
        print(f"Sharpe Ratio: {self.metrics['Sharpe Ratio']:.2f}")
        print(f"Number of Trades: {self.metrics['Trade Count']}")
        
        print("\n--- Buy & Hold Performance ---")
        print(f"Final Portfolio Value: ${self.metrics_bh['Final Portfolio Value']:,.2f}")
        print(f"Total Return: {self.metrics_bh['Total Return']:.2%}")
        print(f"Annual Return: {self.metrics_bh['Annual Return']:.2%}")
        print(f"Maximum Drawdown: {self.metrics_bh['Max Drawdown']:.2%}")
        print(f"Sharpe Ratio: {self.metrics_bh['Sharpe Ratio']:.2f}")
        
        print("\n--- Trade Summary ---")
        if len(self.trades) > 0:
            for i, trade in enumerate(self.trades, 1):
                date, action, shares, price, value = trade
                print(f"{i}. {date.strftime('%Y-%m-%d')}: {action} {int(shares)} shares at ${price:.2f} (${value:,.2f})")
        else:
            print("No trades executed during the backtest period.")

def run_backtest(symbol='SPY', start_date=None, end_date=None, initial_capital=10000, window=20, std_dev=2):
    """Run a complete backtest"""
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
    
    # Create and run the strategy
    strategy = BollingerStrategy(symbol, start_date, end_date, initial_capital)
    strategy.download_data()
    strategy.calculate_indicators(window=window, std_dev=std_dev)
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    
    # Print results
    strategy.print_results()
    
    # Create the results directory if it doesn't exist
    if not os.path.exists('results'):
        os.makedirs('results')
    
    # Save plot with current date
    current_date = datetime.now().strftime('%Y%m%d')
    save_path = f"results/bollinger_bands_backtest_{current_date}.png"
    strategy.plot_results(save_path=save_path)
    
    return strategy

if __name__ == "__main__":
    run_backtest(
        symbol='AAPL',
        start_date='2020-01-01',
        end_date='2025-04-25',
        initial_capital=10000,
        window=20,
        std_dev=2
    ) 