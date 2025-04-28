import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import os
import sys
import matplotlib.dates as mdates

# Add the project root to the Python path to import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.indicators import calculate_bollinger_bands, calculate_mfi, add_all_indicators

# Define backtest parameters
END_DATE = datetime.now().strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")  # 5년 데이터
TICKER = "SPY"
INITIAL_CAPITAL = 10000
COMMISSION = 0.001  # 0.1% commission per trade

def download_data(ticker, start_date, end_date):
    """Download historical data for a ticker"""
    print(f"Downloading {ticker} data from {start_date} to {end_date}...")
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True)
    
    # 다중 인덱스 열 있는 경우 평탄화
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    
    # 지표 추가
    data = add_all_indicators(data)
    
    print(f"Downloaded {len(data)} data points for {ticker}")
    return data

def run_buy_and_hold(df):
    """
    단순 매수 후 보유 전략 실행
    """
    # 변수 초기화
    cash = 0
    equity = []
    trades = []
    
    # 시작가로 매수
    start_price = df['Close'].iloc[0]
    shares = int(INITIAL_CAPITAL / start_price)
    cost = shares * start_price * (1 + COMMISSION)
    cash = INITIAL_CAPITAL - cost
    
    # 자산가치 추적
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        current_equity = cash + shares * current_price
        equity.append(current_equity)
    
    # 매수 정보 기록
    trades.append({
        'date': df.index[0].strftime('%Y-%m-%d'),
        'type': 'buy',
        'price': float(start_price),
        'shares': shares,
        'value': float(shares * start_price)
    })
    
    # 수익률 계산
    total_return = (equity[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # 연간 수익률 계산
    years = (df.index[-1] - df.index[0]).days / 365.25
    annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100
    
    # 최대 낙폭 계산
    drawdowns = []
    max_equity = equity[0]
    
    for current_equity in equity:
        if current_equity > max_equity:
            max_equity = current_equity
        if max_equity > 0:
            drawdown = (max_equity - current_equity) / max_equity * 100
            drawdowns.append(drawdown)
    
    max_drawdown = max(drawdowns) if drawdowns else 0
    
    # 결과 반환
    return {
        'equity_curve': equity,
        'trades': trades,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'final_value': equity[-1],
        'total_trades': len(trades)
    }

def run_bollinger_strategy(df, params):
    """
    볼린저 밴드 전략 백테스트 실행
    
    Parameters:
    -----------
    df : DataFrame
        주가 데이터 및 지표
    params : dict
        전략 파라미터
    """
    # 파라미터 추출
    tranche_count = params.get('tranche_count', 3)  # 분할 매수 횟수
    stop_loss_percent = params.get('stop_loss_percent', 7)  # 손절매 비율
    use_band_riding = params.get('use_band_riding', True)  # 밴드타기 감지 사용
    risk_level = params.get('risk_level', 'medium')  # 리스크 수준
    target_profit_percent = params.get('target_profit_percent', 10)  # 목표 수익률
    use_mfi_filter = params.get('use_mfi_filter', False)  # MFI 필터 사용 여부
    
    # 포트폴리오 변수 초기화
    cash = INITIAL_CAPITAL
    shares = 0
    equity = []
    trades = []
    
    # 매수 관련 변수
    entry_price = 0
    max_price_since_entry = 0
    stop_loss_price = 0
    target_profit_price = 0
    
    # 트랜치(분할매수) 관련 변수
    current_tranche = 0
    allocated_capital = 0
    
    # 리스크 수준에 따른 트랜치 조정
    if risk_level == 'low':
        tranche_amounts = [0.15, 0.2, 0.25, 0.4]  # 15%, 20%, 25%, 40%
    elif risk_level == 'medium':
        tranche_amounts = [0.25, 0.35, 0.4]  # 25%, 35%, 40%
    else:  # high
        tranche_amounts = [0.4, 0.6]  # 40%, 60%
    
    # 리스크 수준에 따른 매도 분할 전략
    if risk_level == 'low':
        sell_tranches = [0.7, 0.3]  # 70%, 30% 
    elif risk_level == 'medium':
        sell_tranches = [0.4, 0.3, 0.3]  # 40%, 30%, 30%
    else:  # high
        sell_tranches = [0.3, 0.2, 0.2, 0.3]  # 30%, 20%, 20%, 30%
    
    # 현재 매도 단계
    current_sell_tranche = 0
    remaining_shares = 0
    
    # 데이터 순회
    for i in range(len(df)):
        date = df.index[i]
        current_price = float(df['Close'].iloc[i])
        
        # 필요한 지표 추출
        b_value = float(df['%B'].iloc[i]) if not pd.isna(df['%B'].iloc[i]) else 0.5
        mfi_value = float(df['MFI'].iloc[i]) if 'MFI' in df.columns and not pd.isna(df['MFI'].iloc[i]) else 50
        
        # 현재 자산가치
        current_value = cash + shares * current_price
        
        # 밴드타기 감지
        is_band_riding = False
        band_riding_strength = 0
        
        if use_band_riding and i >= 5:
            # 최근 5일간의 데이터
            lookback_df = df.iloc[i-5:i+1]
            # 상단밴드 접촉 횟수
            upper_band_touches = lookback_df[lookback_df['%B'] >= 0.8]
            
            if len(upper_band_touches) >= 3:
                is_band_riding = True
                # 밴드타기 강도 계산 (0-100%)
                band_riding_strength = (len(upper_band_touches) / 5) * 100
                
                # 강한 상승 추세 확인
                price_up_days = sum(1 for j in range(i-5, i) if j > 0 and float(df['Close'].iloc[j]) > float(df['Close'].iloc[j-1]))
                volume_increase = float(df['Volume'].iloc[i]) > float(df['Volume'].iloc[i-5])
                
                strong_trend = (price_up_days / 5 * 100 >= 70) and (volume_increase or b_value >= 0.9)
        
        # 매수 신호 확인 - 하단밴드 터치, 분할매수 전략
        buy_signal = False
        if shares == 0 or current_tranche < len(tranche_amounts):
            if b_value <= 0.2 and b_value > 0.1:
                # 첫 매수 (하단밴드 터치)
                buy_signal = True
                allocation_percent = tranche_amounts[0 if current_tranche == 0 else min(current_tranche, len(tranche_amounts)-1)]
            elif b_value <= 0.1 and b_value > 0.05:
                # 추가 하락 시 매수
                buy_signal = True
                allocation_percent = tranche_amounts[1 if current_tranche < 1 else min(current_tranche, len(tranche_amounts)-1)]
            elif b_value <= 0.05:
                # 급격한 하락 시 안전망 매수
                buy_signal = True
                allocation_percent = tranche_amounts[-1]  # 마지막 트랜치 사용
            
            # MFI 확인으로 매수 신호 보강
            if buy_signal:
                if use_mfi_filter:
                    # MFI 필터 활성화: MFI가 20 이하인 경우에만 매수
                    if mfi_value > 20:
                        buy_signal = False
                        continue
                else:
                    # 기존 로직: MFI가 50 이상이면 매수 시점 재검토
                    if mfi_value >= 50:
                        buy_signal = False
                        continue
        
        # 매도 신호 확인
        sell_signal = False
        partial_sell = False
        sell_percent = 0
        
        if shares > 0:
            # 손절매 확인
            if entry_price > 0 and current_price < stop_loss_price:
                sell_signal = True
                sell_percent = 1.0  # 전량 매도
                sell_reason = "손절매"
            
            # 목표 수익률 도달 확인
            elif entry_price > 0 and current_price >= target_profit_price:
                sell_signal = True
                sell_percent = 1.0  # 전량 매도
                sell_reason = "목표 수익률 도달"
            
            # 익절 전략
            elif b_value >= 0.45 and b_value <= 0.55:
                # 중심선 도달 시 50% 익절 고려
                partial_sell = True
                sell_percent = 0.5
                sell_reason = "익절"
            elif b_value > 0.7:
                # 상단밴드 접근 시 매도 검토
                if is_band_riding:
                    if band_riding_strength >= 70:
                        # 강한 밴드타기 - 이익실현
                        sell_signal = True
                        sell_percent = sell_tranches[current_sell_tranche]
                        current_sell_tranche = min(current_sell_tranche + 1, len(sell_tranches) - 1)
                        sell_reason = "밴드타기 매도"
                    elif band_riding_strength >= 40:
                        # 중간 강도 - 분할 매도
                        partial_sell = True
                        sell_percent = sell_tranches[0] / 2
                        sell_reason = "밴드타기 매도"
                else:
                    # 일반적인 상단밴드 접근
                    sell_signal = True
                    sell_percent = 1.0  # 전량 매도
                    sell_reason = "익절"
            
            # MFI 확인으로 매도 신호 보강
            if (sell_signal or partial_sell):
                if use_mfi_filter:
                    # MFI 필터 활성화: MFI가 80 이상인 경우에만 매도
                    if mfi_value < 80:
                        sell_signal = False
                        partial_sell = False
                        continue
                else:
                    # 기존 로직: MFI가 50 이하면 매도 시점 재검토
                    if mfi_value <= 50:
                        sell_signal = False
                        partial_sell = False
                        continue
        
        # 매수 실행
        if buy_signal and cash > 0:
            # 투자 금액 계산
            amount_to_invest = min(INITIAL_CAPITAL * tranche_amounts[current_tranche], cash)
            
            # 구매 가능한 주식 수
            new_shares = int(amount_to_invest / (current_price * (1 + COMMISSION)))
            
            if new_shares > 0:
                cost = new_shares * current_price * (1 + COMMISSION)
                cash -= cost
                shares += new_shares
                
                # 평균 매수가 계산
                if entry_price == 0:
                    entry_price = current_price
                else:
                    entry_price = ((shares - new_shares) * entry_price + new_shares * current_price) / shares
                
                # 손절가 설정
                stop_loss_price = entry_price * (1 - stop_loss_percent/100)
                
                # 목표 수익률에 따른 목표가 설정
                target_profit_price = entry_price * (1 + target_profit_percent/100)
                
                # 트랜치 카운트 증가
                current_tranche += 1
                
                # 매수 기록
                mfi_status = f", MFI: {mfi_value:.1f}" if use_mfi_filter else ""
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': 'buy',
                    'price': current_price,
                    'shares': new_shares,
                    'value': new_shares * current_price,
                    'reason': f'하단밴드 매수 (트랜치 {current_tranche}{mfi_status})'
                })
        
        # 매도 실행 (전량 또는 부분)
        if (sell_signal or partial_sell) and shares > 0:
            # 매도할 주식 수
            shares_to_sell = int(shares * sell_percent)
            
            if shares_to_sell > 0:
                sale_value = shares_to_sell * current_price * (1 - COMMISSION)
                cash += sale_value
                shares -= shares_to_sell
                
                # 매도 기록
                mfi_status = f", MFI: {mfi_value:.1f}" if use_mfi_filter else ""
                sell_reason_with_mfi = f"{sell_reason if 'sell_reason' in locals() else '익절'}{mfi_status}"
                
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': 'sell',
                    'price': current_price,
                    'shares': shares_to_sell,
                    'value': shares_to_sell * current_price,
                    'reason': sell_reason_with_mfi
                })
                
                # 모든 주식 매도 시 초기화
                if shares == 0:
                    entry_price = 0
                    max_price_since_entry = 0
                    stop_loss_price = 0
                    target_profit_price = 0
                    current_tranche = 0
                    current_sell_tranche = 0
        
        # 최고가 갱신 시 추적
        if shares > 0 and current_price > max_price_since_entry:
            max_price_since_entry = current_price
            
            # 추세 강도에 따라 트레일링 스탑 적용 (밴드타기 감지 시)
            if is_band_riding and band_riding_strength > 60:
                # 강한 추세에서는 트레일링 스탑 적용
                new_stop_loss = max_price_since_entry * (1 - stop_loss_percent/200)  # 절반의 손절 비율 적용
                if new_stop_loss > stop_loss_price:
                    stop_loss_price = new_stop_loss
        
        # 자산 가치 추적
        equity.append(current_value)
    
    # 마지막 날에 남은 주식 가치
    final_price = float(df['Close'].iloc[-1])
    final_value = cash + shares * final_price
    
    # 수익률 계산
    total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # 연간 수익률
    years = (df.index[-1] - df.index[0]).days / 365.25
    annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100
    
    # 최대 낙폭 계산
    drawdowns = []
    max_equity = equity[0]
    
    for current_equity in equity:
        if current_equity > max_equity:
            max_equity = current_equity
        if max_equity > 0:
            drawdown = (max_equity - current_equity) / max_equity * 100
            drawdowns.append(drawdown)
    
    max_drawdown = max(drawdowns) if drawdowns else 0
    
    return {
        'equity_curve': equity,
        'trades': trades,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'final_value': final_value,
        'total_trades': len(trades),
        'params': params
    }

def plot_comparison(df, strategies_results):
    """결과 비교 그래프 생성"""
    # 날짜 범위
    dates = df.index
    
    # 결과 플롯
    plt.figure(figsize=(16, 12))
    
    # 자산 가치 곡선
    ax1 = plt.subplot(311)
    for name, result in strategies_results.items():
        # 데이터 길이 확인 및 조정
        equity_curve = result['equity_curve']
        if len(equity_curve) != len(dates):
            # 길이가 다르면 데이터프레임 인덱스에 맞게 조정
            if len(equity_curve) < len(dates):
                # 부족한 데이터는 마지막 값으로 채움
                padding = [equity_curve[-1]] * (len(dates) - len(equity_curve))
                equity_curve = equity_curve + padding
            else:
                # 초과 데이터는 잘라냄
                equity_curve = equity_curve[:len(dates)]
        
        plt.plot(dates, equity_curve, label=f"{name} (Return: {result['total_return']:.2f}%)")
    
    plt.title('Strategy Asset Value Comparison', fontsize=14)
    plt.ylabel('Asset Value ($)')
    plt.legend(loc='upper left')
    plt.grid(True)
    
    # 수익률 곡선 (초기 투자 대비 %)
    ax2 = plt.subplot(312, sharex=ax1)
    for name, result in strategies_results.items():
        # 초기 투자 대비 % 변화로 변환
        equity_curve = result['equity_curve']
        if len(equity_curve) != len(dates):
            # 길이가 다르면 데이터프레임 인덱스에 맞게 조정
            if len(equity_curve) < len(dates):
                padding = [equity_curve[-1]] * (len(dates) - len(equity_curve))
                equity_curve = equity_curve + padding
            else:
                equity_curve = equity_curve[:len(dates)]
                
        returns = [(equity / INITIAL_CAPITAL - 1) * 100 for equity in equity_curve]
        plt.plot(dates, returns, label=f"{name}")
    
    plt.title('Percentage Return Comparison', fontsize=14)
    plt.ylabel('Return (%)')
    plt.legend(loc='upper left')
    plt.grid(True)
    
    # 가격 차트
    ax3 = plt.subplot(313, sharex=ax1)
    plt.plot(dates, df['Close'], label='SPY Close', color='gray')
    
    # Bollinger Bands
    plt.plot(dates, df['UpperBand'], 'r--', label='Upper Band', alpha=0.5)
    plt.plot(dates, df['MA25'], 'g--', label='MA25 (Center)', alpha=0.5)
    plt.plot(dates, df['LowerBand'], 'b--', label='Lower Band', alpha=0.5)
    
    # SMA 200 추가
    plt.plot(dates, df['SMA200'], 'purple', label='SMA 200', linewidth=1.5, alpha=0.7)
    
    # 매매 표시 - 전략별로 다른 색상 및 마커 사용
    colors = ['green', 'blue', 'orange', 'red', 'cyan']
    markers = ['^', 's', 'd', 'o', 'x']
    
    for i, (name, result) in enumerate(strategies_results.items()):
        if name == 'Buy & Hold':
            continue
            
        # 매수/매도 포인트 표시
        buy_dates = [pd.to_datetime(trade['date']) for trade in result['trades'] if trade['type'] == 'buy']
        buy_prices = [trade['price'] for trade in result['trades'] if trade['type'] == 'buy']
        
        sell_dates = [pd.to_datetime(trade['date']) for trade in result['trades'] if trade['type'] == 'sell']
        sell_prices = [trade['price'] for trade in result['trades'] if trade['type'] == 'sell']
        
        # 주요 거래만 표시 (30회 이상인 경우 일부만)
        max_points = 30
        if len(buy_dates) > max_points:
            step = len(buy_dates) // max_points
            buy_dates = buy_dates[::step]
            buy_prices = buy_prices[::step]
            
        if len(sell_dates) > max_points:
            step = len(sell_dates) // max_points
            sell_dates = sell_dates[::step]
            sell_prices = sell_prices[::step]
        
        # 색상 인덱스 범위 확인
        color_idx = i % len(colors)
        marker_idx = i % len(markers)
        
        if buy_dates:
            plt.scatter(buy_dates, buy_prices, marker=markers[marker_idx], color=colors[color_idx], 
                       s=50, alpha=0.6, label=f"{name} Buy")
            
        if sell_dates:
            plt.scatter(sell_dates, sell_prices, marker='v', color=colors[color_idx], 
                       s=50, alpha=0.6, label=f"{name} Sell")
    
    plt.title('SPY Price Chart with Trading Points', fontsize=14)
    plt.ylabel('Price ($)')
    plt.xlabel('Date')
    plt.legend(loc='upper left', ncol=2)
    plt.grid(True)
    
    # x축 날짜 포맷 조정
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # 3개월 간격
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # 현재 스크립트 위치 기준 상대 경로 사용
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, 'spy_band_riding_comparison.png')
    plt.savefig(output_path, dpi=300)
    print(f"Saved chart to: {output_path}")
    plt.close()

def format_trade_log(trades):
    """매매 기록 포맷팅"""
    log = []
    for trade in trades:
        log.append(f"{trade['date']} - {trade['type'].upper()}: {trade['shares']} 주 @ ${trade['price']:.2f} (${trade['value']:.2f})")
        if 'reason' in trade:
            log[-1] += f" - 이유: {trade['reason']}"
    return log

def run_comparison():
    """전략 비교 실행"""
    # 데이터 다운로드
    df = download_data(TICKER, START_DATE, END_DATE)
    
    # Buy & Hold 전략 실행
    buy_hold_results = run_buy_and_hold(df)
    
    # 밴드타기 감지 기능 사용 vs 미사용 비교
    bollinger_with_band_riding = run_bollinger_strategy(df, {
        'tranche_count': 3,            # 분할 매수 횟수
        'stop_loss_percent': 7,        # 손절매 비율
        'use_band_riding': True,       # 밴드타기 감지 사용
        'risk_level': 'medium',        # 리스크 수준 (low, medium, high)
        'target_profit_percent': 10,   # 목표 수익률
        'use_mfi_filter': False        # MFI 필터 미사용
    })
    
    bollinger_without_band_riding = run_bollinger_strategy(df, {
        'tranche_count': 3,
        'stop_loss_percent': 7,
        'use_band_riding': False,
        'risk_level': 'medium',
        'target_profit_percent': 10,
        'use_mfi_filter': False
    })
    
    # MFI 필터를 사용하는 전략 추가
    bollinger_with_mfi_filter = run_bollinger_strategy(df, {
        'tranche_count': 3,
        'stop_loss_percent': 7,
        'use_band_riding': True,
        'risk_level': 'medium',
        'target_profit_percent': 10,
        'use_mfi_filter': True        # MFI 필터 사용 (매수: MFI < 20, 매도: MFI > 80)
    })
    
    # 결과 비교
    strategies_results = {
        'Buy & Hold': buy_hold_results,
        'With Band Riding': bollinger_with_band_riding,
        'Without Band Riding': bollinger_without_band_riding,
        'With MFI Filter': bollinger_with_mfi_filter
    }
    
    # 결과 시각화
    plot_comparison(df, strategies_results)
    
    # 결과 보고서 생성
    report = "# SPY Strategy Comparison Analysis - Band Riding Effect (5 Year Data)\n\n"
    
    report += "## 1. Performance Summary\n\n"
    report += "| Strategy | Total Return | Annual Return | Max Drawdown | Final Asset | Trade Count |\n"
    report += "|------|----------|------------|---------|-----------|--------|\n"
    
    for name, result in strategies_results.items():
        report += f"| {name} | {result['total_return']:.2f}% | {result['annual_return']:.2f}% | "
        report += f"{result['max_drawdown']:.2f}% | ${result['final_value']:.2f} | {result['total_trades']} |\n"
    
    report += "\n## 2. Strategy Parameters\n\n"
    report += "### Common Parameters\n"
    report += "- **Split Purchase Count**: 3\n"
    report += "- **Stop Loss Percentage**: 7%\n"
    report += "- **Target Profit Percentage**: 10%\n"
    report += "- **Risk Level**: medium\n\n"
    
    report += "### Variable Parameters\n"
    report += "- **Band Riding Detection**: True vs False\n"
    report += "- **MFI Filter**: With MFI strategy uses stricter conditions (Buy: MFI < 20, Sell: MFI > 80)\n\n"
    
    report += "## 3. Strategy Analysis\n\n"
    
    # 각 전략 별 거래 분석
    for name, result in strategies_results.items():
        if name == 'Buy & Hold':
            continue
            
        trades = result['trades']
        buys = [t for t in trades if t['type'] == 'buy']
        sells = [t for t in trades if t['type'] == 'sell']
        
        report += f"### {name}\n"
        report += f"- **Total Trades**: {len(trades)}\n"
        report += f"- **Buy Trades**: {len(buys)}\n"
        report += f"- **Sell Trades**: {len(sells)}\n\n"
        
        # 매도 이유 분석
        if sells:
            sell_reasons = {}
            for trade in sells:
                reason = trade.get('reason', 'Unknown')
                # MFI 정보 제거하고 기본 이유만 추출
                base_reason = reason.split(',')[0] if ',' in reason else reason
                sell_reasons[base_reason] = sell_reasons.get(base_reason, 0) + 1
                
            report += "**Sell Reasons**:\n"
            for reason, count in sell_reasons.items():
                percentage = (count / len(sells)) * 100
                report += f"- {reason}: {count} times ({percentage:.1f}%)\n"
            
            report += "\n"
    
    report += "## 4. Key Differences\n\n"
    
    # 기본 밴드타기 전략과 다른 전략들 비교
    base_strategy = bollinger_with_band_riding
    for name, result in strategies_results.items():
        if name == 'Buy & Hold' or name == 'With Band Riding':
            continue
            
        performance_diff = result['total_return'] - base_strategy['total_return']
        drawdown_diff = result['max_drawdown'] - base_strategy['max_drawdown']
        trade_count_diff = len(result['trades']) - len(base_strategy['trades'])
        
        report += f"### {name} vs. With Band Riding\n"
        report += f"- **Return Difference**: {performance_diff:.2f}% {'higher' if performance_diff > 0 else 'lower'}\n"
        report += f"- **Max Drawdown Difference**: {abs(drawdown_diff):.2f}% {'higher' if drawdown_diff > 0 else 'lower'}\n"
        report += f"- **Trade Count Difference**: {abs(trade_count_diff)} {'more' if trade_count_diff > 0 else 'fewer'} trades\n\n"
    
    report += "## 5. Conclusion\n\n"
    
    # MFI 필터에 대한 결론
    mfi_performance_diff = bollinger_with_mfi_filter['total_return'] - base_strategy['total_return']
    
    if mfi_performance_diff > 0:
        report += "### MFI Filter Value\n\n"
        report += "- **Positive Impact**: Strict MFI filtering (Buy < 20, Sell > 80) improves strategy performance\n"
        report += "- Using strict MFI thresholds helped identify better entry and exit points\n\n"
    else:
        report += "### MFI Filter Value\n\n"
        report += "- **Negative Impact**: Strict MFI filtering reduced strategy performance\n"
        report += "- Stricter MFI conditions may have caused missed opportunities in this test period\n\n"
    
    report += "### Recommendation\n\n"
    
    # 밴드타기 권장 사항
    if bollinger_with_band_riding['total_return'] > bollinger_without_band_riding['total_return']:
        report += "- **Band Riding Detection**: Recommended as it improves performance\n"
    else:
        report += "- **Band Riding Detection**: Consider disabling as it may reduce performance\n"
    
    # MFI 필터 권장 사항
    if mfi_performance_diff > 0:
        report += "- **MFI Filter**: Recommended with strict thresholds (Buy < 20, Sell > 80)\n"
    else:
        report += "- **MFI Filter**: Standard thresholds may work better than strict ones\n"
    
    report += "\nThe optimal strategy depends on specific market conditions and investor's risk tolerance. "
    report += "These results are based on historical data and may not predict future performance."
    
    # 현재 스크립트 위치 기준 상대 경로 사용
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, 'spy_band_riding_comparison.md')
    
    # 보고서 저장
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Saved report to: {report_path}")
    
    return strategies_results

if __name__ == "__main__":
    run_comparison() 