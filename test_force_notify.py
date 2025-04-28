import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import os
import sys

# Add the project directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import check_trading_signal

def create_sample_data(scenario='hold'):
    """
    Create sample data for testing
    scenario: 'hold' - creates data that will generate a HOLD signal
    """
    # Create date range for the past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create sample data based on scenario
    if scenario == 'hold':
        # Create a neutral scenario that will generate a HOLD signal
        close_prices = np.linspace(100, 105, len(dates))  # Slight uptrend
        volume = np.random.randint(1000, 2000, size=len(dates))
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'close': close_prices,
        'volume': volume
    })
    
    # Set date as index
    df.set_index('date', inplace=True)
    
    # Calculate moving average and bollinger bands
    df['ma20'] = df['close'].rolling(window=20).mean().fillna(method='bfill')
    df['std20'] = df['close'].rolling(window=20).std().fillna(method='bfill')
    df['upper_band'] = df['ma20'] + 2 * df['std20']
    df['lower_band'] = df['ma20'] - 2 * df['std20']
    df['%b'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
    
    # Calculate MFI (simplified for testing)
    df['mfi'] = 50 + np.random.normal(0, 5, size=len(df))  # Neutral MFI around 50
    
    return df

def main():
    print("force_notify 매개변수 테스트 중...")
    print("\n1. force_notify 없이 테스트:")
    create_sample_data('hold')  # 데이터는 생성하지만 직접 사용하지 않음
    check_trading_signal(
        ticker="SPY", 
        notify_method="json_body",
        tranche_count=3, 
        stop_loss_percent=5, 
        band_riding_detection=True,
        risk_management_level="medium",
        use_mfi_filter=True,
        force_notify=False
    )
    
    print("\n2. force_notify 활성화하여 테스트:")
    check_trading_signal(
        ticker="SPY", 
        notify_method="json_body",
        tranche_count=3, 
        stop_loss_percent=5, 
        band_riding_detection=True,
        risk_management_level="medium",
        use_mfi_filter=True,
        force_notify=True
    )
    
    print("\n테스트 완료!")

if __name__ == "__main__":
    main() 