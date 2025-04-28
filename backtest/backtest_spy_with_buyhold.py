import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import os
import sys

# Add the project root to the Python path to import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators import add_all_indicators

# Define backtest parameters
START_DATE = "2020-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")
TICKER = "SPY"
INITIAL_CAPITAL = 10000
COMMISSION = 0.001  # 0.1% commission per trade

def download_data(ticker, start_date, end_date):
    """Download historical data for a ticker"""
    print(f"Downloading {ticker} data from {start_date} to {end_date}...")
    data = yf.download(ticker, start=start_date, end=end_date)
    
    # Flatten multi-level column names if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    
    print(f"Downloaded {len(data)} data points for {ticker}")
    return data

def run_buy_and_hold(df):
    """
    Run a simple buy and hold strategy
    
    Parameters:
    -----------
    df : DataFrame
        Stock data
    
    Returns:
    --------
    dict
        Backtest results
    """
    # Initialize variables
    cash = 0
    equity = []
    
    # Get starting price and calculate shares to buy
    start_price = df['Close'].iloc[0]
    shares = int(INITIAL_CAPITAL / start_price)
    cost = shares * start_price * (1 + COMMISSION)
    cash = INITIAL_CAPITAL - cost
    
    # Track equity value over time
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        current_equity = cash + shares * current_price
        equity.append(current_equity)
    
    # Calculate returns
    total_return = (equity[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # Calculate annualized return
    years = (df.index[-1] - df.index[0]).days / 365.25
    annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100
    
    # Calculate max drawdown
    drawdowns = []
    max_equity = equity[0]
    
    for current_equity in equity:
        if current_equity > max_equity:
            max_equity = current_equity
        if max_equity > 0:
            drawdown = (max_equity - current_equity) / max_equity * 100
            drawdowns.append(drawdown)
    
    max_drawdown = max(drawdowns) if drawdowns else 0
    
    # Return results
    results = {
        'equity_curve': equity,
        'buy_signals': [0],  # Buy at the start
        'sell_signals': [],  # Never sell
        'trades': [{'type': 'buy', 'price': start_price, 'shares': shares, 'value': shares * start_price}],
        'parameters': {'strategy': 'Buy and Hold'},
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'final_value': equity[-1],
        'sharpe_ratio': (annual_return - 1.5) / (np.std(np.diff(equity)/equity[:-1]) * np.sqrt(252)) if len(equity) > 1 else 0
    }
    
    return results

def run_backtest(df, params):
    """
    Run backtest with specified parameters
    
    Parameters:
    -----------
    df : DataFrame
        Stock data with indicators
    params : dict
        Strategy parameters
    
    Returns:
    --------
    dict
        Backtest results
    """
    # Extract parameters
    buy_b_threshold = params.get('buy_b_threshold', 0.2)
    buy_mfi_threshold = params.get('buy_mfi_threshold', 20)
    sell_b_threshold = params.get('sell_b_threshold', 0.8)
    sell_mfi_threshold = params.get('sell_mfi_threshold', 80)
    tranche_count = params.get('tranche_count', 3)
    stop_loss_percent = params.get('stop_loss_percent', 7)
    band_riding = params.get('band_riding', False)
    risk_level = params.get('risk_level', 'medium')
    
    # Initialize portfolio variables
    cash = INITIAL_CAPITAL
    shares = 0
    equity = []
    buy_signals = []
    sell_signals = []
    trades = []
    
    # Portfolio tracking
    entry_price = 0
    max_price_since_entry = 0
    stop_loss_price = 0
    
    # Tranche tracking
    current_tranche = 0
    allocated_capital = 0
    
    # Risk tracking
    drawdowns = []
    max_equity = INITIAL_CAPITAL
    
    # Ensure required columns exist
    if '%B' not in df.columns or 'MFI' not in df.columns:
        print("Error: Required columns %B or MFI not found in the dataframe")
        return None
    
    # Loop through each day
    for i in range(len(df)):
        date = df.index[i]
        current_price = df['Close'].iloc[i]
        
        # Skip days with missing indicator values
        b_value = df['%B'].iloc[i]
        mfi_value = df['MFI'].iloc[i]
        
        if pd.isna(b_value) or pd.isna(mfi_value):
            equity.append(cash + shares * current_price)
            continue
        
        # Calculate price deviation from moving average
        if 'MA25' in df.columns and not pd.isna(df['MA25'].iloc[i]):
            dev_percent = (current_price - df['MA25'].iloc[i]) / df['MA25'].iloc[i] * 100
        else:
            dev_percent = 0
        
        # Detect band riding if enabled
        is_band_riding = False
        if band_riding and i >= 5:
            lookback_df = df.iloc[i-5:i+1]
            upper_band_touches = lookback_df[lookback_df['%B'] > 0.8]
            is_band_riding = len(upper_band_touches) >= 3
        
        # Check for buy signal
        buy_signal = False
        if (shares == 0 or current_tranche < tranche_count) and b_value < buy_b_threshold and mfi_value < buy_mfi_threshold:
            buy_signal = True
            
            # Determine allocation amount based on tranche
            if current_tranche == 0:
                allocation_percent = 0.3  # 30% for first tranche
            elif current_tranche == 1:
                allocation_percent = 0.3  # 30% for second tranche
            else:
                allocation_percent = 0.4  # 40% for final tranche
            
            # Risk adjustment based on risk level
            if risk_level == 'low':
                allocation_percent *= 0.8
            elif risk_level == 'high':
                allocation_percent *= 1.2
                
            # Calculate shares to buy
            amount_to_invest = (INITIAL_CAPITAL * allocation_percent) - allocated_capital
            if amount_to_invest > cash:
                amount_to_invest = cash
                
            additional_shares = int(amount_to_invest / current_price)
            
            if additional_shares > 0:
                # Execute buy
                cost = additional_shares * current_price * (1 + COMMISSION)
                if cost <= cash:
                    cash -= cost
                    shares += additional_shares
                    
                    # Update entry info
                    if current_tranche == 0:
                        entry_price = current_price
                        max_price_since_entry = current_price
                        stop_loss_price = entry_price * (1 - stop_loss_percent/100)
                    else:
                        # Recalculate average entry price
                        entry_price = (entry_price * (shares - additional_shares) + 
                                     current_price * additional_shares) / shares
                        stop_loss_price = entry_price * (1 - stop_loss_percent/100)
                    
                    current_tranche += 1
                    allocated_capital += amount_to_invest
                    
                    # Record trade
                    trades.append({
                        'date': date,
                        'type': 'buy',
                        'price': current_price,
                        'shares': additional_shares,
                        'value': additional_shares * current_price,
                        'tranche': current_tranche
                    })
                    
                    buy_signals.append(i)
        
        # Check for sell signal
        sell_signal = False
        if shares > 0:
            # Update maximum price since entry
            if current_price > max_price_since_entry:
                max_price_since_entry = current_price
            
            # Check for sell conditions
            if b_value > sell_b_threshold and mfi_value > sell_mfi_threshold:
                sell_signal = True
            # Stop loss check
            elif current_price <= stop_loss_price:
                sell_signal = True
            # Band riding detection (sell half on band riding if enabled)
            elif is_band_riding and band_riding:
                # Sell half position on band riding
                sell_shares = shares // 2
                if sell_shares > 0:
                    cash += sell_shares * current_price * (1 - COMMISSION)
                    shares -= sell_shares
                    
                    # Record trade
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'price': current_price,
                        'shares': sell_shares,
                        'value': sell_shares * current_price,
                        'reason': 'band_riding'
                    })
            
            # Execute full sell if sell signal
            if sell_signal:
                cash += shares * current_price * (1 - COMMISSION)
                
                # Record trade
                trades.append({
                    'date': date,
                    'type': 'sell',
                    'price': current_price,
                    'shares': shares,
                    'value': shares * current_price,
                    'reason': 'signal' if b_value > sell_b_threshold else 'stop_loss'
                })
                
                sell_signals.append(i)
                
                # Reset position tracking
                shares = 0
                current_tranche = 0
                allocated_capital = 0
                entry_price = 0
                max_price_since_entry = 0
        
        # Update equity and drawdown
        current_equity = cash + shares * current_price
        equity.append(current_equity)
        
        # Update max equity and calculate drawdown
        if current_equity > max_equity:
            max_equity = current_equity
        
        if max_equity > 0:
            drawdown = (max_equity - current_equity) / max_equity * 100
            drawdowns.append(drawdown)
    
    # Calculate returns
    total_return = (equity[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # Calculate annualized return
    years = (df.index[-1] - df.index[0]).days / 365.25
    annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100
    
    # Maximum drawdown
    max_drawdown = max(drawdowns) if drawdowns else 0
    
    # Return results
    results = {
        'equity_curve': equity,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'trades': trades,
        'parameters': params,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'final_value': equity[-1],
        'sharpe_ratio': (annual_return - 1.5) / (np.std(np.diff(equity)/equity[:-1]) * np.sqrt(252)) if len(equity) > 1 else 0
    }
    
    return results

def plot_results_with_buyhold(df, strategy_results, buyhold_results, title=None):
    """Plot strategy results against buy and hold"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 2]})
    
    # Plot price data on top chart
    ax1.plot(df.index, df['Close'], label='Close Price', alpha=0.5)
    
    if 'MA25' in df.columns:
        ax1.plot(df.index, df['MA25'], label='MA25', alpha=0.7)
    
    if 'UpperBand' in df.columns and 'LowerBand' in df.columns:
        ax1.plot(df.index, df['UpperBand'], 'g--', label='Upper Band', alpha=0.7)
        ax1.plot(df.index, df['LowerBand'], 'r--', label='Lower Band', alpha=0.7)
    
    # Plot buy and sell signals
    for idx in strategy_results['buy_signals']:
        ax1.scatter(df.index[idx], df['Close'].iloc[idx], color='green', marker='^', s=100, alpha=0.7)
    
    for idx in strategy_results['sell_signals']:
        ax1.scatter(df.index[idx], df['Close'].iloc[idx], color='red', marker='v', s=100, alpha=0.7)
    
    # Plot equity curves on bottom chart
    ax2.plot(df.index, strategy_results['equity_curve'], label='Strategy', color='blue')
    ax2.plot(df.index, buyhold_results['equity_curve'], label='Buy & Hold', color='orange', linestyle='--')
    
    # Calculate outperformance
    outperformance = strategy_results['total_return'] - buyhold_results['total_return']
    
    # Set titles and labels
    strategy_params = strategy_results['parameters']
    params_str = f"Buy: %B<{strategy_params['buy_b_threshold']}, MFI<{strategy_params['buy_mfi_threshold']} | "
    params_str += f"Sell: %B>{strategy_params['sell_b_threshold']}, MFI>{strategy_params['sell_mfi_threshold']} | "
    params_str += f"Tranches: {strategy_params['tranche_count']} | StopLoss: {strategy_params['stop_loss_percent']}% | "
    params_str += f"Risk: {strategy_params['risk_level']} | BandRiding: {strategy_params['band_riding']}"
    
    main_title = title or f"{TICKER} Strategy vs Buy & Hold - {params_str}"
    fig.suptitle(main_title, fontsize=12)
    
    strategy_text = f"Strategy: Return: {strategy_results['total_return']:.2f}%, Annual: {strategy_results['annual_return']:.2f}%, Max DD: {strategy_results['max_drawdown']:.2f}%"
    buyhold_text = f"Buy & Hold: Return: {buyhold_results['total_return']:.2f}%, Annual: {buyhold_results['annual_return']:.2f}%, Max DD: {buyhold_results['max_drawdown']:.2f}%"
    
    performance_text = f"{strategy_text}\n{buyhold_text}\nOutperformance: {outperformance:.2f}%"
    ax1.set_title(performance_text)
    
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True)
    
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Portfolio Value ($)')
    ax2.legend(loc='upper left')
    ax2.grid(True)
    
    # Save the figure if title is provided
    if title:
        # Create results directory if it doesn't exist
        if not os.path.exists('backtest/results'):
            os.makedirs('backtest/results')
        plt.savefig(f"backtest/results/{title.replace(' ', '_')}_vs_buyhold.png")
    
    return fig

def plot_comparison_with_buyhold(df, all_results, buyhold_results):
    """Plot all strategies against buy and hold"""
    plt.figure(figsize=(15, 10))
    
    # Plot buy and hold first as a reference
    plt.plot(df.index, buyhold_results['equity_curve'], label='Buy & Hold', linewidth=3, color='black')
    
    # Plot top 5 strategy equity curves
    colors = ['blue', 'green', 'red', 'purple', 'orange']
    for i, result in enumerate(all_results[:5]):
        plt.plot(df.index, result['equity_curve'], 
                label=f"Strategy {i+1} ({result['total_return']:.2f}%)", 
                color=colors[i], alpha=0.7)
    
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.title(f'Top 5 {TICKER} Strategies vs Buy & Hold')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'backtest/results/{TICKER}_strategies_vs_buyhold.png')

def generate_parameter_combinations():
    """Generate different parameter combinations to test"""
    parameter_sets = []
    
    # Default parameters
    default_params = {
        'buy_b_threshold': 0.2,
        'buy_mfi_threshold': 20,
        'sell_b_threshold': 0.8,
        'sell_mfi_threshold': 80,
        'tranche_count': 3,
        'stop_loss_percent': 7,
        'band_riding': False,
        'risk_level': 'medium'
    }
    parameter_sets.append(default_params)
    
    # Different tranche counts
    for tranche in [1, 2, 4, 5]:
        params = default_params.copy()
        params['tranche_count'] = tranche
        parameter_sets.append(params)
    
    # Different stop loss percentages
    for stop_loss in [5, 10, 15]:
        params = default_params.copy()
        params['stop_loss_percent'] = stop_loss
        parameter_sets.append(params)
    
    # Different risk levels
    for risk in ['low', 'high']:
        params = default_params.copy()
        params['risk_level'] = risk
        parameter_sets.append(params)
    
    # With band riding
    params = default_params.copy()
    params['band_riding'] = True
    parameter_sets.append(params)
    
    # Different B thresholds
    thresholds = [
        {'buy_b': 0.1, 'sell_b': 0.9},
        {'buy_b': 0.3, 'sell_b': 0.7}
    ]
    for threshold in thresholds:
        params = default_params.copy()
        params['buy_b_threshold'] = threshold['buy_b']
        params['sell_b_threshold'] = threshold['sell_b']
        parameter_sets.append(params)
    
    # Different MFI thresholds
    mfi_thresholds = [
        {'buy_mfi': 30, 'sell_mfi': 70},
        {'buy_mfi': 10, 'sell_mfi': 90}
    ]
    for threshold in mfi_thresholds:
        params = default_params.copy()
        params['buy_mfi_threshold'] = threshold['buy_mfi']
        params['sell_mfi_threshold'] = threshold['sell_mfi']
        parameter_sets.append(params)
    
    return parameter_sets

def run_parameter_comparison_with_buyhold():
    """Run backtest with different parameter combinations and compare against buy and hold"""
    # Download data once
    df = download_data(TICKER, START_DATE, END_DATE)
    
    # Add technical indicators
    df = add_all_indicators(df)
    
    # Debug: print column names to ensure indicators were added correctly
    print("Available columns after adding indicators:", df.columns.tolist())
    
    # Create results directory if it doesn't exist
    if not os.path.exists('backtest/results'):
        os.makedirs('backtest/results')
    
    # Run buy and hold backtest first
    buyhold_results = run_buy_and_hold(df)
    print(f"\nBuy & Hold results for {TICKER}:")
    print(f"Total Return: {buyhold_results['total_return']:.2f}%")
    print(f"Annual Return: {buyhold_results['annual_return']:.2f}%")
    print(f"Max Drawdown: {buyhold_results['max_drawdown']:.2f}%")
    print(f"Final Value: ${buyhold_results['final_value']:.2f}")
    
    # Generate parameter combinations
    parameter_sets = generate_parameter_combinations()
    
    # Run backtest for each parameter set
    all_results = []
    
    for i, params in enumerate(parameter_sets):
        print(f"\nRunning backtest {i+1}/{len(parameter_sets)} with parameters:")
        print(params)
        
        results = run_backtest(df, params)
        if results is None:
            print(f"Skipping backtest {i+1} due to errors")
            continue
            
        all_results.append(results)
        
        # Create a descriptive title for the plot
        param_description = f"{TICKER} - "
        if params != parameter_sets[0]:  # Not the default parameters
            # Identify what's different from default
            diff_keys = [k for k in params if params[k] != parameter_sets[0][k]]
            param_description += ", ".join([f"{k.replace('_', ' ')}: {params[k]}" for k in diff_keys])
        else:
            param_description += "Default Parameters"
        
        # Plot and save results
        plot_results_with_buyhold(df, results, buyhold_results, title=param_description)
    
    # Skip the rest if no valid results
    if not all_results:
        print("No valid backtest results to analyze")
        return
    
    # Create comparison table
    comparison_data = []
    for result in all_results:
        outperformance = result['total_return'] - buyhold_results['total_return']
        comparison_data.append({
            'parameters': result['parameters'],
            'total_return': result['total_return'],
            'annual_return': result['annual_return'],
            'max_drawdown': result['max_drawdown'],
            'final_value': result['final_value'],
            'sharpe_ratio': result['sharpe_ratio'],
            'trade_count': len(result['trades']),
            'outperformance': outperformance,
            'result_obj': result  # Store the full result object for later use
        })
    
    # Sort by total return
    comparison_data.sort(key=lambda x: x['total_return'], reverse=True)
    
    # Save comparison to CSV
    comparison_df = pd.DataFrame()
    
    for i, data in enumerate(comparison_data):
        params = data['parameters']
        row = {
            'Rank': i+1,
            'Total Return (%)': round(data['total_return'], 2),
            'Buy & Hold Return (%)': round(buyhold_results['total_return'], 2),
            'Outperformance (%)': round(data['outperformance'], 2),
            'Annual Return (%)': round(data['annual_return'], 2),
            'Max Drawdown (%)': round(data['max_drawdown'], 2),
            'Final Value ($)': round(data['final_value'], 2),
            'Sharpe Ratio': round(data['sharpe_ratio'], 2),
            'Trade Count': data['trade_count'],
            'Tranche Count': params['tranche_count'],
            'Stop Loss (%)': params['stop_loss_percent'],
            'Risk Level': params['risk_level'],
            'Band Riding': 'Yes' if params['band_riding'] else 'No',
            'Buy %B Threshold': params['buy_b_threshold'],
            'Sell %B Threshold': params['sell_b_threshold'],
            'Buy MFI Threshold': params['buy_mfi_threshold'],
            'Sell MFI Threshold': params['sell_mfi_threshold']
        }
        comparison_df = pd.concat([comparison_df, pd.DataFrame([row])], ignore_index=True)
    
    comparison_df.to_csv(f'backtest/results/{TICKER}_parameter_comparison_vs_buyhold.csv', index=False)
    
    # Plot comparative results
    plt.figure(figsize=(12, 8))
    # Ensure there are 15 bars even with Buy & Hold by creating a vertical line at 0
    plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
    plt.bar(range(len(comparison_data)), 
            [data['outperformance'] for data in comparison_data], 
            color=['green' if x > 0 else 'red' for x in [data['outperformance'] for data in comparison_data]])
    plt.xlabel('Strategy Variant')
    plt.ylabel('Outperformance vs Buy & Hold (%)')
    plt.title(f'{TICKER} Strategy Outperformance vs Buy & Hold')
    plt.grid(True, alpha=0.3)
    plt.savefig(f'backtest/results/{TICKER}_outperformance_comparison.png')
    
    # Plot top 5 strategies and buy & hold
    top_results = [data['result_obj'] for data in comparison_data[:5]]
    
    # Plot comparison
    plot_comparison_with_buyhold(df, top_results, buyhold_results)
    
    print(f"\nBacktest comparison completed. Results saved to backtest/results/{TICKER}_parameter_comparison_vs_buyhold.csv")
    print("Top 5 strategies by total return (compared to Buy & Hold):")
    for i in range(min(5, len(comparison_data))):
        data = comparison_data[i]
        params = data['parameters']
        print(f"{i+1}. Return: {data['total_return']:.2f}% vs Buy & Hold {buyhold_results['total_return']:.2f}% (Diff: {data['outperformance']:.2f}%)")
        print(f"   Annual: {data['annual_return']:.2f}% vs Buy & Hold {buyhold_results['annual_return']:.2f}%")
        print(f"   Max DD: {data['max_drawdown']:.2f}% vs Buy & Hold {buyhold_results['max_drawdown']:.2f}%")
        print(f"   Params: Tranches={params['tranche_count']}, StopLoss={params['stop_loss_percent']}%, Risk={params['risk_level']}, BandRiding={params['band_riding']}")
        print(f"   Thresholds: Buy %B<{params['buy_b_threshold']}, MFI<{params['buy_mfi_threshold']} | Sell %B>{params['sell_b_threshold']}, MFI>{params['sell_mfi_threshold']}\n")

if __name__ == "__main__":
    run_parameter_comparison_with_buyhold() 