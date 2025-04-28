import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.signal import generate_trading_signal

# Create sample data
def create_sample_data(scenario='buy'):
    """Create sample data for testing different scenarios"""
    dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
    
    # Base DataFrame with close prices
    df = pd.DataFrame({
        'Date': dates,
        'Close': np.linspace(100, 110, 30),
        'Volume': np.random.randint(1000, 10000, 30)
    })
    
    # Set index to Date
    df.set_index('Date', inplace=True)
    
    # Add moving average
    df['MA25'] = df['Close'].rolling(window=25).mean().fillna(method='bfill')
    
    # Add Bollinger Bands
    if scenario == 'buy':
        # Buy scenario: %B near 0
        df['%B'] = np.linspace(0.3, 0.05, 30)
        df['MFI'] = np.linspace(40, 15, 30)
    elif scenario == 'sell':
        # Sell scenario: %B near 1
        df['%B'] = np.linspace(0.7, 0.95, 30)
        df['MFI'] = np.linspace(60, 85, 30)
    elif scenario == 'mid_break_up':
        # Middle line break up
        df['%B'] = np.linspace(0.4, 0.6, 30)
        df['MFI'] = np.linspace(45, 55, 30)
    else:
        # Hold scenario
        df['%B'] = np.linspace(0.4, 0.45, 30)
        df['MFI'] = np.linspace(45, 50, 30)
    
    # Add upper and lower bands
    df['UpperBand'] = df['MA25'] + 2 * df['Close'].rolling(window=20).std().fillna(method='bfill')
    df['LowerBand'] = df['MA25'] - 2 * df['Close'].rolling(window=20).std().fillna(method='bfill')
    
    return df

# Test different scenarios
for scenario in ['buy', 'sell', 'mid_break_up', 'hold']:
    print(f"\n=== Testing {scenario.upper()} scenario ===")
    df = create_sample_data(scenario)
    
    # Generate signal with MFI filter
    result = generate_trading_signal(df, use_mfi_filter=True)
    
    # Print the results
    print(f"Signal: {result['signal']}")
    print(f"Message: {result['message']}")
    print(f"Reason: {result['reason']}")
    print(f"Technical data: %B={result['data']['b_value']:.4f}, MFI={result['data']['mfi']:.2f}")
    
    if 'deviation_percent' in result['data']:
        print(f"Deviation: {result['data']['deviation_percent']:.2f}%")
    
    print("-" * 50)

print("\nAll tests completed.") 